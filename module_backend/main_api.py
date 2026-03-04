"""模块三：FastAPI 后端 + 本地 Chroma 检索 + DeepSeek RAG。"""

from __future__ import annotations

import json
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import defaultdict, deque

import numpy as np
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field

from module_rag_ai.deepseek_agent import DeepSeekAgent
from module_rag_ai.multimodal_embedding import ChineseCLIPEmbedder
from module_rag_ai.vector_db_manager import VectorDBManager, load_products
from module_rag_ai.model_worker import get_global_clip_worker
from module_rag_ai.order_agent import Order, OrderAgent, OrderItem, OrderStatus
from core.user_insight_engine import UserInsightEngine, UserBehaviorEvent

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
PRODUCTS_JSON = DATA_DIR / "meta" / "products.json"
USERS_PROFILE_JSON = DATA_DIR / "meta" / "users_profile.json"
ORDERS_JSON = DATA_DIR / "meta" / "orders.json"
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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    全局异常处理：捕获未处理错误并打印详细日志，方便排查 500。
    """
    print(
        "[backend] 全局异常捕获：",
        {
            "path": str(request.url.path),
            "error": repr(exc),
        },
    )
    traceback.print_exc()

    if isinstance(exc, HTTPException):
        # 保持 HTTPException 的原始语义
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "error": str(exc),
        },
    )


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
    action: str = Field(..., examples=["click", "view", "like", "dislike", "purchase"])
    # 停留时长（秒），用于加强行为权重感知
    dwell_time: float | None = Field(default=None, description="本次交互的停留时长（秒）")
    # 可选的权重和标签，用于个性化推荐算法
    weight: float | None = Field(default=None, description="该行为在个性化模型中的附加权重（可选）")
    # 前端可附加额外上下文（例如：来源页面、曝光位、实验分桶等）
    extra: dict[str, Any] | None = Field(default=None, description="可选的扩展上下文信息")


class InsightReport(BaseModel):
    """DeepSeek 自动化用户画像报告输出结构。"""

    user_id: str
    summary: str
    generated_at: datetime
    # 可选：让前端在需要时展示模型引用的关键信息
    top_categories: List[Dict[str, Any]] = []
    top_tags: List[Dict[str, Any]] = []


class OrderItemModel(BaseModel):
    product_id: str
    quantity: int = Field(1, ge=1)


class OrderPreviewRequest(BaseModel):
    user_id: str
    items: List[OrderItemModel]
    currency: str = "CNY"
    note: str | None = None


class CreateOrderRequest(OrderPreviewRequest):
    """创建订单请求，与预览结构一致."""


class PayOrderRequest(BaseModel):
    order_id: str
    payment_channel: str = Field(..., examples=["mock_pay", "alipay", "wechat"])


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


def _load_orders_doc() -> dict[str, Any]:
    """读取本地订单 JSON 文档，结构固定为 {\"orders\": {order_id: {...}}}。"""
    doc = read_json(ORDERS_JSON, default={"orders": {}})
    if not isinstance(doc, dict):
        doc = {"orders": {}}
    doc.setdefault("orders", {})
    return doc


def _save_orders_doc(doc: dict[str, Any]) -> None:
    atomic_write_json(ORDERS_JSON, doc)


def _order_from_record(rec: dict[str, Any]) -> Order:
    """将持久化字典还原为 Order 对象。"""
    items_raw = rec.get("items", []) or []
    items: list[OrderItem] = []
    for it in items_raw:
        items.append(
            OrderItem(
                product_id=str(it.get("product_id")),
                quantity=int(it.get("quantity", 1)),
                unit_price=float(it.get("unit_price", 0.0)),
            )
        )

    return Order(
        order_id=str(rec.get("order_id")),
        user_id=str(rec.get("user_id")),
        status=str(rec.get("status") or "pending"),  # type: ignore[arg-type]
        items=items,
        total_amount=float(rec.get("total_amount", 0.0)),
        currency=str(rec.get("currency") or "CNY"),
        created_at=str(rec.get("created_at") or datetime.utcnow().isoformat()),
        updated_at=str(rec.get("updated_at") or datetime.utcnow().isoformat()),
        note=rec.get("note"),
        payment_channel=rec.get("payment_channel"),
        paid_at=rec.get("paid_at"),
    )


def _generate_order_id(user_id: str) -> str:
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")[:-3]
    safe_uid = "".join(ch for ch in user_id if ch.isalnum() or ch in ("-", "_"))[:16]
    return f"local-{safe_uid}-{ts}"


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

    db = VectorDBManager()
    worker = get_global_clip_worker()

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

    # 使用批处理 Worker 将 0.1s 内的查询合并为一个 batch 送入 GPU
    query_vec = worker.encode_query(query)
    result = db.collection.query(
        query_embeddings=[query_vec.tolist()],
        n_results=top_k,
        include=["ids"],
    )
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

    try:
        # 初始化向量库与模型 Worker，任何异常都视为本次检索不可用，直接返回空列表，避免 500
        db = VectorDBManager()
        worker = get_global_clip_worker()

        collection = db.collection
        has_count = hasattr(collection, "count")
        if has_count and collection.count() == 0:
            return []
    except Exception as exc:  # noqa: BLE001
        print("[backend] VectorDB / 模型初始化失败（rag_search），将返回空列表:", exc)
        return []

    try:
        # 使用批处理 Worker 将查询编码为向量，并在 Chroma 中检索
        query_vec = worker.encode_query(query)
        result = db.collection.query(
            query_embeddings=[query_vec.tolist()],
            n_results=top_k,
            include=["distances", "metadatas", "documents", "ids"],
        )
    except Exception as exc:  # noqa: BLE001
        # 任何编码/检索阶段的异常，都打印日志并返回空列表，前端不会收到 500
        print("[backend] VectorDB 检索失败（rag_search），将返回空列表:", exc)
        return []

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


def _enrich_order_for_frontend(order: Order, products_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """为前端补齐订单里的商品详情和图片 URL。"""
    base = order.to_dict()
    items_view: list[dict[str, Any]] = []
    for it in order.items:
        p = products_map.get(it.product_id, {})
        items_view.append(
            {
                "product_id": it.product_id,
                "quantity": it.quantity,
                "unit_price": it.unit_price,
                "name": p.get("name"),
                "price": p.get("price"),
                "category": p.get("category"),
                "image_url": (
                    f"/static/images/{Path(p.get('image_path', '')).name}"
                    if p.get("image_path")
                    else None
                ),
            }
        )
    base["items"] = items_view
    return base


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


@app.post("/api/orders/preview")
def preview_order(req: OrderPreviewRequest) -> dict[str, Any]:
    """
    订单预览接口：
    - 不落盘，只计算总价与订单摘要，前端确认后再调用创建接口。
    """
    products_map = load_products_map()
    if not products_map:
        raise HTTPException(status_code=400, detail="本地商品数据为空，请先准备 data/meta/products.json")

    items: list[OrderItem] = []
    total = 0.0
    for it in req.items:
        p = products_map.get(it.product_id)
        if not p:
            raise HTTPException(status_code=404, detail=f"商品不存在: {it.product_id}")
        price = float(p.get("price", 0.0))
        if price < 0:
            raise HTTPException(status_code=400, detail=f"无效价格: {it.product_id}")
        total += price * it.quantity
        items.append(OrderItem(product_id=it.product_id, quantity=it.quantity, unit_price=price))

    now = datetime.utcnow().isoformat()
    order = Order(
        order_id="preview",
        user_id=req.user_id,
        status="pending",
        items=items,
        total_amount=total,
        currency=req.currency,
        created_at=now,
        updated_at=now,
        note=req.note,
    )

    agent = OrderAgent(enable_llm=True)
    users_doc = read_json(USERS_PROFILE_JSON, default={"users": {}})
    user_profile = users_doc.get("users", {}).get(req.user_id, {})
    summary = agent.summarize_order(order, user_profile=user_profile, products_map=products_map)

    return {
        "order": _enrich_order_for_frontend(order, products_map),
        "summary": summary,
    }


@app.post("/api/orders")
def create_order(req: CreateOrderRequest) -> dict[str, Any]:
    """创建订单并持久化到本地 JSON。"""
    products_map = load_products_map()
    if not products_map:
        raise HTTPException(status_code=400, detail="本地商品数据为空，请先准备 data/meta/products.json")

    items: list[OrderItem] = []
    total = 0.0
    for it in req.items:
        p = products_map.get(it.product_id)
        if not p:
            raise HTTPException(status_code=404, detail=f"商品不存在: {it.product_id}")
        price = float(p.get("price", 0.0))
        if price < 0:
            raise HTTPException(status_code=400, detail=f"无效价格: {it.product_id}")
        total += price * it.quantity
        items.append(OrderItem(product_id=it.product_id, quantity=it.quantity, unit_price=price))

    now = datetime.utcnow().isoformat()
    order_id = _generate_order_id(req.user_id)
    order = Order(
        order_id=order_id,
        user_id=req.user_id,
        status="pending",
        items=items,
        total_amount=total,
        currency=req.currency,
        created_at=now,
        updated_at=now,
        note=req.note,
    )

    doc = _load_orders_doc()
    doc["orders"][order_id] = order.to_dict()
    _save_orders_doc(doc)

    agent = OrderAgent(enable_llm=True)
    users_doc = read_json(USERS_PROFILE_JSON, default={"users": {}})
    user_profile = users_doc.get("users", {}).get(req.user_id, {})
    summary = agent.summarize_order(order, user_profile=user_profile, products_map=products_map)

    return {
        "order": _enrich_order_for_frontend(order, products_map),
        "summary": summary,
    }


@app.post("/api/orders/pay")
def pay_order(req: PayOrderRequest) -> dict[str, Any]:
    """
    模拟支付接口：
    - 本地环境下不对接真实支付，只将状态从 pending 切到 paid。
    """
    doc = _load_orders_doc()
    raw = doc["orders"].get(req.order_id)
    if not raw:
        raise HTTPException(status_code=404, detail="订单不存在")

    order = _order_from_record(raw)
    agent = OrderAgent(enable_llm=False)
    try:
        order = agent.transit(order, "paid")  # type: ignore[arg-type]
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    order.payment_channel = req.payment_channel
    doc["orders"][order.order_id] = order.to_dict()
    _save_orders_doc(doc)

    products_map = load_products_map()
    return {"order": _enrich_order_for_frontend(order, products_map)}


@app.get("/api/orders/{order_id}")
def get_order(order_id: str) -> dict[str, Any]:
    doc = _load_orders_doc()
    raw = doc["orders"].get(order_id)
    if not raw:
        raise HTTPException(status_code=404, detail="订单不存在")

    order = _order_from_record(raw)
    products_map = load_products_map()
    return {"order": _enrich_order_for_frontend(order, products_map)}


@app.get("/api/orders")
def list_orders(user_id: str | None = None, limit: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
    """
    订单列表：
    - 可选按 user_id 过滤；
    - 结果按创建时间倒序。
    """
    doc = _load_orders_doc()
    all_orders: list[Order] = []
    for rec in doc["orders"].values():
        try:
            o = _order_from_record(rec)
        except Exception:  # noqa: BLE001
            continue
        if user_id and o.user_id != user_id:
            continue
        all_orders.append(o)

    all_orders.sort(key=lambda x: x.created_at, reverse=True)
    all_orders = all_orders[:limit]

    products_map = load_products_map()
    return {
        "orders": [_enrich_order_for_frontend(o, products_map) for o in all_orders],
        "total": len(all_orders),
    }


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

    is_new_user = not bool(profile)

    if is_new_user:
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
    else:
        # 对已有用户画像，补充高级可选字段：visual_style / contribution / intent_peaks
        try:
            products_map = load_products_map()
            history: list[dict[str, Any]] = (
                profile.get("history", []) if isinstance(profile, dict) else []
            )

            # 使用已有的行为聚合逻辑，兼容近 14 天的行为趋势
            agg = _aggregate_behavior_for_insight(history, products_map, days=14)

            # 1) 视觉审美向量：从近期风格标签与品类粗略映射到 5 维审美空间
            visual_style = _compute_visual_style_from_behavior(agg)
            if visual_style:
                profile.setdefault("visual_style", visual_style)

            # 2) 推荐来源贡献度：从行为日志中的 extra.source 估算
            contribution = _estimate_recommendation_contribution(history)
            if contribution:
                profile.setdefault("contribution", contribution)

            # 3) 意图波峰：在趋势中识别高峰日，并调用 DeepSeek 生成摘要
            intent_peaks = _build_intent_peaks_from_history(
                user_id=user_id,
                history=history,
                timeseries=agg.get("timeseries") or [],
                products_map=products_map,
            )
            if intent_peaks:
                profile.setdefault("intent_peaks", intent_peaks)
        except Exception as exc:  # noqa: BLE001
            # 所有高级字段均为「可选增强」，任何异常都不影响基础画像返回
            print(
                "[backend] /api/user_profile 生成高级画像字段失败（已忽略）：",
                {"user_id": user_id, "error": repr(exc)},
            )
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


def _aggregate_behavior_for_insight(
    history: list[dict[str, Any]],
    products_map: dict[str, dict[str, Any]],
    days: int = 7,
) -> Dict[str, Any]:
    """
    针对最近 N 天行为，做品类/标签/活跃度聚合，支撑 AI 画像总结与图表展示。
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    by_category: dict[str, int] = {}
    by_tag: dict[str, int] = {}
    by_day: dict[str, int] = {}

    for h in reversed(history):
        try:
            ts_raw = h.get("timestamp")
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")) if ts_raw else None
        except Exception:  # noqa: BLE001
            ts = None

        if ts and ts < cutoff:
            continue

        pid = h.get("product_id")
        product = products_map.get(pid, {})
        cat = product.get("category") or "unknown"
        tags = product.get("tags") or product.get("style_tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        by_category[cat] = by_category.get(cat, 0) + 1
        for t in tags:
            by_tag[t] = by_tag.get(t, 0) + 1

        if ts:
            day = ts.date().isoformat()
            by_day[day] = by_day.get(day, 0) + 1

    def _top_k(mapping: dict[str, int], k: int = 5) -> List[Dict[str, Any]]:
        return [
            {"name": name, "value": value}
            for name, value in sorted(mapping.items(), key=lambda x: x[1], reverse=True)[:k]
        ]

    return {
        "by_category": _top_k(by_category, 5),
        "by_tag": _top_k(by_tag, 10),
        "timeseries": [{"day": d, "value": v} for d, v in sorted(by_day.items(), key=lambda x: x[0])],
    }


def _pca_2d(vectors: list[np.ndarray]) -> list[dict[str, float]]:
    """
    对一组高维向量做简单 PCA 降维到 2D，用于可视化“向量偏移轨迹”。

    返回结果与输入向量一一对应，每个元素形如 {"x": float, "y": float}。
    """
    if not vectors:
        return []
    if len(vectors) == 1:
        # 单点无法做 PCA，直接投到原点
        return [{"x": 0.0, "y": 0.0}]

    mat = np.stack(vectors).astype(np.float32)
    mean = mat.mean(axis=0, keepdims=True)
    centered = mat - mean

    # 协方差矩阵维度为 (D, D)，在 D=512 等场景下仍可接受
    cov = np.cov(centered, rowvar=False)
    # 使用 eigh 获得特征向量，按特征值从小到大排序
    eigvals, eigvecs = np.linalg.eigh(cov)
    # 取最大的两个特征向量作为投影基
    idx = np.argsort(eigvals)[-2:]
    basis = eigvecs[:, idx]  # shape: (D, 2)
    coords = centered @ basis  # shape: (N, 2)

    return [{"x": float(x), "y": float(y)} for x, y in coords]


def _semantic_shift_label(product: dict[str, Any], action: str) -> str:
    """
    规则版“语义意图偏移”标签，用于在向量轨迹上标注：
    - 示例：更偏向高性能数码 / 转向生活品质 / 更关注基础性价比 等。

    说明：这里只做轻量级规则推断，避免为每次事件调用 LLM 带来的延迟与成本。
    """
    category = str(product.get("category") or "")
    tags_raw = product.get("tags") or product.get("style_tags") or []
    if isinstance(tags_raw, str):
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
    else:
        tags = [str(t) for t in tags_raw]

    action = str(action or "").lower()

    # 基于品类 & 标签的粗粒度规则
    if any(k in category for k in ("数码", "电子", "电脑", "手机")):
        if any("高性能" in t or "游戏" in t or "旗舰" in t for t in tags):
            return "该行为让画像更偏向高性能数码与性能导向。"
        return "该行为让画像更靠近数码电子类偏好。"

    if any(k in category for k in ("家居", "家装", "家电")):
        if any("舒适" in t or "品质" in t or "生活" in t for t in tags):
            return "该行为让画像更偏向生活品质与居家体验。"
        return "该行为让画像更靠近家居生活相关的需求。"

    if any(k in category for k in ("服饰", "鞋", "包", "配饰")):
        if any("通勤" in t or "商务" in t for t in tags):
            return "该行为让画像更偏向通勤商务穿搭场景。"
        if any("户外" in t or "运动" in t or "机能" in t for t in tags):
            return "该行为让画像更偏向户外机能与运动场景。"
        return "该行为让画像更靠近服饰穿搭类偏好。"

    if any(k in category for k in ("美妆", "个护")):
        return "该行为让画像更偏向美妆个护与自我护理场景。"

    # 若是强正向反馈，给出更坚定的措辞
    if action in ("like", "favorite", "purchase"):
        return "该行为强化了当前兴趣方向，对后续个性化推荐影响较大。"
    if action == "dislike":
        return "该行为让画像远离该类商品风格，有助于减少类似推荐。"

    return "该行为对画像有轻微影响，用于微调近期兴趣方向。"


def _build_vector_drift_for_user(
    user_id: str,
    max_events: int = 50,
) -> dict[str, Any]:
    """
    构建“向量偏移轨迹”数据：
    - 基于最近 max_events 条行为，模拟 persona_vector 的连续更新（不写回数据库）；
    - 对所有 persona 向量做 2D PCA 降维，供前端画“向量轨迹图”；
    - 每条边提供向量位移大小（范数）与规则版语义解释，便于前端做 Tooltip。
    """
    users_doc = read_json(USERS_PROFILE_JSON, default={"users": {}})
    profile: Dict[str, Any] = users_doc.get("users", {}).get(user_id, {})
    history: list[dict[str, Any]] = profile.get("history", []) if isinstance(profile, dict) else []

    if not history:
        return {"user_id": user_id, "points": [], "segments": []}

    # 按时间排序，取最近 max_events 条
    def _parse_ts(raw: str | None) -> datetime:
        if not raw:
            return datetime.utcnow()
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            return datetime.utcnow()

    history_sorted = sorted(history, key=lambda h: _parse_ts(h.get("timestamp")))  # type: ignore[arg-type]
    history_tail = history_sorted[-max_events:]

    vdb = VectorDBManager()
    engine = UserInsightEngine(vector_db=vdb)

    # 初始画像（若不存在则在第一次成功事件时以商品向量为起点）
    current_vec = engine.get_persona_vector(user_id)

    persona_vectors: list[np.ndarray] = []
    steps_meta: list[dict[str, Any]] = []

    def _norm(v: np.ndarray) -> np.ndarray:
        n = float(np.linalg.norm(v))
        if n <= 0:
            return v
        return v / n

    for ev in history_tail:
        ts_raw = ev.get("timestamp")
        ts = _parse_ts(ts_raw)
        action = str(ev.get("action") or "")
        pid = str(ev.get("product_id") or "")

        # 从商品向量库中取出对应商品向量
        try:
            item_vec_res = vdb.collection.get(ids=[pid], include=["embeddings", "metadatas"])
            emb_list = item_vec_res.get("embeddings") or []
            meta_list = item_vec_res.get("metadatas") or []
        except Exception:
            emb_list = []
            meta_list = []

        if not emb_list or not emb_list[0]:
            # 没有商品向量时，只记录一个“无位移”的节点，便于还原行为时间线
            if current_vec is not None:
                persona_vectors.append(current_vec.copy())
                steps_meta.append(
                    {
                        "timestamp": ts.isoformat(),
                        "action": action,
                        "product_id": pid,
                        "product": {},
                        "delta_norm": 0.0,
                        "semantic_shift": "该行为未参与向量更新（缺少商品向量）。",
                    }
                )
            continue

        item_vec = np.asarray(emb_list[0], dtype=np.float32)
        item_vec = _norm(item_vec)
        product_meta = meta_list[0] if meta_list else {}

        # 若当前尚无画像，则以该商品向量为起点
        if current_vec is None:
            current_vec = item_vec.copy()

        event = UserBehaviorEvent(
            user_id=user_id,
            product_id=pid,
            action_type=action,
            timestamp=ts,
            dwell_time=float(ev.get("dwell_time") or 0.0),
        )

        eta = engine.compute_effective_lr(event)
        if eta <= 0.0:
            # 学习率过小，视为对画像影响可忽略
            persona_vectors.append(current_vec.copy())
            steps_meta.append(
                {
                    "timestamp": ts.isoformat(),
                    "action": action,
                    "product_id": pid,
                    "product": product_meta,
                    "delta_norm": 0.0,
                    "semantic_shift": "该行为对画像影响极小，可忽略。",
                }
            )
            continue

        base_w = engine._base_weight(action)  # type: ignore[arg-type]
        old_vec = current_vec.copy()
        if base_w >= 0:
            new_vec = (1.0 - eta) * old_vec + eta * item_vec
        else:
            new_vec = old_vec - eta * item_vec
        new_vec = _norm(new_vec.astype(np.float32))

        delta = new_vec - old_vec
        delta_norm = float(np.linalg.norm(delta))
        current_vec = new_vec

        persona_vectors.append(current_vec.copy())
        steps_meta.append(
            {
                "timestamp": ts.isoformat(),
                "action": action,
                "product_id": pid,
                "product": product_meta,
                "delta_norm": round(delta_norm, 6),
                "semantic_shift": _semantic_shift_label(product_meta, action),
            }
        )

    if not persona_vectors:
        return {"user_id": user_id, "points": [], "segments": []}

    coords = _pca_2d(persona_vectors)

    points: list[dict[str, Any]] = []
    segments: list[dict[str, Any]] = []
    for idx, (meta, coord) in enumerate(zip(steps_meta, coords, strict=False)):
        pt = {
            "step": idx,
            "timestamp": meta["timestamp"],
            "x": coord["x"],
            "y": coord["y"],
            "action": meta["action"],
            "product_id": meta["product_id"],
            "delta_norm": meta["delta_norm"],
        }
        points.append(pt)

        if idx == 0:
            continue
        segments.append(
            {
                "from_step": idx - 1,
                "to_step": idx,
                "product_id": meta["product_id"],
                "action": meta["action"],
                "product": meta["product"],
                "delta_norm": meta["delta_norm"],
                "semantic_shift": meta["semantic_shift"],
            }
        )

    return {
        "user_id": user_id,
        "points": points,
        "segments": segments,
    }


def _build_sankey_for_user(
    user_id: str,
    limit: int = 500,
) -> dict[str, Any]:
    """
    构建“多模态行为路径”桑基图数据：
    - 节点层级示例：搜索关键词/入口 -> 商品详情 -> 最终反馈(action)；
    - 支持从 extra.source / extra.query 等字段中提取“入口语义”。
    """
    users_doc = read_json(USERS_PROFILE_JSON, default={"users": {}})
    users = users_doc.get("users", {})
    profile: Dict[str, Any] = users.get(user_id, {})
    history: list[dict[str, Any]] = profile.get("history", []) if isinstance(profile, dict) else []

    if not history:
        return {"user_id": user_id, "nodes": [], "links": []}

    products_map = load_products_map()

    # 为了兼顾性能与可视化可读性，仅取最近 limit 条行为
    sliced = list(reversed(history))[:limit]

    node_index: dict[str, int] = {}
    nodes: list[dict[str, Any]] = []
    links_counter: dict[tuple[str, str], int] = {}

    def _node_id(name: str) -> int:
        if name not in node_index:
            node_index[name] = len(nodes)
            nodes.append({"name": name})
        return node_index[name]

    def _source_label(extra: dict[str, Any]) -> str:
        src = str(extra.get("source") or extra.get("channel") or "").lower()
        query = str(extra.get("query") or extra.get("search_term") or "").strip()
        if query:
            return f"搜索：{query}"
        if "image" in src or "gallery" in src or "feed" in src:
            return "图片瀑布流"
        if "recommend" in src or "persona" in src:
            return "个性化推荐入口"
        if "direct" in src:
            return "直接访问/收藏夹"
        return "其他入口"

    def _target_label(action: str) -> str:
        mapping = {
            "view": "浏览",
            "click": "点击",
            "like": "点赞/喜欢",
            "favorite": "收藏",
            "dislike": "不感兴趣",
            "purchase": "下单/购买",
        }
        return mapping.get(action, action or "未知行为")

    for ev in sliced:
        action = str(ev.get("action") or "")
        pid = str(ev.get("product_id") or "")
        extra = ev.get("extra") or {}
        product = products_map.get(pid, {})

        src_name = _source_label(extra)
        product_name = str(product.get("name") or pid or "未知商品")
        mid_name = f"商品详情：{product_name}"
        tgt_name = _target_label(action)

        # 三段路径：入口 -> 商品详情 -> 行为
        for a, b in ((src_name, mid_name), (mid_name, tgt_name)):
            key = (a, b)
            links_counter[key] = links_counter.get(key, 0) + 1

    # 将计数转换为节点/边列表
    links: list[dict[str, Any]] = []
    for (src, tgt), value in links_counter.items():
        src_id = _node_id(src)
        tgt_id = _node_id(tgt)
        links.append({"source": src_id, "target": tgt_id, "value": value})

    return {"user_id": user_id, "nodes": nodes, "links": links}


def _build_semantic_period_payload(
    *,
    label: str,
    history: list[dict[str, Any]],
    products_map: dict[str, dict[str, Any]],
    start: str | None,
    end: str | None,
) -> dict[str, Any]:
    """
    为“语义差分对比”构建单个时间段的输入结构。

    说明：
    - 这里不直接计算高维 embedding 重心，而是更多依赖商品类目与标签的语义信息；
      对于 DeepSeek 来说，类目 + 语义标签 + 权重已足够支持“兴趣中心迁移”的自然语言分析。
    - 若需要，可在后续版本中接入真实向量重心（例如从 user_personas 或商品向量中抽样计算）。
    """
    start_dt = parse_iso_date(start)
    end_dt = parse_iso_date(end)
    if end_dt and len(end or "") == 10:
        end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)

    def _parse_ts(raw: str | None) -> datetime | None:
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:  # noqa: BLE001
            return None

    # 过滤该时间段内的行为
    events: list[dict[str, Any]] = []
    for h in history:
        ts_raw = h.get("timestamp")
        ts = _parse_ts(ts_raw)
        if start_dt and ts and ts < start_dt:
            continue
        if end_dt and ts and ts > end_dt:
            continue
        events.append(h)

    # 基础 KPI：事件总数 + 按行为划分的粗略指标
    impressions = 0
    clicks = 0
    conversions = 0
    for ev in events:
        act = str(ev.get("action") or "").lower()
        if act in ("view", "expose", "impression"):
            impressions += 1
        if act in ("click", "detail"):
            clicks += 1
        if act in ("purchase", "order", "pay", "conversion"):
            conversions += 1

    kpis = {
        "events": len(events),
        "impressions": impressions,
        "clicks": clicks,
        "conversions": conversions,
    }

    # Top 商品：按 product_id 聚合，统计权重，并补充类目与语义标签
    by_product: dict[str, dict[str, Any]] = {}
    for ev in events:
        pid = str(ev.get("product_id") or "")
        if not pid:
            continue
        prod = products_map.get(pid, {})
        rec = by_product.setdefault(
            pid,
            {
                "product_id": pid,
                "product_name": prod.get("name"),
                "category": prod.get("category"),
                "semantic_tags": [],
                "weight": 0.0,
            },
        )
        rec["weight"] = float(rec.get("weight", 0.0)) + 1.0

        # 语义标签：优先 tags / style_tags，其次回退到类目
        tags_raw = prod.get("tags") or prod.get("style_tags") or []
        tags: list[str]
        if isinstance(tags_raw, str):
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        elif isinstance(tags_raw, list):
            tags = [str(t) for t in tags_raw if t]
        else:
            tags = []
        if tags:
            existing = set(rec.get("semantic_tags") or [])
            for t in tags:
                if t not in existing:
                    existing.add(t)
            rec["semantic_tags"] = list(existing)
        elif prod.get("category"):
            # 若商品没有显式标签，则使用类目作为弱语义标签
            cat = str(prod.get("category"))
            if cat and cat not in rec.get("semantic_tags", []):
                rec.setdefault("semantic_tags", []).append(cat)

    top_items = sorted(by_product.values(), key=lambda x: x.get("weight", 0.0), reverse=True)[:10]

    # 向量重心：当前版本以占位空列表表示，仅作为字段占位，避免提示词中“字段可能不少于示例”产生歧义。
    # 如需真实向量重心，可在后续版本中扩展为从向量库计算平均 embedding。
    embedding_centroid: list[float] = []

    return {
        "label": label,
        "kpis": kpis,
        "embedding_centroid": embedding_centroid,
        "top_items": top_items,
    }


def _compute_visual_style_from_behavior(agg: Dict[str, Any]) -> Dict[str, float]:
    """
    从聚合后的标签/品类，粗略估算 5 维「视觉审美」画像：
    - 极简 / 技术感 / 商务 / 复古 / 机能

    该向量仅作为前端可视化参考，不参与真实推荐逻辑。
    """
    tags = agg.get("by_tag", []) or []
    categories = agg.get("by_category", []) or []

    # 初始化 5 个维度的计数器
    dims = {"极简": 0.0, "技术感": 0.0, "商务": 0.0, "复古": 0.0, "机能": 0.0}

    def _bump(dim: str, value: float = 1.0) -> None:
        if dim in dims:
            dims[dim] += float(value)

    # 1) 基于标签的显式匹配
    for item in tags:
        name = str(item.get("name") or "").lower()
        value = float(item.get("value") or 1.0)
        if not name:
            continue
        if "极简" in name or "简约" in name or "minimal" in name:
            _bump("极简", value)
        if "科技" in name or "技术" in name or "数码" in name or "future" in name:
            _bump("技术感", value)
        if "商务" in name or "通勤" in name or "office" in name:
            _bump("商务", value)
        if "复古" in name or "怀旧" in name or "vintage" in name:
            _bump("复古", value)
        if "机能" in name or "outdoor" in name or "机能风" in name:
            _bump("机能", value)

    # 2) 基于品类的弱映射，给空白维度一点默认权重
    for item in categories:
        cname = str(item.get("name") or "")
        cval = float(item.get("value") or 1.0)
        if not cname:
            continue
        if "数码" in cname or "电子" in cname:
            _bump("技术感", cval * 0.5)
        if "服饰" in cname or "鞋" in cname or "包" in cname:
            _bump("极简", cval * 0.2)
            _bump("商务", cval * 0.2)
        if "户外" in cname or "运动" in cname:
            _bump("机能", cval * 0.5)

    total = sum(dims.values())
    if total <= 0:
        return {}

    # 归一化到 [0,1]，并保留 2 位小数
    visual_style = {k: round(v / total, 4) for k, v in dims.items()}
    return visual_style


def _estimate_recommendation_contribution(history: list[dict[str, Any]]) -> Dict[str, float]:
    """
    从行为日志中的 extra.source / extra.channel 粗略估算推荐来源贡献度：
    - text_search: 来自文本搜索请求产生的曝光/点击
    - image_browse: 来自图片浏览 / 瀑布流滑动产生的曝光/点击
    - historical_interactions: 从历史画像 / 个性化召回产生的曝光/点击

    若无法从日志中看出明显来源，则返回空 dict，由前端使用默认占比。
    """
    if not history:
        return {}

    text_cnt = 0.0
    image_cnt = 0.0
    hist_cnt = 0.0

    for h in history[-500:]:
        extra = h.get("extra") or {}
        source = str(extra.get("source") or extra.get("channel") or "").lower()
        if not source:
            hist_cnt += 1.0
            continue
        if "search" in source or "query" in source:
            text_cnt += 1.0
        elif "image" in source or "gallery" in source or "feed" in source:
            image_cnt += 1.0
        else:
            hist_cnt += 1.0

    total = text_cnt + image_cnt + hist_cnt
    if total <= 0:
        return {}

    return {
        "text_search": round(text_cnt / total, 4),
        "image_browse": round(image_cnt / total, 4),
        "historical_interactions": round(hist_cnt / total, 4),
    }


def _build_intent_peaks_from_history(
    user_id: str,
    history: list[dict[str, Any]],
    timeseries: list[dict[str, Any]],
    products_map: dict[str, dict[str, Any]],
    max_peaks: int = 3,
) -> List[Dict[str, Any]]:
    """
    在近期行为趋势中识别「意图波峰」，并调用 DeepSeek 生成简要自然语言摘要。

    返回结构：
        [{ "day": "YYYY-MM-DD", "peak_type": str, "summary": str }, ...]
    """
    if not history or not timeseries:
        return []

    # 仅保留按日期排序后最近 30 天的数据
    sorted_ts = sorted(timeseries, key=lambda x: x.get("day") or "")
    recent_ts = sorted_ts[-30:]
    values = np.asarray([float(it.get("value") or 0.0) for it in recent_ts], dtype=float)
    if len(values) < 3 or float(values.max()) <= 0:
        return []

    mean_val = float(values.mean())
    std_val = float(values.std())
    # 阈值：均值 + 0.6 * 标准差，兼顾波动与稳定
    threshold = mean_val + 0.6 * std_val

    candidates: list[tuple[str, float]] = []
    for idx, it in enumerate(recent_ts):
        day = str(it.get("day") or "")
        val = float(it.get("value") or 0.0)
        if not day:
            continue
        if val >= threshold:
            candidates.append((day, val))

    # 若阈值筛选过严，则退回按数值排序取 Top-K
    if not candidates:
        candidates = sorted(((it.get("day"), float(it.get("value") or 0.0)) for it in recent_ts if it.get("day")), key=lambda x: x[1], reverse=True)[
            :max_peaks
        ]

    # 只保留 Top-K 峰值
    candidates = sorted(candidates, key=lambda x: x[1], reverse=True)[:max_peaks]
    peak_days = [c[0] for c in candidates]
    if not peak_days:
        return []

    # 收集每个峰值日期的代表性行为事件（最多 40 条）
    events_by_day: dict[str, list[dict[str, Any]]] = {d: [] for d in peak_days}
    for h in reversed(history):
        ts_raw = h.get("timestamp")
        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")) if ts_raw else None
        except Exception:  # noqa: BLE001
            ts = None
        if not ts:
            continue
        day = ts.date().isoformat()
        if day not in events_by_day:
            continue

        pid = h.get("product_id")
        product = products_map.get(pid, {})
        events_by_day[day].append(
            {
                "timestamp": ts_raw,
                "action": h.get("action"),
                "product_id": pid,
                "product_name": product.get("name"),
                "category": product.get("category"),
                "price": product.get("price"),
            }
        )

    for d in list(events_by_day.keys()):
        events_by_day[d] = events_by_day[d][:40]

    # 调用 DeepSeek 生成结构化波峰摘要（若失败，则使用规则降级）
    agent = DeepSeekAgent()
    prompt_payload: Dict[str, Any] = {
        "user_id": user_id,
        "peaks": [
            {
                "day": day,
                "events": events_by_day.get(day, []),
                "activity_value": float(dict(recent_ts).get(day) or 0.0),
            }
            for day in peak_days
        ],
        "instruction": (
            "你是一名电商用户行为分析师，请基于每个日期的行为事件，识别该时段的主导购物意图波峰，"
            "并为前端可视化提供简要摘要。"
        ),
        "output_schema": {
            "peaks": [
                {
                    "day": "string, 与输入中的 day 完全一致",
                    "peak_type": "string, 例如 research / comparison / purchase / casual_browse 等",
                    "summary": "string, 30~60 字中文摘要，说明该日期用户在做什么、关注什么",
                }
            ]
        },
    }

    try:
        raw = agent._chat(  # noqa: SLF001
            system_prompt=(
                "你是电商用户行为分析师，擅长从行为事件中识别意图波峰。"
                "请严格输出一个 JSON 对象，不要包含 markdown 代码块或多余文字。"
            ),
            user_content=json.dumps(prompt_payload, ensure_ascii=False, indent=2),
            timeout=45,
        )
        parsed = DeepSeekAgent._extract_json(raw)
        peaks = parsed.get("peaks") if isinstance(parsed, dict) else None
        if not isinstance(peaks, list):
            raise ValueError("parsed.peaks is not a list")

        normalized: List[Dict[str, Any]] = []
        for item in peaks:
            day = str(item.get("day") or "")
            if not day or day not in peak_days:
                continue
            summary = str(item.get("summary") or "").strip()
            if not summary:
                continue
            peak_type = str(item.get("peak_type") or "intent_peak")
            normalized.append({"day": day, "peak_type": peak_type, "summary": summary})

        if normalized:
            return normalized
    except Exception as exc:  # noqa: BLE001
        print(
            "[backend] 构建意图波峰 DeepSeek 摘要失败，将使用规则降级：",
            {"user_id": user_id, "error": repr(exc)},
        )

    # 规则降级：仅返回基础结构和通用摘要
    fallback: List[Dict[str, Any]] = []
    for day in peak_days:
        fallback.append(
            {
                "day": day,
                "peak_type": "activity_spike",
                "summary": "该日期的浏览与点击行为明显高于近期平均，可能存在集中调研或强购物意图，可作为重点观察时段。",
            }
        )
    return fallback


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


@app.get("/api/insights/{user_id}/vector_drift")
def get_vector_drift(
    user_id: str,
    max_events: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    """
    向量偏移轨迹接口：
    - 基于 user_profile.json 中的行为 history + Chroma user_personas；
    - 不改写真实画像，只在内存中模拟最近 max_events 条行为驱动下的 persona_vector 变化；
    - 对所有 persona_vector 做 2D PCA 降维，供前端绘制“向量轨迹图”。
    """
    data = _build_vector_drift_for_user(user_id=user_id, max_events=max_events)
    return data


@app.get("/api/insights/{user_id}/behavior_sankey")
def get_behavior_sankey(
    user_id: str,
    limit: int = Query(default=300, ge=50, le=2000),
) -> dict[str, Any]:
    """
    用户多模态行为路径桑基图接口：
    - 节点层级：搜索/入口 -> 商品详情 -> 用户反馈行为；
    - 前端可直接将返回结果映射为 ECharts Sankey 的 nodes + links。
    """
    return _build_sankey_for_user(user_id=user_id, limit=limit)


@app.get("/api/insights/{user_id}/semantic_diff")
def get_semantic_diff(
    user_id: str,
    a_start: str = Query(..., description="本周期开始日期 (YYYY-MM-DD 或 ISO)"),
    a_end: str = Query(..., description="本周期结束日期"),
    b_start: str = Query(..., description="上周期开始日期"),
    b_end: str = Query(..., description="上周期结束日期"),
) -> dict[str, Any]:
    """
    语义化数据对比接口：
    - 对比两个时间窗口内 Top10 商品的语义分布与行为强度；
    - 将结构化 period_a / period_b 作为 DeepSeek 的输入，生成「语义差分看板」所需 JSON；
    - 若 DeepSeek 不可用，则返回规则版的降级结果，字段结构与提示词约定保持一致。
    """
    users_doc = read_json(USERS_PROFILE_JSON, default={"users": {}})
    profile: Dict[str, Any] = users_doc.get("users", {}).get(user_id, {})
    history: list[dict[str, Any]] = profile.get("history", []) if isinstance(profile, dict) else []

    products_map = load_products_map()

    period_a = _build_semantic_period_payload(
        label="本周期",
        history=history,
        products_map=products_map,
        start=a_start,
        end=a_end,
    )
    period_b = _build_semantic_period_payload(
        label="上周期",
        history=history,
        products_map=products_map,
        start=b_start,
        end=b_end,
    )

    prompt_payload: Dict[str, Any] = {
        "period_a": period_a,
        "period_b": period_b,
    }

    system_prompt = (
        "你是一个「用户行为洞察分析师」，负责解释两个时间段内用户兴趣与行为的变化原因，"
        "并输出结构化的数据对比结果 + 自然语言总结。"
        "请严格只返回一个 JSON 对象，字段名固定为 summary_text / focus_shift / semantic_diff_board / health，"
        "不要输出 markdown 代码块或任何额外说明文字。"
    )

    agent = DeepSeekAgent()
    try:
        raw = agent._chat(
            system_prompt=system_prompt,
            user_content=json.dumps(prompt_payload, ensure_ascii=False, indent=2),
            timeout=60,
        )
        parsed = DeepSeekAgent._extract_json(raw)
        if not isinstance(parsed, dict):
            raise ValueError("DeepSeek 输出不是 JSON 对象")
        # 最终直接将结构化 JSON 透传给前端
        return parsed
    except Exception as exc:  # noqa: BLE001
        print(
            "[backend] /api/insights semantic_diff DeepSeek 调用失败，将返回降级结果：",
            {"user_id": user_id, "error": repr(exc)},
        )

        # 规则降级：仅使用基础 KPI 构造一个简洁版「语义差分看板」
        a_events = int(period_a.get("kpis", {}).get("events") or 0)
        b_events = int(period_b.get("kpis", {}).get("events") or 0)
        delta_pct = 0
        if b_events > 0:
            delta_pct = int(round((a_events - b_events) / b_events * 100))

        return {
            "summary_text": (
                "本期与上期在整体行为强度上存在差异，但当前暂无法加载完整的 AI 语义解析。"
                "页面仍基于数值对比为你展示趋势变化，稍后可重试以获得更详细的语义化解读。"
            ),
            "focus_shift": {
                "from_focus": "整体兴趣",
                "to_focus": "整体兴趣",
                "intent_delta_pct": delta_pct,
                "focus_shift_desc": "当前仅展示基础行为变化，语义迁移细节待 AI 分析完成后补充。",
            },
            "semantic_diff_board": [
                {
                    "dimension": "整体行为强度",
                    "weight_before": float(b_events),
                    "weight_after": float(a_events),
                    "delta": float(a_events - b_events),
                    "direction": "up" if a_events > b_events else "down" if a_events < b_events else "flat",
                    "comment": "基于事件数的粗略对比结果，供你先感知趋势方向。",
                }
            ],
            "health": {
                "overall_health": "good" if delta_pct > 0 else "warning" if delta_pct == 0 else "bad",
                "behavior_depth_health": "warning",
                "dimension_health": [
                    {"dimension": "整体行为强度", "status": "good" if delta_pct > 0 else "bad" if delta_pct < 0 else "warning"}
                ],
                "suggested_action": "建议稍后再次刷新页面，以获取完整的 AI 语义差分分析结果。",
            },
        }


@app.get("/api/insights/{user_id}/report", response_model=InsightReport)
def get_insight_report(user_id: str, days: int = Query(default=7, ge=1, le=30)) -> InsightReport:
    """
    DeepSeek 自动化“人话”画像总结。

    输入：
        - 最近 N 天的行为聚合（品类、标签、趋势）；
        - 当前 persona_vector 的预览信息。

    输出：
        - 一段适合直观展示的画像摘要 summary。
    """
    users_doc = read_json(USERS_PROFILE_JSON, default={"users": {}})
    profile: Dict[str, Any] = users_doc.get("users", {}).get(user_id, {})
    history: list[dict[str, Any]] = profile.get("history", []) if isinstance(profile, dict) else []

    products_map = load_products_map()
    agg = _aggregate_behavior_for_insight(history, products_map, days=days)

    # 从画像引擎中拿到 persona_vector 的预览与近期标签/品类
    insight_engine = UserInsightEngine()
    rerank_ctx = insight_engine.build_rerank_context(
        user_id=user_id,
        recent_tags=[x["name"] for x in agg.get("by_tag", [])],
        recent_categories=[x["name"] for x in agg.get("by_category", [])],
    )

    # 构建 DeepSeek Prompt
    agent = DeepSeekAgent()
    prompt_payload: Dict[str, Any] = {
        "user_id": user_id,
        "recent_days": days,
        "behavior_agg": agg,
        "persona_context": rerank_ctx,
        "instruction": (
            "请根据以上结构化信息，用自然、具洞察力的中文写一段 60~120 字的用户画像总结。"
            "避免列举所有细节，突出近期兴趣变化、典型偏好和可能的场景推断。"
        ),
    }
    try:
        raw = agent._chat(  # noqa: SLF001
            system_prompt=(
                "你是一名电商用户运营分析师，擅长把用户行为和画像数据转化为易懂的洞察报告。"
                "请只输出一段自然语言，不要输出 JSON 或 Markdown 代码块。"
            ),
            user_content=json.dumps(prompt_payload, ensure_ascii=False, indent=2),
            timeout=45,
        )
        summary = raw.strip()
    except Exception as exc:  # noqa: BLE001
        print("[backend] 生成 AI 画像总结失败，将返回降级文案：", exc)
        summary = (
            "近期你在本平台的浏览和点击行为呈现出较为集中的兴趣方向，"
            "系统已根据这些线索动态更新你的个性化画像，用于后续推荐和洞察展示。"
        )

    return InsightReport(
        user_id=user_id,
        summary=summary,
        generated_at=datetime.utcnow(),
        top_categories=agg.get("by_category", []),
        top_tags=agg.get("by_tag", []),
    )


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
        print(
            "[backend] /api/recommend 检索阶段异常，将降级为静态候选：",
            {"error": repr(exc)},
        )
        # 降级模式下同样放宽兜底商品数量上限，保持与向量召回策略一致
        candidates = get_default_candidates(limit=1000)

    if not candidates:
        print("[backend] /api/recommend 没有召回到候选商品，直接返回空列表")
        return {"query": req.query, "items": [], "llm": {"recommendations": []}}

    # 画像上下文：从 Chroma user_personas + 行为数据聚合中构造
    products_map = {p["product_id"]: p for p in candidates}
    users_doc = read_json(USERS_PROFILE_JSON, default={"users": {}})
    profile_raw = users_doc.get("users", {}).get(req.user_id, {})
    history: list[dict[str, Any]] = profile_raw.get("history", []) if isinstance(profile_raw, dict) else []

    insight_engine = UserInsightEngine()
    agg = _aggregate_behavior_for_insight(history, products_map, days=7)
    rerank_ctx = insight_engine.build_rerank_context(
        user_id=req.user_id,
        recent_tags=[x["name"] for x in agg.get("by_tag", [])],
        recent_categories=[x["name"] for x in agg.get("by_category", [])],
    )

    agent = DeepSeekAgent()
    # 扩展 Rerank Prompt：注入 persona_vector 预览与近期兴趣点
    prompt_payload = {
        "user_id": req.user_id,
        "query": req.query,
        "user_profile": user_profile,
        "candidates": candidates,
        "persona_context": rerank_ctx,
        "recent_behavior_agg": agg,
        "rules": {
            "target": "输出 Top-N 推荐（N >= 3，允许比页面展示更多以便分页）",
            "must_format": "必须返回 JSON，字段包含 recommendations(list)；每项含 product_id, rank, reason",
            "constraints": [
                "优先贴合 persona_context 中总结的近期关注点与高频品类/标签",
                "结合本次 query 的语义进行再筛选和排序",
                "对于近期多次被 dislike 的风格/品牌，应明显降低排序，必要时可以在 reason 中解释规避原因",
            ],
        },
    }
    prompt = json.dumps(prompt_payload, ensure_ascii=False, indent=2)

    try:
        llm_result = agent.recommend(prompt)
    except Exception as exc:  # noqa: BLE001
        print(
            "[backend] /api/recommend LLM 调用异常，将使用 fallback_rank：",
            {"error": repr(exc)},
        )
        llm_result = fallback_rank(candidates)

    # 为前端补齐商品详情和可访问图片 URL，并根据 page / page_size 做分页切片
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


def _persist_action_and_update_persona(req: ActionLogRequest) -> None:
    """在后台任务中持久化行为日志并更新用户画像，避免阻塞前端主链路。"""
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
            "dwell_time": req.dwell_time,
            "weight": req.weight,
            "extra": req.extra,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
    profile["activity_score"] = min(100, int(profile.get("activity_score", 0)) + 1)
    profile.setdefault("recent_activity", []).append(1)
    profile["recent_activity"] = profile["recent_activity"][-30:]

    atomic_write_json(USERS_PROFILE_JSON, users_doc)

    try:
        vdb = VectorDBManager()
        item_vec_res = vdb.collection.get(ids=[req.product_id], include=["embeddings"])
        item_emb_list = item_vec_res.get("embeddings") or []
        if item_emb_list and item_emb_list[0]:
            item_vec = np.asarray(item_emb_list[0], dtype=np.float32)
            event = UserBehaviorEvent(
                user_id=req.user_id,
                product_id=req.product_id,
                action_type=req.action,
                timestamp=datetime.utcnow(),
                dwell_time=float(req.dwell_time or 0.0),
            )
            insight_engine = UserInsightEngine(vector_db=vdb)
            insight_engine.update_persona_with_event(event, item_vector=item_vec)
        else:
            print(
                "[backend] /api/log_action: 向量库中未找到商品向量，暂不更新 user_personas。product_id=",
                req.product_id,
            )
    except Exception as exc:  # noqa: BLE001
        print("[backend] /api/log_action 更新用户画像失败（将忽略）：", exc)


@app.post("/api/log_action")
def log_action(req: ActionLogRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    print(
        "[backend] /api/log_action 收到行为日志：",
        {
            "user_id": req.user_id,
            "product_id": req.product_id,
            "action": req.action,
            "dwell_time": req.dwell_time,
            "weight": req.weight,
            "has_extra": bool(req.extra),
        },
    )
    background_tasks.add_task(_persist_action_and_update_persona, req)
    return {"message": "accepted"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("module_backend.main_api:app", host="0.0.0.0", port=8000, reload=True)
