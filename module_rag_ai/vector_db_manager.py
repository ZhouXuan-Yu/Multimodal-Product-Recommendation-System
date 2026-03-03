"""模块二：ChromaDB 向量库读写管理。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Iterable, Tuple

import chromadb

from module_rag_ai.multimodal_embedding import ChineseCLIPEmbedder

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# 统一使用 data/meta/products.json 作为商品主数据源，便于与后端 /api/recommend 保持一致
PRODUCTS_JSON = PROJECT_ROOT / "data" / "meta" / "products.json"
VECTOR_STORE_DIR = PROJECT_ROOT / "data" / "vector_store"


class VectorDBManager:
    """管理本地 ChromaDB 的持久化集合。"""

    def __init__(self, collection_name: str = "products_multimodal"):
        self.client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def _build_record(
        self,
        item: dict[str, Any],
        embedder: ChineseCLIPEmbedder,
    ) -> Tuple[str, list[float], dict[str, Any], str] | None:
        """单条商品 → 向量与元数据的构建逻辑（可被多线程复用）。"""
        # 兼容不同数据字段：processed/products.json 使用 title；早期版本可能是 name
        title = item.get("title") or item.get("name") or ""
        description = item.get("description") or item.get("description_text") or ""
        category = item.get("category") or ""
        text = f"{title}。{description}。分类：{category}"

        image_path_value = item.get("image_path")
        image_path = PROJECT_ROOT / image_path_value if image_path_value else None

        # 图片可选：如果找不到图片，就退化为纯文本向量，避免整条商品被跳过
        if image_path is not None and image_path.exists():
            vector = embedder.encode_multimodal(image_path=image_path, text=text)
        else:
            vector = embedder.encode_text(text)

        metadata = {
            "name": title,
            "category": category,
            "price": float(item.get("price", 0.0)),
            "image_path": image_path_value,
        }
        return item["product_id"], vector.tolist(), metadata, text

    def upsert_products(
        self,
        products: list[dict[str, Any]],
        embedder: ChineseCLIPEmbedder,
        max_workers: int = 4,
        batch_size: int = 256,
    ) -> int:
        """将商品多模态向量与元数据写入向量库。

        - 使用线程池并行编码文本/图片，以提升 3000+ 商品场景下的入库速度。
        - 为了避免对 Chroma 产生过多小批次写入，仍然按批次进行 upsert。
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        if not products:
            return 0

        # 预先按 product_id 去重，避免 Chroma 报错 "Expected IDs to be unique"
        unique_products: dict[str, dict[str, Any]] = {}
        for item in products:
            pid = item.get("product_id")
            if not pid:
                continue
            unique_products[pid] = item
        products_dedup = list(unique_products.values())

        if len(products_dedup) != len(products):
            print(
                f"[vector_db] 检测到重复或缺失 product_id 的商品，"
                f"原始数量={len(products)}，去重后={len(products_dedup)}"
            )

        products = products_dedup

        max_workers = max(1, max_workers)
        total = 0

        def iter_batches(items: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
            for i in range(0, len(items), size):
                yield items[i : i + size]

        for batch in iter_batches(products, batch_size):
            ids: list[str] = []
            embeddings: list[list[float]] = []
            metadatas: list[dict[str, Any]] = []
            documents: list[str] = []

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_idx = {
                    executor.submit(self._build_record, item, embedder): idx for idx, item in enumerate(batch)
                }
                # 按完成顺序收集结果，保留全部有效记录
                for future in as_completed(future_to_idx):
                    record = future.result()
                    if record is None:
                        continue
                    pid, vec, meta, doc = record
                    ids.append(pid)
                    embeddings.append(vec)
                    metadatas.append(meta)
                    documents.append(doc)

            if ids:
                self.collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=documents,
                )
                total += len(ids)

        return total

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
