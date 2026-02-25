"""模块五：本地数据监控逻辑（无数据库）。"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_JSON = PROJECT_ROOT / "data" / "meta" / "products.json"
USERS_PROFILE_JSON = PROJECT_ROOT / "data" / "meta" / "users_profile.json"
LOG_FILE = PROJECT_ROOT / "logs" / "app.log"


def safe_load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def compute_product_stats() -> dict[str, Any]:
    products = safe_load_json(PRODUCTS_JSON, [])
    counter = Counter([p.get("category", "unknown") for p in products])
    return {"total": len(products), "category_dist": dict(counter)}


def compute_user_table() -> list[dict[str, Any]]:
    users = safe_load_json(USERS_PROFILE_JSON, {"users": {}}).get("users", {})
    rows = []
    for uid, info in users.items():
        rows.append(
            {
                "user_id": uid,
                "activity_score": info.get("activity_score", 0),
                "core_tags": ", ".join(info.get("core_tags", [])),
            }
        )
    return rows


def compute_llm_usage() -> dict[str, int]:
    # 简易统计：按关键字计数，可按需改为结构化日志解析。
    if not LOG_FILE.exists():
        return {"deepseek_calls": 0, "estimated_tokens": 0}

    text = LOG_FILE.read_text(encoding="utf-8", errors="ignore")
    calls = text.count("deepseek") + text.count("DeepSeek")
    return {"deepseek_calls": calls, "estimated_tokens": calls * 800}
