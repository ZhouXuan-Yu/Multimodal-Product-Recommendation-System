"""模块三：FastAPI 后端 + 本地 Chroma 检索 + DeepSeek RAG。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from collections import defaultdict, deque
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field

from module_rag_ai.deepseek_agent import DeepSeekAgent
from module_rag_ai.multimodal_embedding import ChineseCLIPEmbedder
from module_rag_ai.vector_db_manager import VectorDBManager, load_products

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
PRODUCTS_JSON = DATA_DIR / "meta" / "products.json"
USERS_PROFILE_JSON = DATA_DIR / "meta" / "users_profile.json"
VECTOR_STORE_DIR = DATA_DIR / "vector_store"


class LoggingMiddleware(BaseHTTPMiddleware):
    """统一请求/响应日志中间件。

    - 每次前端调用后端接口时，打印请求方法、路径、查询参数和请求体（尽量截断为安全长度）；
    - 每次后端返回响应时，打印对应的状态码；
    - 已有的业务级别 print（例如 /api/recommend 内部）仍然保留，用于更细粒度的调试。
    """

    async def dispatch(self, request: Request, call_next):
        try:
            body_bytes = await request.body()
            raw_body = body_bytes.decode("utf-8", errors="ignore") if body_bytes else ""
        except Exception:  # noqa: BLE001
            raw_body = "<unreadable>"

        # 为避免日志过长，只打印前 2000 个字符
        body_preview = raw_body[:2000]

        print(
            "[backend] HTTP 请求：",
            {
                "method": request.method,
                "path": request.url.path,
                "query": dict(request.query_params),
                "body": body_preview,
            },
        )

        response = await call_next(request)

        print(
            "[backend] HTTP 响应：",
            {
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
            },
        )

        return response


app = FastAPI(title="Multimodal Recommendation API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)
app.mount("/static/images", StaticFiles(directory=str(DATA_DIR / "images")), name="images")


@app.on_event("startup")
def init_vector_db_on_startup() -> None:
    """服务启动时自动检查并初始化向量库（仅在为空时执行一次全量入库）。"""
    try:
        db = VectorDBManager()
        collection = db.collection
        has_count = hasattr(collection, "count")
        if not has_count:
            print("[backend] 当前 Chroma collection 不支持 count()，跳过启动期向量库检查。")
            return

        current_count = collection.count()
        if current_count > 0:
            print(f"[backend] 启动时检测到已有向量库记录，count={current_count}，跳过初始化。")
            return

        print("[backend] 启动时检测到向量库为空，开始离线全量入库（可能需要几分钟）...")
        products = load_products()
        if not products:
            print("[backend] 启动期入库失败：未在 data/meta/products.json 中找到商品数据。")
            return

        embedder = ChineseCLIPEmbedder()
        upserted = db.upsert_products(products, embedder)
        print(f"[backend] 启动期已完成向量库初始化，入库商品数: {upserted}")
    except Exception as exc:  # noqa: BLE001
        # 启动期初始化失败时，不中断服务，仍然保留兜底逻辑
        print("[backend] 启动期初始化向量库失败，将保留静态候选兜底逻辑：", exc)


class RecommendRequest(BaseModel):
    """前端推荐请求模型。

    - user_id: 当前用户 ID
    - query:   搜索 / 意图文本
    - page:    页码（从 1 开始）
    - page_size: 每页条数，默认与前端保持一致（20）
    """

    user_id: str = Field(..., examples=["user_001"])
    query: str = Field(..., examples=["适合通勤的简约风外套"])
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=50)


class ActionLogRequest(BaseModel):
    user_id: str
    product_id: str
    action: str = Field(..., examples=["click", "view", "buy"])
    # 可选的权重和标签，用于个性化推荐算法
    weight: float | None = Field(default=None, description="该行为在个性化模型中的权重")
    # 前端可附加额外上下文（例如：来源页面、曝光位、实验分桶等）
    extra: dict[str, Any] | None = Field(default=None, description="可选的扩展上下文信息")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"JSON 解析失败: {path.name}: {exc}") from exc


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def retrieve_top_k(query: str, top_k: int = 10) -> list[dict[str, Any]]:
    """检索层：向量召回 + products.json 反查详情。

    - 正常情况下：基于已初始化好的 Chroma 向量库，返回与 query 语义最相近的 Top-K 商品详情；
    - 若本地向量库尚未初始化，则直接返回空列表，由上层逻辑走兜底 candidates，
      同时在日志中提示需要先运行 `python module_rag_ai/vector_db_manager.py`。
    """
    # 读取商品主数据，并构造 product_id → 详情映射
    products: list[dict[str, Any]] = read_json(PRODUCTS_JSON, default=[])
    product_map = {p.get("product_id"): p for p in products if p.get("product_id")}

    if not products:
        return []

    embedder = ChineseCLIPEmbedder()
    db = VectorDBManager()

    # 若向量库尚未初始化，则直接退回静态候选集，避免首个请求耗时过长
    try:
        collection = db.collection
        has_count = hasattr(collection, "count")
        if has_count and collection.count() == 0:
            print(
                "[backend] VectorDB 当前为空，将直接退回静态候选集。"
                "请先运行：python module_rag_ai/vector_db_manager.py 完成离线入库。"
            )
            return []
    except Exception as exc:  # noqa: BLE001
        # 访问失败同样退回静态候选集
        print("[backend] VectorDB 访问失败，将退回静态候选集:", exc)
        return []

    # 使用文本查询向量化检索 Top-K
    result = db.query_by_text(query=query, embedder=embedder, top_k=top_k)
    ids = result.get("ids", [[]])[0]

    output: list[dict[str, Any]] = []
    for pid in ids:
        p = product_map.get(pid)
        if p:
            output.append(p)
    return output


def retrieve_top_k_with_scores(query: str, top_k: int = 10) -> list[dict[str, Any]]:
    """本地向量检索（带距离/相似度），用于前端直接展示 RAG 召回结果。"""
    products: list[dict[str, Any]] = read_json(PRODUCTS_JSON, default=[])
    product_map = {p.get("product_id"): p for p in products if p.get("product_id")}
    if not products:
        return []

    embedder = ChineseCLIPEmbedder()
    db = VectorDBManager()

    try:
        collection = db.collection
        has_count = hasattr(collection, "count")
        if has_count and collection.count() == 0:
            return []
    except Exception as exc:  # noqa: BLE001
        print("[backend] VectorDB 访问失败（rag_search），将返回空列表:", exc)
        return []

    result = db.query_by_text(
        query=query,
        embedder=embedder,
        top_k=top_k,
        include=["distances", "metadatas", "documents"],
    )
    ids = result.get("ids", [[]])[0]
    distances = result.get("distances", [[]])[0]

    output: list[dict[str, Any]] = []
    for idx, pid in enumerate(ids):
        p = product_map.get(pid)
        if not p:
            continue
        dist = None
        try:
            dist = float(distances[idx]) if idx < len(distances) else None
        except Exception:
            dist = None
        similarity = (1.0 - dist) if dist is not None else None
        output.append(
            {
                **p,
                "distance": dist,
                "similarity": similarity,
                "image_url": f"/static/images/{Path(p.get('image_path', '')).name}",
            }
        )
    return output


def get_default_candidates(limit: int = 1000) -> list[dict[str, Any]]:
    """兜底候选集：当向量召回不可用或为空时，直接从 products.json 截取前 N 条。

    - 统一控制上限，避免一次性返回过多数据；
    - 便于 /api/recommend 与 /api/ai_chat 复用。
    """
    products: List[dict[str, Any]] = read_json(PRODUCTS_JSON, default=[])
    if not products:
        return []
    return products[: min(len(products), max(1, limit))]


def load_products_map() -> dict[str, dict[str, Any]]:
    products: list[dict[str, Any]] = read_json(PRODUCTS_JSON, default=[])
    return {p.get("product_id"): p for p in products if p.get("product_id")}


def parse_iso_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # 支持 YYYY-MM-DD 或 ISO datetime
        if len(value) == 10:
            return datetime.fromisoformat(value + "T00:00:00")
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date: {value}")


def fallback_rank(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """当 DeepSeek 不可用时的降级策略。

    这里不再只返回 3 条，而是为所有候选打一个简易排序，便于前端展示更多商品。
    """

    return {
        "recommendations": [
            {
                "product_id": p["product_id"],
                "rank": i + 1,
                "reason": "基于本地向量相似度排序结果（LLM 降级模式）。",
            }
            for i, p in enumerate(candidates)
        ]
    }


def diversify_by_image(
    recs: list[dict[str, Any]],
    products_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    对推荐结果按图片打散排序，避免同一款图片在瀑布流中连续“刷屏”。

    设计思路（对标淘宝等电商前端的视觉打散）：
    - 将拥有相同图片（image_path）的商品视为同一“款式分组”；
    - 保留每个分组内原始 rank 顺序不变；
    - 使用轮询（round‑robin）方式在不同分组之间交替取一个元素，尽量保证：
      - 同一图片不会长时间连续出现；
      - 高 rank 的商品依然整体靠前，只是视觉上被穿插开。
    """
    if not recs:
        return recs

    # 1. 先按图片分组，key 优先使用 image_path，其次退回 product_id
    group_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in recs:
        pid = rec.get("product_id")
        product = products_map.get(pid, {})
        image_path = product.get("image_path") or product.get("image_url")
        key = image_path or pid
        group_map[key].append(rec)

    # 2. 为了尽量保持整体排序稳定，按每组首个元素的 rank 进行分组排序
    def group_rank(g: list[dict[str, Any]]) -> int:
        head = g[0]
        return int(head.get("rank") or 0)

    groups: list[deque[dict[str, Any]]] = [
        deque(group_map[k])
        for k in sorted(group_map.keys(), key=lambda kk: group_rank(group_map[kk]))
    ]

    # 3. 轮询取数：每轮从所有非空分组中各取一个，直到全部取完
    diversified: list[dict[str, Any]] = []
    while groups:
        next_round: list[deque[dict[str, Any]]] = []
        for q in groups:
            if q:
                diversified.append(q.popleft())
            if q:
                next_round.append(q)
        groups = next_round

    return diversified


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/rag_search")
def rag_search(q: str = Query(..., min_length=1), top_k: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
    """直接返回本地向量库 Top-K 检索结果（不走 LLM），用于前端展示检索多样性。"""
    items = retrieve_top_k_with_scores(query=q, top_k=top_k)
    return {"query": q, "top_k": top_k, "items": items}


@app.get("/api/user_profile/{user_id}")
def get_user_profile(user_id: str) -> dict[str, Any]:
    """
    为前端仪表盘提供一个结构稳定的用户画像数据。

    即使用户画像文件中不存在该用户，也会返回带有默认结构的占位数据，
    防止前端拿到 {} 导致图表为空。
    """
    print(f"[backend] /api/user_profile 请求 user_id={user_id}")
    users_doc = read_json(USERS_PROFILE_JSON, default={"users": {}})
    users = users_doc.get("users", {})
    profile: Dict[str, Any] = users.get(user_id, {})

    if not profile:
        # 默认占位数据，便于前端展示基础图形
        profile = {
            "name": user_id,
            "core_tags": ["新用户", "待冷启动"],
            "category_preferences": {
                "数码": 0.32,
                "服饰": 0.26,
                "家居": 0.22,
                "美妆": 0.2,
            },
            "recent_activity": [
                {
                    "day": f"2025-02-{10 + i:02d}",
                    "activity_score": 60 + i * 2,
                    "views": 80 + i * 10,
                    "conversion_rate": 0.12 + i * 0.01,
                }
                for i in range(7)
            ],
            "activity_score": 70,
        }
    print(
        "[backend] /api/user_profile 返回概览：",
        {
            "user_id": user_id,
            "has_profile": bool(profile),
            "category_keys": list(profile.get("category_preferences", {}).keys()),
            "recent_activity_len": len(profile.get("recent_activity", [])),
        },
    )
    return profile


@app.get("/api/insights/{user_id}/events")
def get_insight_events(
    user_id: str,
    start: str | None = Query(default=None, description="Start date (YYYY-MM-DD or ISO)"),
    end: str | None = Query(default=None, description="End date (YYYY-MM-DD or ISO)"),
    action: str | None = Query(default=None, description="Filter action, e.g. click/view/buy"),
    category: str | None = Query(default=None, description="Filter product category"),
    q: str | None = Query(default=None, description="Keyword filter on product name/description"),
    limit: int = Query(default=5000, ge=1, le=20000),
) -> dict[str, Any]:
    """为“个人数据洞察中心”提供结构化事件流（可被筛选/钻取/对比/异常检测复用）。"""
    users_doc = read_json(USERS_PROFILE_JSON, default={"users": {}})
    users = users_doc.get("users", {})
    profile: Dict[str, Any] = users.get(user_id, {})
    history: list[dict[str, Any]] = profile.get("history", []) if isinstance(profile, dict) else []

    start_dt = parse_iso_date(start)
    end_dt = parse_iso_date(end)
    if end_dt and len(end or "") == 10:
        # end 为日期时，包含整天（到 23:59:59）
        end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)

    products_map = load_products_map()
    keyword = (q or "").strip().lower()

    events: list[dict[str, Any]] = []
    for h in reversed(history):
        try:
            ts_raw = h.get("timestamp")
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")) if ts_raw else None
        except Exception:  # noqa: BLE001
            ts = None

        if start_dt and ts and ts < start_dt:
            continue
        if end_dt and ts and ts > end_dt:
            continue

        act = h.get("action")
        if action and act != action:
            continue

        pid = h.get("product_id")
        product = products_map.get(pid, {})
        cat = product.get("category")
        if category and cat != category:
            continue

        if keyword:
            hay = f"{product.get('name','')} {product.get('description','')}".lower()
            if keyword not in hay:
                continue

        events.append(
            {
                "timestamp": ts_raw,
                "day": (ts.date().isoformat() if ts else None),
                "action": act,
                "weight": h.get("weight"),
                "product_id": pid,
                "product_name": product.get("name"),
                "category": cat,
                "price": product.get("price"),
                "image_url": (
                    f"/static/images/{Path(product.get('image_path', '')).name}"
                    if product.get("image_path")
                    else None
                ),
            }
        )
        if len(events) >= limit:
            break

    by_category: dict[str, int] = {}
    by_action: dict[str, int] = {}
    by_day: dict[str, int] = {}
    for ev in events:
        cat_key = ev.get("category") or "unknown"
        act_key = ev.get("action") or "unknown"
        by_category[cat_key] = by_category.get(cat_key, 0) + 1
        by_action[act_key] = by_action.get(act_key, 0) + 1
        if ev.get("day"):
            by_day[ev["day"]] = by_day.get(ev["day"], 0) + 1

    overview = {
        "kpis": {
            "events": len(events),
            "active_days": len(by_day),
            "unique_products": len({e.get("product_id") for e in events if e.get("product_id")}),
        },
        "distribution": {
            "by_category": [
                {"name": k, "value": v}
                for k, v in sorted(by_category.items(), key=lambda x: x[1], reverse=True)
            ],
            "by_action": [
                {"name": k, "value": v}
                for k, v in sorted(by_action.items(), key=lambda x: x[1], reverse=True)
            ],
        },
        "timeseries": [{"day": k, "value": by_day[k]} for k in sorted(by_day.keys())],
    }

    if not events:
        profile_fallback = get_user_profile(user_id)
        pref = profile_fallback.get("category_preferences", {}) or {}
        overview["distribution"]["by_category"] = [
            {"name": k, "value": int(float(v) * 100)} for k, v in pref.items()
        ]
        raw_recent = profile_fallback.get("recent_activity", []) or []
        if raw_recent and isinstance(raw_recent[0], dict):
            overview["timeseries"] = [{"day": d.get("day"), "value": d.get("views", 0)} for d in raw_recent]
        else:
            overview["timeseries"] = [{"day": f"D{i+1}", "value": int(v) * 10} for i, v in enumerate(raw_recent[:14])]

    return {
        "user_id": user_id,
        "filters": {"start": start, "end": end, "action": action, "category": category, "q": q},
        "overview": overview,
        "events": events,
    }


@app.post("/api/recommend")
def recommend(req: RecommendRequest) -> dict[str, Any]:
    print(
        "[backend] /api/recommend 收到请求：",
        {
            "user_id": req.user_id,
            "query": req.query,
            "page": req.page,
            "page_size": req.page_size,
        },
    )
    users_doc = read_json(USERS_PROFILE_JSON, default={"users": {}})
    user_profile = users_doc.get("users", {}).get(req.user_id, {})

    # 检索层加入兜底逻辑：
    # 1. 优先从本地向量库做多模态召回；
    # 2. 若向量库或模型不可用，或召回结果为空，则回退到基于 products.json 的静态候选集。
    try:
        # 为了支持分页，召回的数量与 page / page_size 挂钩，并设置一个上限
        # 这里将上限从 80 提升到 1000，以支持更多页的浏览体验
        top_k = min(req.page * req.page_size, 1000)
        candidates = retrieve_top_k(query=req.query, top_k=top_k)
        # 向量库可用但当前尚未完成入库时，retrieve_top_k 会返回空列表；
        # 此时也应视作需要降级，而不是直接给前端空推荐。
        if not candidates:
            raise RuntimeError("Empty candidates from vector DB, fallback to products.json.")
    except Exception as exc:  # noqa: BLE001
        # 降级模式下同样放宽兜底商品数量上限，保持与向量召回策略一致
        candidates = get_default_candidates(limit=1000)

    if not candidates:
        print("[backend] /api/recommend 没有召回到候选商品，直接返回空列表")
        return {"query": req.query, "items": [], "llm": {"recommendations": []}}

    agent = DeepSeekAgent()
    prompt = agent.build_prompt(req.user_id, user_profile, candidates, req.query)

    try:
        llm_result = agent.recommend(prompt)
    except Exception:
        llm_result = fallback_rank(candidates)

    # 为前端补齐商品详情和可访问图片 URL，并根据 page / page_size 做分页切片
    products_map = {p["product_id"]: p for p in candidates}

    recs = llm_result.get("recommendations", [])
    # 如果 LLM 没有返回结构化 recommendations，则降级为按 candidates 顺序返回
    if not recs:
        recs = [
            {
                "product_id": p["product_id"],
                "rank": i + 1,
                "reason": "基于你的搜索词和偏好的相似度排序结果。",
            }
            for i, p in enumerate(candidates)
        ]

    # 在分页之前，先按图片进行打散排序，减少同款图片在视觉上的密集堆叠
    recs = diversify_by_image(recs, products_map)

    start = (req.page - 1) * req.page_size
    end = start + req.page_size

    final_items: list[dict[str, Any]] = []
    for rec in recs[start:end]:
        pid = rec.get("product_id")
        p = products_map.get(pid)
        if not p:
            continue
        final_items.append(
            {
                "product_id": pid,
                "name": p.get("name"),
                "price": p.get("price"),
                "category": p.get("category"),
                "description": p.get("description"),
                "image_url": f"/static/images/{Path(p.get('image_path', '')).name}",
                "reason": rec.get("reason", ""),
                "rank": rec.get("rank", 0),
            }
        )

    print(
        "[backend] /api/recommend 返回结果概览：",
        {
            "page": req.page,
            "page_size": req.page_size,
            "items_len": len(final_items),
            "llm_rec_len": len(recs),
        },
    )
    return {"query": req.query, "items": final_items, "llm": llm_result}


class ChatRequest(BaseModel):
    user_id: str
    message: str


@app.post("/api/ai_chat")
def ai_chat(req: ChatRequest) -> dict[str, Any]:
    """
    极简版 AI 导购对话接口：
    - 使用与 /api/recommend 相同的召回逻辑
    - 返回一段自然语言回复 + product_suggestions 列表
    """
    # 直接复用 recommend 的候选集逻辑
    print(
        "[backend] /api/ai_chat 收到请求：",
        {
            "user_id": req.user_id,
            "message": (req.message[:80] + "...") if len(req.message) > 80 else req.message,
        },
    )
    try:
        # 首选向量召回，若失败或为空则回退到静态候选集
        candidates = retrieve_top_k(query=req.message, top_k=6)
        if not candidates:
            raise RuntimeError("Empty candidates from vector DB for ai_chat.")
    except Exception:  # noqa: BLE001
        candidates = get_default_candidates(limit=6)

    if not candidates:
        print("[backend] /api/ai_chat 没有召回到候选商品")
        return {
            "reply": "我暂时没有找到与之匹配的商品，但后续会为你补充更多货品，请稍后再试。",
            "product_suggestions": [],
        }

    products_brief = [
        {
            "product_id": p.get("product_id"),
            "name": p.get("name"),
            "price": p.get("price"),
            "image_url": f"/static/images/{Path(p.get('image_path', '')).name}",
        }
        for p in candidates[:4]
    ]

    reply = (
        "我根据你的描述，从多模态特征空间中为你挑选了一批更匹配的候选商品，"
        "你可以在右侧推荐瀑布流中查看详情并继续微调偏好。"
    )

    print(
        "[backend] /api/ai_chat 返回结果概览：",
        {"suggestion_count": len(products_brief), "has_query_suggestion": bool(req.message)},
    )
    return {
        "reply": reply,
        "product_suggestions": products_brief,
        "query_suggestion": req.message,
    }


@app.post("/api/log_action")
def log_action(req: ActionLogRequest) -> dict[str, Any]:
    print(
        "[backend] /api/log_action 收到行为日志：",
        {
            "user_id": req.user_id,
            "product_id": req.product_id,
            "action": req.action,
            "weight": req.weight,
            "has_extra": bool(req.extra),
        },
    )
    users_doc = read_json(USERS_PROFILE_JSON, default={"users": {}})
    users = users_doc.setdefault("users", {})
    profile = users.setdefault(
        req.user_id,
        {
            "name": req.user_id,
            "core_tags": [],
            "category_preferences": {},
            "recent_activity": [],
            "activity_score": 0,
            "history": [],
        },
    )

    profile.setdefault("history", []).append(
        {
            "product_id": req.product_id,
            "action": req.action,
            "weight": req.weight,
            "extra": req.extra,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
    profile["activity_score"] = min(100, int(profile.get("activity_score", 0)) + 1)
    profile.setdefault("recent_activity", []).append(1)
    profile["recent_activity"] = profile["recent_activity"][-30:]

    atomic_write_json(USERS_PROFILE_JSON, users_doc)
    print(
        "[backend] /api/log_action 已写入日志，当前 activity_score=",
        profile.get("activity_score"),
    )
    return {"message": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("module_backend.main_api:app", host="0.0.0.0", port=8000, reload=True)
