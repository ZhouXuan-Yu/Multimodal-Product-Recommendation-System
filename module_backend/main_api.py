"""模块三：FastAPI 后端 + 本地 Chroma 检索 + DeepSeek RAG。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import chromadb
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from module_rag_ai.deepseek_agent import DeepSeekAgent
from module_rag_ai.multimodal_embedding import ChineseCLIPEmbedder

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
PRODUCTS_JSON = DATA_DIR / "meta" / "products.json"
USERS_PROFILE_JSON = DATA_DIR / "meta" / "users_profile.json"
VECTOR_STORE_DIR = DATA_DIR / "vector_store"

app = FastAPI(title="Multimodal Recommendation API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static/images", StaticFiles(directory=str(DATA_DIR / "images")), name="images")


class RecommendRequest(BaseModel):
    user_id: str = Field(..., examples=["user_001"])
    query: str = Field(..., examples=["适合通勤的简约风外套"])


class ActionLogRequest(BaseModel):
    user_id: str
    product_id: str
    action: str = Field(..., examples=["click", "view", "buy"])


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
    """检索层：向量召回 + products.json 反查详情。"""
    products: list[dict[str, Any]] = read_json(PRODUCTS_JSON, default=[])
    product_map = {p["product_id"]: p for p in products}

    if not products:
        return []

    client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
    collection = client.get_or_create_collection(name="products_multimodal")

    embedder = ChineseCLIPEmbedder()
    query_vector = embedder.encode_text(query).tolist()
    result = collection.query(query_embeddings=[query_vector], n_results=top_k)

    ids = result.get("ids", [[]])[0]
    output: list[dict[str, Any]] = []
    for pid in ids:
        p = product_map.get(pid)
        if p:
            output.append(p)
    return output


def fallback_rank(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """当 DeepSeek 不可用时的降级策略。"""
    top3 = candidates[:3]
    return {
        "recommendations": [
            {
                "product_id": p["product_id"],
                "rank": i + 1,
                "reason": "基于本地向量检索结果生成（降级模式）。",
            }
            for i, p in enumerate(top3)
        ]
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/user_profile/{user_id}")
def get_user_profile(user_id: str) -> dict[str, Any]:
    users = read_json(USERS_PROFILE_JSON, default={"users": {}})
    return users.get("users", {}).get(user_id, {})


@app.post("/api/recommend")
def recommend(req: RecommendRequest) -> dict[str, Any]:
    users_doc = read_json(USERS_PROFILE_JSON, default={"users": {}})
    user_profile = users_doc.get("users", {}).get(req.user_id, {})
    candidates = retrieve_top_k(query=req.query, top_k=10)

    if not candidates:
        return {"query": req.query, "items": [], "llm": {"recommendations": []}}

    agent = DeepSeekAgent()
    prompt = agent.build_prompt(req.user_id, user_profile, candidates, req.query)

    try:
        llm_result = agent.recommend(prompt)
    except Exception:
        llm_result = fallback_rank(candidates)

    # 为前端补齐商品详情和可访问图片 URL
    products_map = {p["product_id"]: p for p in candidates}
    final_items = []
    for rec in llm_result.get("recommendations", [])[:3]:
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

    return {"query": req.query, "items": final_items, "llm": llm_result}


@app.post("/api/log_action")
def log_action(req: ActionLogRequest) -> dict[str, Any]:
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
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
    profile["activity_score"] = min(100, int(profile.get("activity_score", 0)) + 1)
    profile.setdefault("recent_activity", []).append(1)
    profile["recent_activity"] = profile["recent_activity"][-30:]

    atomic_write_json(USERS_PROFILE_JSON, users_doc)
    return {"message": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("module_backend.main_api:app", host="0.0.0.0", port=8000, reload=True)
