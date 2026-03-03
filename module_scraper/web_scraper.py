"""模块一：自动化数据采集与本地初始化。

功能：
1. 初始化 data/ 目录结构。
2. 从公开模拟电商接口抓取商品元数据。
3. 下载商品图片到 data/images/。
4. 生成 data/meta/products.json 与 data/meta/users_profile.json。

运行示例：
    python module_scraper/web_scraper.py --limit 30
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import re
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
IMAGES_DIR = DATA_DIR / "images"
META_DIR = DATA_DIR / "meta"
PRODUCTS_JSON = META_DIR / "products.json"
USERS_PROFILE_JSON = META_DIR / "users_profile.json"

FAKESTORE_API = "https://fakestoreapi.com/products"


@dataclass
class Product:
    """统一的商品元数据结构。"""

    product_id: str
    name: str
    description: str
    price: float
    category: str
    image_path: str
    source_url: str


class LocalDataBootstrapper:
    """负责本地目录初始化与商品采集。"""

    def __init__(self, timeout: int = 15, max_workers: int = 8):
        self.timeout = timeout
        self.logger = logging.getLogger(self.__class__.__name__)
        # 控制下载与处理时的最大线程数，避免开太多线程把网络/显存打爆
        self.max_workers = max_workers

    def reset_data(self) -> None:
        """清理本地旧数据：图片、元数据与向量库目录。

        - data/images/*
        - data/meta/products.json
        - data/meta/users_profile.json
        - data/vector_store/*
        """
        vector_store_dir = DATA_DIR / "vector_store"

        if IMAGES_DIR.exists():
            shutil.rmtree(IMAGES_DIR, ignore_errors=True)
        if vector_store_dir.exists():
            shutil.rmtree(vector_store_dir, ignore_errors=True)
        if PRODUCTS_JSON.exists():
            PRODUCTS_JSON.unlink(missing_ok=True)  # type: ignore[arg-type]
        if USERS_PROFILE_JSON.exists():
            USERS_PROFILE_JSON.unlink(missing_ok=True)  # type: ignore[arg-type]

        self.logger.info("已清理本地旧数据（images/meta/vector_store）。")

    def init_directories(self) -> None:
        """创建本地目录与基础 JSON 文件。"""
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        META_DIR.mkdir(parents=True, exist_ok=True)

        # 初始化商品文件
        if not PRODUCTS_JSON.exists():
            self._atomic_write_json(PRODUCTS_JSON, [])

        # 初始化用户画像文件（给前后端联调一个默认用户）
        if not USERS_PROFILE_JSON.exists():
            default_profile = {
                "users": {
                    "user_001": {
                        "name": "默认用户",
                        "core_tags": ["休闲", "简约"],
                        "category_preferences": {
                            "men's clothing": 0.2,
                            "women's clothing": 0.2,
                            "electronics": 0.3,
                            "jewelery": 0.1,
                            "sports": 0.2,
                        },
                        "recent_activity": [1, 3, 2, 5, 4, 6, 3],
                        "activity_score": 62,
                        "history": [],
                    }
                }
            }
            self._atomic_write_json(USERS_PROFILE_JSON, default_profile)

    def fetch_products(self, limit: int = 30) -> list[dict[str, Any]]:
        """抓取商品基础信息。

        - 优先从 FakeStoreAPI 拉取。
        - 若条目不足，自动进行重复采样并改写 ID 生成更多样本。
        """
        self.logger.info("开始请求模拟电商接口: %s", FAKESTORE_API)
        response = requests.get(FAKESTORE_API, timeout=self.timeout)
        response.raise_for_status()

        items = response.json()
        if not isinstance(items, list):
            raise ValueError("接口返回格式异常，预期为列表")

        if len(items) >= limit:
            return items[:limit]

        # 样本扩增：对现有样本做轻微扰动，满足 20~50 条数据初始化需求。
        expanded: list[dict[str, Any]] = []
        multiplier = (limit // len(items)) + 1
        for i in range(multiplier):
            for item in items:
                clone = dict(item)
                clone["id"] = int(f"{item['id']}{i}")
                clone["title"] = f"{item['title']} #{i + 1}"
                price = float(item.get("price", 99.0))
                clone["price"] = round(price * random.uniform(0.85, 1.15), 2)
                expanded.append(clone)
                if len(expanded) >= limit:
                    return expanded
        return expanded

    def download_image(self, image_url: str, file_name: str) -> str | None:
        """下载图片并返回相对路径。失败时返回 None。"""
        target = IMAGES_DIR / file_name

        # 已存在则跳过下载，直接复用
        if target.exists() and target.stat().st_size > 0:
            return str(target.relative_to(PROJECT_ROOT))

        try:
            resp = requests.get(image_url, timeout=self.timeout)
            resp.raise_for_status()
            target.write_bytes(resp.content)
            return str(target.relative_to(PROJECT_ROOT))
        except requests.RequestException as exc:
            self.logger.warning("图片下载失败，已跳过: %s, error=%s", image_url, exc)
            return None

    def run(self, limit: int, reset: bool = False) -> None:
        """主流程：可选清理 -> 抓取商品 -> 多线程下载图片 -> 落盘 products.json。

        - limit: 目标商品数量（例如 3000）
        - reset: 是否在本次运行前清理旧数据与向量库
        """
        if reset:
            self.reset_data()

        self.init_directories()
        raw_items = self.fetch_products(limit=limit)

        products: list[Product] = []

        def process_item(item: dict[str, Any]) -> Product | None:
            raw_id = str(item.get("id", "unknown"))
            safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", raw_id)
            image_rel_path = self.download_image(item.get("image", ""), f"product_{safe_name}.jpg")
            if not image_rel_path:
                # 图片失败则跳过，避免无效记录进入后续多模态流程
                return None

            return Product(
                product_id=f"p_{raw_id}",
                name=str(item.get("title", "未命名商品")),
                description=str(item.get("description", "")),
                price=float(item.get("price", 0.0)),
                category=str(item.get("category", "unknown")),
                image_path=image_rel_path,
                source_url=FAKESTORE_API,
            )

        # 使用线程池并行下载图片与构建 Product，提升 3000+ 商品场景下的初始化速度
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(process_item, item) for item in raw_items]
            for future in as_completed(futures):
                product = future.result()
                if product is not None:
                    products.append(product)

        self._atomic_write_json(PRODUCTS_JSON, [asdict(p) for p in products])
        self.logger.info("数据初始化完成：成功写入 %s 条商品", len(products))

    @staticmethod
    def _atomic_write_json(path: Path, payload: Any) -> None:
        """原子写入 JSON，防止中断导致文件损坏。"""
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        tmp_path.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="自动化商品采集与本地数据初始化")
    parser.add_argument("--limit", type=int, default=30, help="抓取商品数量（建议 20~50，批量实验可设为 3000）")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="在本次运行前清理本地旧数据（images/meta/vector_store），适用于大规模重新初始化",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    args = parse_args()

    if args.limit < 1:
        raise ValueError("--limit 必须大于 0")

    bootstrapper = LocalDataBootstrapper()
    bootstrapper.run(limit=args.limit, reset=args.reset)


if __name__ == "__main__":
    main()
