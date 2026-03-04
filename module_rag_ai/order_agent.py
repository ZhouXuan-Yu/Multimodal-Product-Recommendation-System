"""订单导购 Agent：封装订单状态机与 DeepSeek 辅助文案."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from .deepseek_agent import DeepSeekAgent


OrderStatus = Literal["pending", "paid", "processing", "shipped", "cancelled"]


@dataclass
class OrderItem:
    product_id: str
    quantity: int
    unit_price: float


@dataclass
class Order:
    order_id: str
    user_id: str
    status: OrderStatus
    items: List[OrderItem]
    total_amount: float
    currency: str
    created_at: str
    updated_at: str
    note: str | None = None
    payment_channel: str | None = None
    paid_at: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["items"] = [asdict(it) for it in self.items]
        return payload


class InvalidTransitionError(RuntimeError):
    """非法状态流转."""


class OrderAgent:
    """订单导购 Agent.

    - 维护简单订单状态机：pending -> paid -> processing -> shipped / cancelled
    - 使用 DeepSeek 为订单生成自然语言摘要与确认话术（可选）
    """

    def __init__(self, enable_llm: bool = True) -> None:
        self.enable_llm = enable_llm
        self._agent = DeepSeekAgent() if enable_llm else None

    # ============ 状态机核心 ============ #
    @staticmethod
    def allow_transition(current: OrderStatus, target: OrderStatus) -> bool:
        graph: Dict[OrderStatus, List[OrderStatus]] = {
            "pending": ["paid", "cancelled"],
            "paid": ["processing", "cancelled"],
            "processing": ["shipped", "cancelled"],
            "shipped": [],
            "cancelled": [],
        }
        return target in graph[current]

    def transit(self, order: Order, target: OrderStatus) -> Order:
        if not self.allow_transition(order.status, target):
            raise InvalidTransitionError(f"非法状态流转: {order.status} -> {target}")
        now = datetime.utcnow().isoformat()
        order.status = target
        order.updated_at = now
        if target == "paid" and not order.paid_at:
            order.paid_at = now
        return order

    # ============ LLM 话术封装（可选） ============ #
    def build_order_summary_prompt(
        self,
        order: Order,
        user_profile: Optional[Dict[str, Any]] = None,
        products_map: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> str:
        """构建给 DeepSeek 的订单摘要 Prompt."""
        payload: Dict[str, Any] = {
            "user_id": order.user_id,
            "order_id": order.order_id,
            "status": order.status,
            "total_amount": order.total_amount,
            "currency": order.currency,
            "items": [
                {
                    "product_id": it.product_id,
                    "quantity": it.quantity,
                    "unit_price": it.unit_price,
                    "product": (products_map or {}).get(it.product_id),
                }
                for it in order.items
            ],
            "user_profile": user_profile or {},
            "instruction": (
                "请用简洁自然的中文生成一段 40~80 字的下单确认话术，"
                "向用户总结本次订单的核心信息（品类、价格区间、适合场景），"
                "避免重复堆砌明细，不要输出 JSON 或 Markdown 代码块。"
            ),
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def summarize_order(
        self,
        order: Order,
        user_profile: Optional[Dict[str, Any]] = None,
        products_map: Optional[Dict[str, Dict[str, Any]]] = None,
        timeout: int = 30,
    ) -> str:
        """调用 DeepSeek 生成订单确认文案，失败时返回降级模板."""
        if not self.enable_llm or not self._agent:
            return self._fallback_summary(order)

        prompt = self.build_order_summary_prompt(order, user_profile, products_map)
        try:
            text = self._agent._chat(  # noqa: SLF001
                system_prompt=(
                    "你是一名电商导购助手，擅长根据用户的订单信息生成友好、专业的确认话术。"
                    "只输出一小段自然语言，不要输出 JSON 或 Markdown 代码块。"
                ),
                user_content=prompt,
                timeout=timeout,
            )
            return text.strip()
        except Exception:  # noqa: BLE001
            return self._fallback_summary(order)

    @staticmethod
    def _fallback_summary(order: Order) -> str:
        return (
            f"已为你创建订单（编号：{order.order_id}），共 {len(order.items)} 件商品，"
            f"合计约 {order.total_amount:.2f} {order.currency}。"
            "你可以在订单列表中查看详情和后续物流进度。"
        )

