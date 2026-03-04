"""数据流水线：从原始 JSON/CSV 到 ChromaDB 的工业化入库。

主要步骤：
1. 数据清洗与预处理（ETL）：
   - 处理缺失值、去重、价格转 float；
   - 文本规范化：去 HTML / 特殊符号，截断到 512 字符。
2. 语义增强（Semantic Enrichment）：
   - 调用 DeepSeek API，对每个商品的描述做结构化特征抽取；
   - 返回 JSON：{style, material, suitable_scene, target_user}。
3. 多模态特征提取（Multi-modal Feature Engineering）：
   - 使用 CLIP ViT-L/14（openai/clip-vit-large-patch14）；
   - 图像：本地图片中心裁剪 + 归一化，提取视觉向量；
   - 文本：标题 + 增强特征 + 卖点，提取文本向量；
   - 向量融合：V = Normalize(ω * V_img + (1-ω) * V_txt)，默认 ω=0.5，可按品类调节。
4. ChromaDB 持久化：
   - chromadb.PersistentClient(path="./data/chroma_storage")；
   - metadata 中必须包含 original_id, price, category, brand, tags 等。
5. 性能优化：
   - 图片加载使用 ThreadPoolExecutor；
   - GPU 批处理（batch_size=32/64）；
   - 每批处理后 torch.cuda.empty_cache()。

运行示例：
    python data_pipeline.py ^
        --input data/meta/products.json ^
        --image-root data/images ^
        --limit 1000 ^
        --batch-size 32
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Optional

import aiohttp
import chromadb
import numpy as np
import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from transformers import CLIPModel, CLIPProcessor


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_CHROMA_PATH = DATA_DIR / "chroma_storage"

# 如果你只在本地单机使用，可以把 DeepSeek 的 API Key 直接填在这里。
# !!! 注意：不要把包含真实密钥的代码提交到任何远程仓库或发给别人。
DEEPSEEK_API_KEY_HARDCODED = "sk-fa86cd1e1c814e0b90155dd6180d9055"  # 在这里填入你的 DeepSeek API Key，例如："sk-xxx..."


logger = logging.getLogger("data_pipeline")


# --------------------------
# 通用工具与数据结构
# --------------------------


HTML_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


def clean_text(text: str, max_len: int = 512) -> str:
    """移除 HTML / 过多空白 / 特殊符号，并截断长度。"""
    if not text:
        return ""
    s = str(text)
    # 去 HTML 标签
    s = HTML_TAG_RE.sub(" ", s)
    # 去除部分特殊符号（保留中英文、数字、常见标点）
    s = re.sub(r"[^\w\s\u4e00-\u9fff.,;:!?（）()、\-¥￥$%:/]", " ", s)
    # 规范空白
    s = WHITESPACE_RE.sub(" ", s).strip()
    # 截断
    if len(s) > max_len:
        s = s[: max_len - 3] + "..."
    return s


def normalize_price(value: Any) -> float:
    """将各种格式的价格转换为 float，无法解析时返回 0.0。"""
    if value is None:
        return 0.0
    try:
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value)
        # 去掉货币符号
        s = re.sub(r"[^\d.,\-]", "", s)
        s = s.replace(",", "")
        return float(s)
    except Exception:
        logger.warning("价格解析失败，value=%r，已置为 0.0", value)
        return 0.0


@dataclass
class RawItem:
    original_id: str
    title: str
    description: str
    price: float
    category: str
    image_path: str
    brand: str = ""
    tags: List[str] | None = None
    extra: dict[str, Any] | None = None


@dataclass
class EnrichedItem:
    raw: RawItem
    style: str = ""
    material: str = ""
    suitable_scene: str = ""
    target_user: str = ""

    @property
    def merged_text(self) -> str:
        """组合最终用于文本向量的内容：标题 + 增强特征 + 描述。"""
        blocks: list[str] = []
        if self.raw.title:
            blocks.append(f"标题：{self.raw.title}")
        attr_parts: list[str] = []
        if self.style:
            attr_parts.append(f"风格：{self.style}")
        if self.material:
            attr_parts.append(f"材质：{self.material}")
        if self.suitable_scene:
            attr_parts.append(f"适用场景：{self.suitable_scene}")
        if self.target_user:
            attr_parts.append(f"适用人群：{self.target_user}")
        if attr_parts:
            blocks.append("；".join(attr_parts))
        if self.raw.description:
            blocks.append(f"卖点描述：{self.raw.description}")
        txt = "。".join(blocks)
        return clean_text(txt, max_len=512)


# --------------------------
# DeepSeek 语义增强（异步）
# --------------------------


class DeepSeekEnricher:
    """使用 DeepSeek Chat API 对商品描述做语义特征抽取。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com/v1/chat/completions",
        model: str = "deepseek-chat",
        timeout: int = 30,
        max_concurrency: int = 8,
        max_retries: int = 3,
    ) -> None:
        # 优先使用显式传入的 api_key，其次是本文件中硬编码的常量，最后才尝试读环境变量。
        self.api_key = api_key or DEEPSEEK_API_KEY_HARDCODED or os.getenv("DEEPSEEK_API_KEY", "")
        if not self.api_key:
            raise RuntimeError(
                "缺少 DeepSeek API Key：请在 data_pipeline.py 中设置 DEEPSEEK_API_KEY_HARDCODED，"
                "或者配置环境变量 DEEPSEEK_API_KEY。"
            )
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.max_retries = max_retries

    def build_prompt(self, title: str, description: str) -> str:
        """构造让 DeepSeek 返回结构化 JSON 的 Prompt。"""
        instruction = {
            "task": "请你作为电商商品运营专家，对下面的【商品标题】和【原始描述】进行特征抽取。",
            "requirement": [
                "只从文本中归纳，不要胡编乱造新信息；",
                "所有输出必须是严格可解析的 JSON；",
                "中文简洁描述，每个字段长度控制在 2~20 字。",
            ],
            "input": {
                "title": title,
                "description": description,
            },
            "output_schema": {
                "style": "商品整体风格，例如：极简、复古、运动、商务、通勤、户外等",
                "material": "主要材质或面料，例如：纯棉、真皮、合金、塑料等",
                "suitable_scene": "典型适用场景，例如：日常通勤、户外旅行、商务会议、运动健身等",
                "target_user": "主要目标人群，例如：年轻上班族、学生党、中年商务人士、户外爱好者等",
            },
            "must_format": "你必须只返回一个 JSON 对象，不能包含任何多余说明或 Markdown 代码块。",
            "example_output": {
                "style": "极简通勤",
                "material": "头层牛皮",
                "suitable_scene": "日常通勤和商务出差",
                "target_user": "一二线城市的年轻上班族",
            },
        }
        return json.dumps(instruction, ensure_ascii=False)

    async def _call_api_once(self, session: aiohttp.ClientSession, prompt: str) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个严格输出 JSON 的电商商品特征分析助手。",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.2,
        }
        async with session.post(self.base_url, headers=headers, json=payload, timeout=self.timeout) as resp:
            text = await resp.text()
            if resp.status >= 400:
                raise RuntimeError(f"DeepSeek API error: status={resp.status}, body={text[:200]}")
            data = json.loads(text)
            content = data["choices"][0]["message"]["content"]
            # 防止模型包了一层 ```json
            content = content.strip()
            if content.startswith("```"):
                content = content.strip("`")
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content)

    async def enrich(self, items: list[RawItem]) -> list[EnrichedItem]:
        """并发调用 DeepSeek，对所有商品进行语义增强。"""

        async def _enrich_one(item: RawItem, session: aiohttp.ClientSession) -> EnrichedItem:
            prompt = self.build_prompt(item.title, item.description)
            last_err: Exception | None = None
            for attempt in range(1, self.max_retries + 1):
                try:
                    async with self.semaphore:
                        resp = await self._call_api_once(session, prompt)
                    return EnrichedItem(
                        raw=item,
                        style=str(resp.get("style", "")).strip(),
                        material=str(resp.get("material", "")).strip(),
                        suitable_scene=str(resp.get("suitable_scene", "")).strip(),
                        target_user=str(resp.get("target_user", "")).strip(),
                    )
                except Exception as exc:  # noqa: BLE001
                    last_err = exc
                    logger.warning(
                        "DeepSeek enrich 失败 (attempt=%s, id=%s): %s",
                        attempt,
                        item.original_id,
                        exc,
                    )
                    await asyncio.sleep(1.5 * attempt)
            logger.error("DeepSeek enrich 多次失败，使用空增强字段, id=%s, err=%s", item.original_id, last_err)
            return EnrichedItem(raw=item)

        if not items:
            return []

        timeout = aiohttp.ClientTimeout(total=None, sock_connect=self.timeout, sock_read=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            tasks = [_enrich_one(it, session) for it in items]
            return await asyncio.gather(*tasks)


# --------------------------
# CLIP 多模态向量抽取
# --------------------------


class ProductDataset(Dataset):
    """简单的多模态数据集，供 DataLoader 批处理读取。"""

    def __init__(self, items: list[EnrichedItem], image_root: Path) -> None:
        self.items = items
        self.image_root = image_root

    def __len__(self) -> int:  # type: ignore[override]
        return len(self.items)

    def __getitem__(self, idx: int) -> dict[str, Any]:  # type: ignore[override]
        item = self.items[idx]
        img_path = self.image_root / item.raw.image_path
        return {
            "id": item.raw.original_id,
            "image_path": img_path,
            "text": item.merged_text,
            "price": item.raw.price,
            "category": item.raw.category,
            "brand": item.raw.brand,
            "tags": item.raw.tags or [],
            "style": item.style,
            "material": item.material,
            "suitable_scene": item.suitable_scene,
            "target_user": item.target_user,
        }


def load_image(path: Path) -> Image.Image:
    """使用 PIL 加载并转换为 RGB，出错时抛异常。"""
    with Image.open(path) as img:
        return img.convert("RGB")


class CLIPMultimodalEmbedder:
    """封装 CLIP ViT-L/14 多模态向量抽取与加权融合。"""

    def __init__(
        self,
        model_name: str = "openai/clip-vit-large-patch14",
        device: Optional[str] = None,
        fp16: bool = True,
    ) -> None:
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(device)

        torch_dtype = torch.float16 if (fp16 and self.device.type == "cuda") else torch.float32
        logger.info("加载 CLIP 模型: %s, device=%s, dtype=%s", model_name, self.device, torch_dtype)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model = CLIPModel.from_pretrained(model_name, torch_dtype=torch_dtype)
        self.model.to(self.device)
        self.model.eval()

    @torch.no_grad()
    def encode_batch(
        self,
        batch_samples: list[dict[str, Any]],
        image_executor: ThreadPoolExecutor,
    ) -> np.ndarray:
        """对一个 batch 内的样本做多模态向量编码并加权融合。"""
        texts: list[str] = [s["text"] for s in batch_samples]
        img_paths: list[Path] = [s["image_path"] for s in batch_samples]

        # 多线程加载图片
        images: list[Image.Image] = list(image_executor.map(load_image, img_paths))

        inputs = self.processor(
            text=texts,
            images=images,
            return_tensors="pt",
            padding=True,
            truncation=True,
        ).to(self.device)

        image_features = self.model.get_image_features(**inputs)
        text_features = self.model.get_text_features(**inputs)

        # L2 归一化
        image_features = torch.nn.functional.normalize(image_features, dim=-1)
        text_features = torch.nn.functional.normalize(text_features, dim=-1)

        # 默认加权系数，全局 ω，可在外层按品类微调
        omegas = []
        for s in batch_samples:
            base_omega = 0.5
            cat = str(s.get("category") or "").lower()
            # 简单按品类做一个示例性的动态调整
            if "clothing" in cat or "服饰" in cat or "men" in cat or "women" in cat:
                base_omega = 0.6  # 服饰图片更重要
            elif "electronics" in cat or "数码" in cat:
                base_omega = 0.4  # 文本参数更重要
            omegas.append(base_omega)

        omega_tensor = torch.tensor(omegas, dtype=image_features.dtype, device=self.device).unsqueeze(-1)
        fused = omega_tensor * image_features + (1.0 - omega_tensor) * text_features
        fused = torch.nn.functional.normalize(fused, dim=-1)

        return fused.detach().cpu().numpy().astype(np.float32)


# --------------------------
# ChromaDB 写入
# --------------------------


def get_chroma_collection(chroma_path: Path, collection_name: str) -> Any:
    client = chromadb.PersistentClient(path=str(chroma_path))
    # 显式使用 cosine 相似度
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def upsert_to_chroma(
    collection: Any,
    batch_samples: list[dict[str, Any]],
    embeddings: np.ndarray,
) -> None:
    ids: list[str] = []
    metadatas: list[dict[str, Any]] = []
    documents: list[str] = []

    for sample, vec in zip(batch_samples, embeddings):
        pid = str(sample["id"])
        if not pid:
            continue
        ids.append(pid)
        documents.append(sample["text"])

        # 处理 tags：Chroma 要求 list 类型且非空；若为空则干脆不带该字段
        raw_tags = sample.get("tags", []) or []
        cleaned_tags: list[str] = []
        if isinstance(raw_tags, Iterable) and not isinstance(raw_tags, (str, bytes)):
            cleaned_tags = [str(t).strip() for t in raw_tags if str(t).strip()]
        else:
            s = str(raw_tags).strip()
            if s:
                cleaned_tags = [s]

        metadata: dict[str, Any] = {
            "original_id": pid,
            "price": float(sample.get("price", 0.0)),
            "category": sample.get("category", ""),
            "brand": sample.get("brand", ""),
            # 一些语义增强字段，便于后续过滤与分析
            "style": sample.get("style", ""),
            "material": sample.get("material", ""),
            "suitable_scene": sample.get("suitable_scene", ""),
            "target_user": sample.get("target_user", ""),
        }
        if cleaned_tags:
            metadata["tags"] = cleaned_tags

        metadatas.append(metadata)

    if not ids:
        return

    try:
        collection.upsert(
            ids=ids,
            embeddings=embeddings.tolist(),
            metadatas=metadatas,
            documents=documents,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("ChromaDB upsert 失败（batch_size=%d）: %s", len(ids), exc)
        raise


# --------------------------
# ETL：读取与清洗
# --------------------------


def load_from_json(path: Path, limit: Optional[int] = None) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("JSON 格式错误，预期为 list")
    if limit is not None:
        data = data[:limit]
    return data


def load_from_csv(path: Path, limit: Optional[int] = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            rows.append(row)
            if limit is not None and len(rows) >= limit:
                break
    return rows


def etl_records(raw_rows: list[dict[str, Any]]) -> list[RawItem]:
    """ETL：缺失值处理、去重、字段规范化。"""
    seen_ids: set[str] = set()
    items: list[RawItem] = []

    for row in raw_rows:
        # 兼容不同字段命名
        rid = str(
            row.get("original_id")
            or row.get("product_id")
            or row.get("id")
            or row.get("sku")
            or ""
        ).strip()
        if not rid:
            continue
        if rid in seen_ids:
            continue
        seen_ids.add(rid)

        title = str(row.get("title") or row.get("name") or "").strip()
        desc_raw = str(row.get("description") or "").strip()
        if not desc_raw:
            desc_raw = title  # 缺失描述则用标题兜底

        description = clean_text(desc_raw, max_len=512)
        price = normalize_price(row.get("price"))
        category = str(row.get("category") or "").strip()

        image_path = str(row.get("image_path") or row.get("image") or "").strip()
        if not image_path:
            # 没有图片的商品对多模态帮助有限，可以后续根据需求过滤
            continue
        # 规范图片路径：去掉可能重复的根目录前缀，例如 "data/images/"
        image_path_norm = image_path.replace("\\", "/")
        prefix = "data/images/"
        if image_path_norm.startswith(prefix):
            image_path = image_path_norm[len(prefix) :]
        else:
            image_path = image_path_norm

        brand = str(row.get("brand") or "").strip()
        tags_field = row.get("tags") or row.get("keywords") or []
        if isinstance(tags_field, str):
            tags = [t.strip() for t in re.split(r"[,/;；、]", tags_field) if t.strip()]
        elif isinstance(tags_field, Iterable):
            tags = [str(t).strip() for t in tags_field if str(t).strip()]
        else:
            tags = []

        extra = {k: v for k, v in row.items() if k not in {"id", "product_id", "original_id"}}

        item = RawItem(
            original_id=rid,
            title=title,
            description=description,
            price=price,
            category=category,
            image_path=image_path,
            brand=brand,
            tags=tags,
            extra=extra,
        )
        items.append(item)

    logger.info("ETL 完成：原始 %d 条 -> 清洗后 %d 条（去重 & 过滤缺失图片）", len(raw_rows), len(items))
    return items


# --------------------------
# 主流程
# --------------------------


async def async_run_pipeline(args: argparse.Namespace) -> None:
    input_path = (PROJECT_ROOT / args.input).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    # 1) 读取原始数据
    if input_path.suffix.lower() == ".json":
        raw_rows = load_from_json(input_path, limit=args.limit)
    elif input_path.suffix.lower() in {".csv", ".tsv"}:
        raw_rows = load_from_csv(input_path, limit=args.limit)
    else:
        raise ValueError(f"不支持的输入格式: {input_path.suffix}")

    # 2) ETL 清洗
    records = etl_records(raw_rows)
    if not records:
        logger.warning("清洗后记录为空，终止流水线。")
        return

    # 3) 语义增强（DeepSeek） + 本地缓存
    cache_path = (PROJECT_ROOT / args.enrich_cache_path).resolve()

    # 辅助函数：从缓存中恢复 EnrichedItem
    def load_enriched_from_cache() -> list[EnrichedItem]:
        if not cache_path.exists():
            logger.warning(
                "指定了 --skip-enrich 但缓存文件不存在，将直接使用原始标题和描述。cache=%s",
                cache_path,
            )
            return [EnrichedItem(raw=rec) for rec in records]

        try:
            with cache_path.open("r", encoding="utf-8") as f:
                cache_data = json.load(f)
        except Exception as exc:  # noqa: BLE001
            logger.warning("加载语义增强缓存失败，将退化为无增强：%s", exc)
            return [EnrichedItem(raw=rec) for rec in records]

        if not isinstance(cache_data, list):
            logger.warning("语义增强缓存格式异常（预期为 list），将退化为无增强。")
            return [EnrichedItem(raw=rec) for rec in records]

        cache_map: dict[str, dict[str, Any]] = {}
        for entry in cache_data:
            if not isinstance(entry, dict):
                continue
            oid = str(entry.get("original_id") or "").strip()
            if not oid:
                continue
            cache_map[oid] = entry

        enriched_list: list[EnrichedItem] = []
        missing = 0
        for rec in records:
            cached = cache_map.get(rec.original_id)
            if not cached:
                missing += 1
                enriched_list.append(EnrichedItem(raw=rec))
                continue
            enriched_list.append(
                EnrichedItem(
                    raw=rec,
                    style=str(cached.get("style", "")).strip(),
                    material=str(cached.get("material", "")).strip(),
                    suitable_scene=str(cached.get("suitable_scene", "")).strip(),
                    target_user=str(cached.get("target_user", "")).strip(),
                )
            )

        if missing:
            logger.warning("语义增强缓存中缺失 %d 条记录，已使用无增强版本填充。", missing)
        logger.info("已从语义增强缓存中恢复 %d 条记录。", len(enriched_list))
        return enriched_list

    # 辅助函数：将本次增强结果写入缓存
    def save_enriched_to_cache(items: list[EnrichedItem]) -> None:
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            payload = [
                {
                    "original_id": it.raw.original_id,
                    "style": it.style,
                    "material": it.material,
                    "suitable_scene": it.suitable_scene,
                    "target_user": it.target_user,
                }
                for it in items
            ]
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            logger.info("语义增强结果已写入缓存：%s（共 %d 条）", cache_path, len(items))
        except Exception as exc:  # noqa: BLE001
            logger.warning("写入语义增强缓存失败（不影响主流程）：%s", exc)

    if getattr(args, "skip_enrich", False):
        logger.info("已启用 --skip-enrich，将从本地缓存加载语义增强结果。")
        enriched_items = load_enriched_from_cache()
    elif getattr(args, "disable_deepseek", False):
        logger.info("已启用 --disable-deepseek，跳过 DeepSeek 调用，仅使用原始标题和描述。")
        enriched_items = [EnrichedItem(raw=rec) for rec in records]
    else:
        logger.info("开始语义增强（DeepSeek），样本数=%d", len(records))
        enricher = DeepSeekEnricher(
            max_concurrency=args.ds_max_concurrency,
            timeout=args.ds_timeout,
        )
        enriched_items = await enricher.enrich(records)
        logger.info("语义增强完成。")
        save_enriched_to_cache(enriched_items)

    # 4) 多模态向量抽取 + ChromaDB 入库
    image_root = (PROJECT_ROOT / args.image_root).resolve()
    if not image_root.exists():
        raise FileNotFoundError(f"图片根目录不存在: {image_root}")

    dataset = ProductDataset(enriched_items, image_root=image_root)
    dataloader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False, num_workers=0, collate_fn=list)

    embedder = CLIPMultimodalEmbedder()
    chroma_path = (PROJECT_ROOT / args.chroma_path).resolve()
    chroma_path.mkdir(parents=True, exist_ok=True)
    collection = get_chroma_collection(chroma_path, args.collection)

    image_executor = ThreadPoolExecutor(max_workers=args.image_workers)

    total = 0
    try:
        for batch_idx, batch in enumerate(dataloader):
            # DataLoader 的 collate_fn 返回的是一个 list[dict]
            batch_samples: list[dict[str, Any]] = batch
            # 编码
            embeddings = embedder.encode_batch(batch_samples, image_executor=image_executor)
            # 入库
            upsert_to_chroma(collection, batch_samples, embeddings)
            total += len(batch_samples)
            logger.info(
                "已处理 batch=%d, 本批=%d, 累计入库=%d",
                batch_idx,
                len(batch_samples),
                total,
            )
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    finally:
        image_executor.shutdown(wait=True)

    logger.info("流水线完成，总入库商品数：%d", total)


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="从原始 JSON/CSV 数据到 ChromaDB 的多模态入库流水线")
    parser.add_argument(
        "--input",
        type=str,
        default="data/meta/products.json",
        help="原始 JSON/CSV 文件路径（相对于项目根目录）",
    )
    parser.add_argument(
        "--image-root",
        type=str,
        default="data/images",
        help="本地图片根目录（相对于项目根目录）",
    )
    parser.add_argument(
        "--chroma-path",
        type=str,
        default=str(DEFAULT_CHROMA_PATH.relative_to(PROJECT_ROOT)),
        help="ChromaDB 持久化目录（相对于项目根目录）",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="products_multimodal_clip_l14",
        help="ChromaDB Collection 名称",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="最多处理的商品数量（默认不限制）",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="CLIP 推理 batch 大小",
    )
    parser.add_argument(
        "--image-workers",
        type=int,
        default=8,
        help="图片加载线程数（ThreadPoolExecutor.max_workers）",
    )
    parser.add_argument(
        "--ds-timeout",
        type=int,
        default=30,
        help="DeepSeek 单次请求超时时间（秒）",
    )
    parser.add_argument(
        "--ds-max-concurrency",
        type=int,
        default=8,
        help="DeepSeek 最大并发请求数（Semaphore 限制）",
    )
    parser.add_argument(
        "--enrich-cache-path",
        type=str,
        default="data/cache/deepseek_enrich_cache.json",
        help="语义增强结果缓存文件路径（相对于项目根目录）",
    )
    parser.add_argument(
        "--disable-deepseek",
        action="store_true",
        help="跳过 DeepSeek 语义增强，不调用外部大模型 API（仅使用原始标题和描述）",
    )
    parser.add_argument(
        "--skip-enrich",
        action="store_true",
        help="从本地缓存加载语义增强结果，不再调用 DeepSeek；若缓存缺失则退化为无增强。",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable[str]] = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    args = parse_args(argv)
    logger.info("启动数据流水线，参数：%s", vars(args))
    try:
        asyncio.run(async_run_pipeline(args))
    except KeyboardInterrupt:
        logger.warning("收到 KeyboardInterrupt，中断流水线。")
    except Exception as exc:  # noqa: BLE001
        logger.exception("流水线运行失败: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()

