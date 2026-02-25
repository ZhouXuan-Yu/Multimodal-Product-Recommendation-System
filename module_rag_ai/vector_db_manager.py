"""模块二：ChromaDB 向量库读写管理。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import chromadb

from module_rag_ai.multimodal_embedding import ChineseCLIPEmbedder

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_JSON = PROJECT_ROOT / "data" / "meta" / "products.json"
VECTOR_STORE_DIR = PROJECT_ROOT / "data" / "vector_store"


class VectorDBManager:
    """管理本地 ChromaDB 的持久化集合。"""

    def __init__(self, collection_name: str = "products_multimodal"):
        self.client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
        self.collection = self.client.get_or_create_collection(name=collection_name)

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

            text = f"{item['name']}。{item['description']}。分类：{item['category']}"
            vector = embedder.encode_multimodal(image_path=image_path, text=text)

            ids.append(item["product_id"])
            embeddings.append(vector.tolist())
            metadatas.append(
                {
                    "name": item["name"],
                    "category": item["category"],
                    "price": float(item["price"]),
                    "image_path": item["image_path"],
                }
            )
            documents.append(text)

        if ids:
            self.collection.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)
        return len(ids)

    def query_by_text(self, query: str, embedder: ChineseCLIPEmbedder, top_k: int = 3) -> dict[str, Any]:
        """将自然语言查询向量化后检索 Top-K。"""
        query_vector = embedder.encode_text(query).tolist()
        return self.collection.query(query_embeddings=[query_vector], n_results=top_k)


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
