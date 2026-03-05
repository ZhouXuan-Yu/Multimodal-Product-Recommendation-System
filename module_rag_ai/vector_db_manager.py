"""模块二：ChromaDB 向量库读写管理。"""

from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Any, ClassVar, Optional, Sequence

import chromadb
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_JSON = PROJECT_ROOT / "data" / "meta" / "products.json"
VECTOR_STORE_DIR = PROJECT_ROOT / "data" / "vector_store"

# 允许以脚本形式运行（python module_rag_ai/vector_db_manager.py）时也能正确 import 包内模块
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from module_rag_ai.multimodal_embedding import ChineseCLIPEmbedder


class VectorDBManager:
    """管理本地 ChromaDB 的持久化集合（轻量级单例 + 多模态检索封装）。

    设计要点（对齐 docs/流程.md 第一阶段要求）：
    - 使用 PersistentClient 连接本地向量库目录；
    - 对外暴露：
        - upsert_products：将多模态向量与元数据写入向量库；
        - query_by_text：仅文本向量检索（向后兼容已有代码）；
        - search：增强型多模态检索接口，支持 text + image + filters；
    - 预留 rerank 占位符：当前阶段按距离排序，后续可接入 LLM 语义重排。
    """

    _instance: ClassVar["VectorDBManager"] | None = None

    def __init__(self, collection_name: str = "products_multimodal") -> None:
        # 避免外部误传 None 导致 chromadb 报错
        if not collection_name:
            collection_name = "products_multimodal"
        self.client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
        # 商品多模态向量集合
        self.collection = self.client.get_or_create_collection(name=collection_name)

    # ---- 单例访问入口（新代码优先使用，旧代码保持兼容直接实例化） -----------------
    @classmethod
    def instance(cls, collection_name: str = "products_multimodal") -> "VectorDBManager":
        if cls._instance is None:
            cls._instance = cls(collection_name=collection_name)
        return cls._instance

    # ---- 入库：多模态向量 + 元数据 -------------------------------------------------
    def upsert_products(self, products: list[dict[str, Any]], embedder: ChineseCLIPEmbedder) -> int:
        """将商品多模态向量与元数据写入向量库。"""
        ids: list[str] = []
        embeddings: list[list[float]] = []
        metadatas: list[dict[str, Any]] = []
        documents: list[str] = []

        for item in products:
            image_path = PROJECT_ROOT / item["image_path"]
            if not image_path.exists():
                continue

            text = f"{item.get('name','')}。{item.get('description','')}。分类：{item.get('category','')}"
            vector = embedder.encode_multimodal(image_path=image_path, text=text)

            pid = str(item.get("product_id") or "")
            if not pid:
                continue
            ids.append(pid)
            embeddings.append(vector.tolist())
            metadatas.append(
                {
                    "product_id": pid,
                    "name": item["name"],
                    "category": item["category"],
                    "price": float(item["price"]),
                    "image_path": item["image_path"],
                    "source_url": item.get("source_url", ""),
                }
            )
            documents.append(text)

        if ids:
            self.collection.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)
        return len(ids)

    # ---- 文本检索（向后兼容接口） -------------------------------------------------
    def query_by_text(
        self,
        query: str,
        embedder: ChineseCLIPEmbedder,
        top_k: int = 20,
        include: Optional[list[str]] = None,
        where: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        将自然语言查询向量化后检索 Top-K（保持与旧版兼容的低层封装）。

        支持：
        - include: 控制返回字段（如 ["metadatas", "documents", "distances"]）
        - where: ChromaDB 结构化过滤条件，例如：
            {"category": "笔记本电脑", "price": {"$gte": 3000, "$lte": 6000}}
        """
        query_vector = embedder.encode_text(query).tolist()
        kwargs: dict[str, Any] = {
            "query_embeddings": [query_vector],
            "n_results": top_k,
        }
        if include is not None:
            kwargs["include"] = include
        if where:
            kwargs["where"] = where
        return self.collection.query(**kwargs)

    # ---- 增强版多模态检索（text + image + filters） -------------------------------
    def search(
        self,
        *,
        query_text: str | None = None,
        query_image_path: str | None = None,
        top_k: int = 20,
        filters: Optional[dict[str, Any]] = None,
        include: Optional[Sequence[str]] = None,
        embedder: Optional[ChineseCLIPEmbedder] = None,
        text_weight: float = 0.4,
        image_weight: float = 0.6,
    ) -> list[dict[str, Any]]:
        """
        增强型多模态检索接口：

        - 支持仅文本、仅图片、图文融合三种模式；
        - 支持通过 filters 传入 ChromaDB where 条件（如价格区间、品类）；
        - 返回结构化 Python Dict 列表，包含 id / score / metadata / image_url。

        当前阶段的“score”直接由 1 - distance 得到，后续可在此处挂载 LLM Rerank。
        """
        if not query_text and not query_image_path:
            return []

        emb = embedder or ChineseCLIPEmbedder()

        # 1) 生成查询向量（纯文本 / 纯图片 / 图文融合）
        vecs: list[np.ndarray] = []
        weights: list[float] = []

        if query_text:
            v_text = emb.encode_text(query_text)
            vecs.append(v_text)
            weights.append(max(text_weight, 0.0))

        if query_image_path:
            image_path = Path(query_image_path)
            if image_path.is_file():
                v_img = emb.encode_image(image_path)
                vecs.append(v_img)
                weights.append(max(image_weight, 0.0))

        if not vecs:
            return []

        if len(vecs) == 1:
            query_vec = vecs[0]
        else:
            w = np.asarray(weights, dtype=np.float32)
            if float(w.sum()) <= 0:
                w = np.ones_like(w)
            w = w / w.sum()
            stacked = np.stack(vecs).astype(np.float32)
            query_vec = (w[:, None] * stacked).sum(axis=0)

        # 2) 构造 where 过滤条件
        where = filters or None

        # 3) 调用 Chroma 查询
        chroma_include = list(include) if include is not None else ["metadatas", "distances", "documents"]
        result = self.collection.query(
            query_embeddings=[query_vec.tolist()],
            n_results=top_k,
            include=chroma_include,
            where=where,
        )

        # 4) 预留 rerank 占位：当前按 distance -> score 排序
        return self._format_results(result)

    # ---- 内部工具：结果格式化与占位 rerank -----------------------------------------
    def _format_results(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        """将 Chroma 原始 query 结果格式化为统一结构。"""
        ids = (raw.get("ids") or [[]])[0] or []
        metadatas = (raw.get("metadatas") or [[]])[0] or []
        distances = (raw.get("distances") or [[]])[0] or []

        items: list[dict[str, Any]] = []
        for idx, pid in enumerate(ids):
            meta = metadatas[idx] if idx < len(metadatas) else {}
            dist = None
            try:
                dist = float(distances[idx]) if idx < len(distances) else None
            except Exception:  # noqa: BLE001
                dist = None
            score = (1.0 - dist) if dist is not None else None
            image_path = meta.get("image_path") or ""
            image_url = f"/static/images/{Path(image_path).name}" if image_path else None

            items.append(
                {
                    "id": str(pid),
                    "score": score,
                    "distance": dist,
                    "metadata": meta,
                    "image_url": image_url,
                }
            )

        # 这里按 score 进行一次基础排序，占位未来的 LLM Rerank。
        items.sort(key=lambda x: (x["score"] is None, -(x["score"] or 0.0)))
        return items


def load_products() -> list[dict[str, Any]]:
    if not PRODUCTS_JSON.exists():
        raise FileNotFoundError(f"商品文件不存在: {PRODUCTS_JSON}")
    with PRODUCTS_JSON.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("products.json 格式错误，预期 list")
    return data


def demo_search(query: str = "适合户外运动的黑色鞋子", top_k: int = 3) -> None:
    products = load_products()
    embedder = ChineseCLIPEmbedder()
    db = VectorDBManager()
    upserted = db.upsert_products(products, embedder)
    print(f"已入库商品数: {upserted}")

    result = db.query_by_text(query=query, embedder=embedder, top_k=top_k)
    ids = result.get("ids", [[]])[0]
    print(f"查询词: {query}")
    print("Top-3 商品ID:")
    for pid in ids:
        print(f"- {pid}")


if __name__ == "__main__":
    demo_search()
