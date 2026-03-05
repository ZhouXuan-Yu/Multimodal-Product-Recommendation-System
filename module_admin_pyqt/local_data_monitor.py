"""模块五：本地数据监控逻辑（无数据库）。"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import random
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_JSON = PROJECT_ROOT / "data" / "meta" / "products.json"
USERS_PROFILE_JSON = PROJECT_ROOT / "data" / "meta" / "users_profile.json"
ORDERS_JSON = PROJECT_ROOT / "data" / "meta" / "orders.json"
EVAL_METRICS_JSON = PROJECT_ROOT / "data" / "metrics" / "recommender_eval.json"
LOG_FILE = PROJECT_ROOT / "logs" / "app.log"


def safe_load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def compute_product_stats() -> dict[str, Any]:
    """商品基本统计：数量与品类分布。"""
    products = safe_load_json(PRODUCTS_JSON, [])
    counter = Counter([p.get("category", "unknown") for p in products])
    return {"total": len(products), "category_dist": dict(counter)}


def _load_users_doc() -> dict[str, Any]:
    doc = safe_load_json(USERS_PROFILE_JSON, {"users": {}})
    if not isinstance(doc, dict):
        doc = {"users": {}}
    doc.setdefault("users", {})
    return doc


def compute_user_table() -> list[dict[str, Any]]:
    """用户列表：用于在 PyQt 表格中展示核心画像。"""
    users_doc = _load_users_doc()
    users = users_doc.get("users", {})

    # 若暂无真实用户画像，则构造一批轻量级模拟用户，避免 PyQt 侧完全空白
    if not users:
        mock_users: dict[str, Any] = {}
        base_tags = [
            ["新用户", "待冷启动"],
            ["高价值用户", "偏好数码"],
            ["高频浏览", "爱逛服饰"],
            ["理性消费", "价格敏感"],
        ]
        today = datetime.utcnow().date()
        for i in range(1, 9):
            uid = f"mock_user_{i:03d}"
            score = random.randint(20, 95)
            tags = base_tags[i % len(base_tags)]
            # 用简单整数数组模拟 recent_activity，便于前端和 PyQt 同时消费
            recent = [random.randint(1, 5) for _ in range(30)]
            mock_users[uid] = {
                "name": uid,
                "activity_score": score,
                "core_tags": tags,
                "recent_activity": recent,
                # 为管理端预生成一段“画像说明”，即使尚未通过后端 DeepSeek 生成真实报告，
                # 也能在 PyQt 表格中看到专业感较强的一句话摘要。
                "last_insight_summary": (
                    f"该用户最近 30 天整体活跃度约为 {score} 分，偏好标签集中在「{tags[0]}」「{tags[1]}」，"
                    "适合在推荐中重点曝光相关品类，并结合价格敏感度做差异化运营。"
                ),
                "history": [
                    {
                        "product_id": f"MOCK-{(i + j) % 10 + 1}",
                        "action": random.choice(["view", "click", "purchase"]),
                        "timestamp": datetime.combine(
                            today - timedelta(days=random.randint(0, 20)),
                            datetime.min.time(),
                        ).isoformat(),
                    }
                    for j in range(12)
                ],
            }
        users_doc["users"] = mock_users
        users = mock_users

    rows: list[dict[str, Any]] = []
    for uid, info in users.items():
        activity_score = info.get("activity_score", 0)
        core_tags_raw = info.get("core_tags", [])
        core_tags = ", ".join(core_tags_raw)

        # 若后端已生成并持久化“画像与数据说明”，在此一并带给 PyQt；
        # 否则根据标签和活跃度自动生成一段降级画像摘要，避免前端看到空白。
        persona_summary = info.get("last_insight_summary", "") or ""
        if not persona_summary:
            if core_tags_raw:
                main_tag = core_tags_raw[0]
                persona_summary = (
                    f"该用户近期活跃度约为 {activity_score} 分，核心标签偏向「{main_tag}」，"
                    "适合作为重点运营人群进行个性化推荐与活动触达。"
                )
            else:
                persona_summary = (
                    f"该用户近期活跃度约为 {activity_score} 分，行为尚不充分，"
                    "系统将继续收集浏览与下单记录以完善个性化画像。"
                )

        rows.append(
            {
                "user_id": uid,
                "activity_score": activity_score,
                "core_tags": core_tags,
                "persona_summary": persona_summary,
            }
        )
    return rows


def compute_llm_usage() -> dict[str, int]:
    """
    LLM 调用粗略统计：
    - 按日志中 deepseek 关键词计数，估算大致调用次数与 Token 消耗。
    """
    if not LOG_FILE.exists():
        return {"deepseek_calls": 0, "estimated_tokens": 0}

    text = LOG_FILE.read_text(encoding="utf-8", errors="ignore")
    calls = text.count("deepseek") + text.count("DeepSeek")
    return {"deepseek_calls": calls, "estimated_tokens": calls * 800}


def _parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def compute_daily_activity(window_days: int = 30) -> List[Dict[str, Any]]:
    """
    按天汇总用户行为活跃度与下单量，用于趋势折线图：
    - events: 当日所有行为条数
    - orders: 当日订单数量
    """
    users_doc = _load_users_doc()
    users = users_doc.get("users", {})

    by_day_events: dict[str, int] = defaultdict(int)

    for info in users.values():
        history = info.get("history", []) or []
        for ev in history:
            ts = _parse_ts(ev.get("timestamp"))
            if not ts:
                continue
            day = ts.date().isoformat()
            by_day_events[day] += 1

    orders_doc = safe_load_json(ORDERS_JSON, {"orders": {}})
    orders_raw = orders_doc.get("orders", {})
    if isinstance(orders_raw, dict):
        orders = list(orders_raw.values())
    else:
        orders = orders_raw or []

    by_day_orders: dict[str, int] = defaultdict(int)
    for o in orders:
        ts = _parse_ts(o.get("created_at"))
        if not ts:
            continue
        day = ts.date().isoformat()
        by_day_orders[day] += 1

    # 若行为与订单全为空，则构造一段近 30 天的模拟曲线，避免趋势图完全空白
    if not by_day_events and not by_day_orders:
        today = datetime.utcnow().date()
        for i in range(29, -1, -1):
            day = (today - timedelta(days=i)).isoformat()
            base = random.randint(5, 40)
            by_day_events[day] = base + random.randint(0, 20)
            by_day_orders[day] = max(0, base // random.randint(6, 10))

    all_days = sorted(set(by_day_events.keys()) | set(by_day_orders.keys()))
    # 只展示最近 window_days 天，避免时间跨度过长影响阅读
    if len(all_days) > window_days:
        all_days = all_days[-window_days:]

    result: List[Dict[str, Any]] = []
    for d in all_days:
        result.append(
            {
                "day": d,
                "events": by_day_events.get(d, 0),
                "orders": by_day_orders.get(d, 0),
            }
        )
    return result


def compute_recommendation_effect() -> dict[str, Any]:
    """
    基于行为日志与订单数据的推荐效果基础指标：
    - total_users           总用户数
    - active_users          有行为记录的用户数
    - total_events          记录的行为总数
    - clicks / purchases    点击与下单行为次数
    - ctr                   点击率（click / view）
    - cvr                   转化率（purchase / click）
    - total_orders / revenue / avg_order_value  订单数量与总金额
    """
    users_doc = _load_users_doc()
    users = users_doc.get("users", {})

    total_users = len(users)
    active_users = 0
    total_events = 0
    views = 0
    clicks = 0
    purchases = 0

    for info in users.values():
        history = info.get("history", []) or []
        if history:
            active_users += 1
        for ev in history:
            total_events += 1
            action = str(ev.get("action") or "").lower()
            if action in ("view", "expose", "impression", "detail"):
                views += 1
            if action in ("click", "detail"):
                clicks += 1
            if action in ("purchase", "order", "pay", "conversion"):
                purchases += 1

    orders_doc = safe_load_json(ORDERS_JSON, {"orders": {}})
    orders_raw = orders_doc.get("orders", {})
    if isinstance(orders_raw, dict):
        orders = list(orders_raw.values())
    else:
        orders = orders_raw or []

    # 若还没有真实订单，则基于模拟用户与商品价格随机生成一小批本地订单
    if not orders:
        products = safe_load_json(PRODUCTS_JSON, [])
        today = datetime.utcnow().date()
        for i, uid in enumerate(list(users.keys())[:5] or ["mock_user_001"]):
            if not products:
                break
            p = random.choice(products)
            amount = float(p.get("price", 99.0) or 99.0) * random.randint(1, 3)
            created = datetime.combine(
                today - timedelta(days=random.randint(0, 10)),
                datetime.min.time(),
            ).isoformat()
            orders.append(
                {
                    "order_id": f"MOCK-{uid}-{i+1}",
                    "user_id": uid,
                    "status": "paid",
                    "items": [
                        {
                            "product_id": p.get("product_id", f"MOCK-{i+1}"),
                            "quantity": 1,
                            "unit_price": p.get("price", 99.0),
                        }
                    ],
                    "total_amount": amount,
                    "currency": "CNY",
                    "created_at": created,
                    "updated_at": created,
                }
            )

    total_orders = len(orders)
    revenue = 0.0
    for o in orders:
        try:
            revenue += float(o.get("total_amount", 0.0) or 0.0)
        except Exception:
            continue

    avg_order_value = revenue / total_orders if total_orders else 0.0

    # 若当前埋点中尚未显式上报 view / purchase 行为，则做一次 Demo 级兜底：
    # - 将 views 近似视为所有事件数，用于估算 CTR；
    # - 将 purchases 近似视为真实订单数，用于估算 CVR。
    if views == 0 and total_events > 0:
        views = total_events
    if purchases == 0 and total_orders > 0:
        purchases = total_orders

    ctr = (clicks / views) if views > 0 else 0.0
    cvr = (purchases / clicks) if clicks > 0 else 0.0

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_events": total_events,
        "views": views,
        "clicks": clicks,
        "purchases": purchases,
        "ctr": ctr,
        "cvr": cvr,
        "total_orders": total_orders,
        "revenue": revenue,
        "avg_order_value": avg_order_value,
    }


def compute_offline_eval() -> Dict[str, Any]:
    """
    读取公开测试集上的离线评估结果（例如 top-K 命中率 / MAP）。

    约定文件：data/metrics/recommender_eval.json，推荐格式示例：
    {
      "dataset": "public_test_v1",
      "last_updated": "2026-03-05T12:00:00",
      "topk": [5, 10, 20],
      "hit_rate": [0.32, 0.45, 0.53],
      "map": [0.21, 0.27, 0.30]
    }
    """
    raw = safe_load_json(EVAL_METRICS_JSON, {})
    if not isinstance(raw, dict) or not raw:
        return {}

    dataset = raw.get("dataset", "public_test")
    last_updated = raw.get("last_updated", "-")
    topk = raw.get("topk") or []
    hit_rate = raw.get("hit_rate") or []
    map_scores = raw.get("map") or raw.get("MAP") or []

    rows: List[Dict[str, Any]] = []
    for idx, k in enumerate(topk):
        hr = hit_rate[idx] if idx < len(hit_rate) else None
        mp = map_scores[idx] if idx < len(map_scores) else None
        rows.append({"k": k, "hit_rate": hr, "map": mp})

    return {
        "dataset": dataset,
        "last_updated": last_updated,
        "rows": rows,
    }
