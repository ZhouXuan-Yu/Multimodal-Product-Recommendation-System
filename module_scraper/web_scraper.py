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
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import requests
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
IMAGES_DIR = DATA_DIR / "images"
RAW_IMAGES_DIR = DATA_DIR / "raw" / "base_images"
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
        # 图片 URL -> 本地相对路径缓存，避免扩增到 3000 时重复下载同一张图
        self._image_cache: dict[str, str] = {}
        self._image_cache_lock = threading.Lock()
        # 基础图片（原图）缓存：URL -> base_image_path（用于做 3000 变体）
        self._base_image_cache: dict[str, str] = {}
        self._base_image_cache_lock = threading.Lock()

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
        RAW_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

        # 写入一个二进制占位图（JPEG），用于图片下载失败/缺失时兜底
        # 注意：向量化阶段会用 PIL 打开图片，SVG 可能无法被 PIL 默认解码，因此使用 JPEG 更稳。
        placeholder = IMAGES_DIR / "placeholder.jpg"
        if not placeholder.exists() or placeholder.stat().st_size == 0:
            try:
                from PIL import Image, ImageDraw, ImageFont  # type: ignore

                img = Image.new("RGB", (512, 512), color=(242, 242, 242))
                draw = ImageDraw.Draw(img)
                draw.rectangle([64, 96, 448, 416], outline=(208, 208, 208), width=3, fill=(255, 255, 255))
                draw.polygon([(128, 352), (224, 256), (288, 320), (352, 224), (416, 352)], outline=(207, 207, 207), fill=(230, 230, 230))
                draw.ellipse([176, 184, 224, 232], outline=(217, 217, 217), fill=(217, 217, 217))
                # 字体加载失败就不写字，也不影响兜底
                try:
                    font = ImageFont.load_default()
                    draw.text((156, 452), "image unavailable", fill=(154, 154, 154), font=font)
                except Exception:
                    pass
                img.save(placeholder, format="JPEG", quality=85)
            except Exception:
                # 若 PIL 不可用，写一个空文件避免崩溃（后续会尽量走真实图片）
                placeholder.write_bytes(b"")

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

        # 样本扩增：对现有样本做轻微扰动，满足 3000+ 条数据初始化需求。
        expanded: list[dict[str, Any]] = []
        multiplier = (limit // len(items)) + 1
        for i in range(multiplier):
            for item in items:
                clone = dict(item)
                # 重要：不能用 int(f"{id}{i}")，会产生歧义碰撞（例如 1+94 与 19+4 都变为 194）
                clone["id"] = f"{item['id']}_{i}"

                # 文本多样化：为每条记录加入稳定且可复现的扰动（基于 seed）
                seed = int(hashlib.md5(str(clone["id"]).encode("utf-8")).hexdigest()[:8], 16)
                rng = random.Random(seed)
                color = rng.choice(["黑色", "白色", "灰色", "蓝色", "红色", "绿色", "卡其", "棕色", "银色", "金色"])
                style = rng.choice(["简约", "复古", "轻奢", "运动", "通勤", "街头", "学院", "商务", "户外", "甜酷"])
                material = rng.choice(["棉", "羊毛", "真皮", "仿皮", "涤纶", "尼龙", "不锈钢", "陶瓷", "玻璃", "合金"])
                scene = rng.choice(["日常", "旅行", "约会", "健身", "办公", "露营", "通学", "通勤", "派对", "居家"])
                feature = rng.choice(["耐磨", "透气", "防水", "轻量", "大容量", "高颜值", "舒适", "易清洁", "抗皱", "护眼"])
                size_hint = rng.choice(["S", "M", "L", "XL", "均码", "28", "30", "32", "34", "42"])
                sku = hashlib.sha1(f"{clone['id']}|{clone.get('category','')}".encode("utf-8")).hexdigest()[:10].upper()

                base_title = str(item.get("title", "未命名商品")).strip()
                clone["title"] = f"{base_title} · {style}{color} · {feature}款 #{i + 1}"
                price = float(item.get("price", 99.0))
                clone["price"] = round(price * random.uniform(0.85, 1.15), 2)
                base_desc = str(item.get("description", "")).strip()
                clone["description"] = (
                    f"{base_desc}\n"
                    f"风格：{style}；颜色：{color}；材质：{material}；场景：{scene}；尺码：{size_hint}；卖点：{feature}。\n"
                    f"SKU：{sku}（本地合成样本，用于提升检索多样性）"
                )
                expanded.append(clone)
                if len(expanded) >= limit:
                    return expanded
        return expanded

    def _download_base_image(self, image_url: str) -> Path:
        """下载“基础原图”到 data/raw/base_images，用于生成 3000 张独立变体图片。"""
        placeholder = IMAGES_DIR / "placeholder.jpg"
        if not image_url:
            return placeholder

        # URL -> base 文件名（稳定）
        url_hash = hashlib.md5(image_url.encode("utf-8")).hexdigest()[:16]
        target = RAW_IMAGES_DIR / f"base_{url_hash}.jpg"

        # 缓存命中（多线程下加锁）
        with self._base_image_cache_lock:
            cached = self._base_image_cache.get(image_url)
        if cached:
            p = Path(cached)
            if p.exists() and p.stat().st_size > 0:
                return p

        if target.exists() and target.stat().st_size > 0:
            with self._base_image_cache_lock:
                self._base_image_cache[image_url] = str(target)
            return target

        try:
            resp = requests.get(image_url, timeout=self.timeout)
            resp.raise_for_status()
            target.write_bytes(resp.content)
            with self._base_image_cache_lock:
                self._base_image_cache[image_url] = str(target)
            return target
        except requests.RequestException as exc:
            self.logger.warning("基础图片下载失败，已使用占位图: %s, error=%s", image_url, exc)
            return placeholder

    @staticmethod
    def _make_unique_variant_image(
        base_image_path: Path,
        out_path: Path,
        seed: int,
        label: str,
        category: str,
    ) -> None:
        """从基础图片生成一个“视觉上不同”的变体，并保存为 JPEG。"""
        from PIL import Image, ImageDraw, ImageEnhance, ImageFilter  # type: ignore

        rng = random.Random(seed)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            img = Image.open(base_image_path).convert("RGB")
        except Exception:
            # 兜底：生成一张纯色底图
            bg = (rng.randint(30, 240), rng.randint(30, 240), rng.randint(30, 240))
            img = Image.new("RGB", (512, 512), color=bg)

        # 1) 随机裁剪（保证不同 seed 产生不同内容）
        w, h = img.size
        min_side = max(32, min(w, h))
        crop_scale = rng.uniform(0.72, 1.0)
        cw = int(min_side * crop_scale)
        ch = int(min_side * crop_scale)
        x0 = rng.randint(0, max(0, w - cw))
        y0 = rng.randint(0, max(0, h - ch))
        img = img.crop((x0, y0, x0 + cw, y0 + ch)).resize((512, 512))

        # 2) 轻度旋转 + 滤镜
        angle = rng.uniform(-18, 18)
        img = img.rotate(angle, resample=Image.BICUBIC, expand=False)
        if rng.random() < 0.35:
            img = img.filter(ImageFilter.GaussianBlur(radius=rng.uniform(0.2, 1.2)))
        if rng.random() < 0.25:
            img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))

        # 3) 颜色抖动（亮度/对比度/饱和度）
        img = ImageEnhance.Brightness(img).enhance(rng.uniform(0.78, 1.22))
        img = ImageEnhance.Contrast(img).enhance(rng.uniform(0.78, 1.25))
        img = ImageEnhance.Color(img).enhance(rng.uniform(0.75, 1.35))

        # 4) 加噪声（依赖 numpy，项目内已使用）
        arr = np.asarray(img).astype(np.int16)
        sigma = rng.uniform(2.0, 14.0)
        noise = rng.normalvariate(0, sigma)
        # 逐通道轻度扰动 + 噪声偏置
        arr = arr + int(noise)
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        img = Image.fromarray(arr, mode="RGB")

        # 5) 叠加标签（确保即便基础图相同也能强制差异）
        draw = ImageDraw.Draw(img)
        bar_h = 76
        draw.rectangle([0, 512 - bar_h, 512, 512], fill=(0, 0, 0, 128))
        tag = f"{label} | {category[:24]}"
        # 不强依赖字体，默认字体即可
        try:
            from PIL import ImageFont  # type: ignore

            font = ImageFont.load_default()
            draw.text((12, 512 - bar_h + 10), tag, fill=(245, 245, 245), font=font)
        except Exception:
            draw.text((12, 512 - bar_h + 10), tag, fill=(245, 245, 245))

        img.save(out_path, format="JPEG", quality=88, optimize=True)

    def build_unique_image(self, image_url: str, product_id: str, name: str, category: str) -> str:
        """为每个商品生成独立图片文件，并返回相对路径（指向 data/images）。"""
        safe_pid = re.sub(r"[^a-zA-Z0-9_-]", "_", product_id)
        out_path = IMAGES_DIR / f"{safe_pid}.jpg"

        # 已存在则复用（便于断点续跑）
        if out_path.exists() and out_path.stat().st_size > 0:
            return str(out_path.relative_to(PROJECT_ROOT))

        base_path = self._download_base_image(image_url)
        seed = int(hashlib.md5(product_id.encode("utf-8")).hexdigest()[:8], 16)
        label = (name[:24] + "...") if len(name) > 24 else name
        self._make_unique_variant_image(base_path, out_path, seed=seed, label=label, category=category)
        return str(out_path.relative_to(PROJECT_ROOT))

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
            product_id = f"p_{raw_id}"
            name = str(item.get("title", "未命名商品"))
            category = str(item.get("category", "unknown"))
            image_rel_path = self.build_unique_image(item.get("image", ""), product_id=product_id, name=name, category=category)

            return Product(
                product_id=product_id,
                name=name,
                description=str(item.get("description", "")),
                price=float(item.get("price", 0.0)),
                category=category,
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
