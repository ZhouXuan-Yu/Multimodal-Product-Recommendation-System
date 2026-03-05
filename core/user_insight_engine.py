"""
用户画像与洞察引擎（Phase 3）

职责：
- 统一管理用户行为打点（行为 -> 评分/权重）
- 维护 ChromaDB 中的 user_personas 向量集合（偏好中心向量）
- 基于时间衰减与 Vector Shifting 动态更新用户画像
- 提供画像与行为统计的聚合接口，支撑前端“数据洞察中心”与 Rerank
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from module_rag_ai.multimodal_embedding import ChineseCLIPEmbedder
from module_rag_ai.vector_db_manager import VectorDBManager
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class UserBehaviorEvent:
    user_id: str
    product_id: str
    action_type: str  # click/like/dislike/view/purchase
    timestamp: datetime
    dwell_time: float = 0.0  # 停留时长（秒）


class UserInsightEngine:
    """
    用户画像/洞察引擎。

    画像存储：
        - 在 ChromaDB 中维护一个名为 user_personas 的集合，
          其中每条记录的 id = user_id，embedding = persona_vector。

    行为权重示例（可根据业务微调）：
        view      -> +0.5
        click     -> +1
        like      -> +3
        dislike   -> -5
        purchase  -> +10

    Vector Shifting 核心公式：
        V_new = Normalize((1 - η) * V_old + η * V_item)
        其中 η 由行为权重和时间衰减共同决定。
    """

    ACTION_WEIGHTS: Dict[str, float] = {
        "view": 0.5,
        "click": 1.0,
        "like": 3.0,
        "favorite": 3.0,
        "purchase": 10.0,
        "dislike": -5.0,
    }

    def __init__(
        self,
        vector_db: Optional[VectorDBManager] = None,
        embedder: Optional[ChineseCLIPEmbedder] = None,
        persona_collection_name: str = "user_personas",
    ) -> None:
        # 这里不再向 VectorDBManager 传入 None 作为 collection_name，
        # 避免在 chromadb.get_or_create_collection(name=None) 时触发 TypeError。
        # 默认使用 VectorDBManager 自身的默认集合（商品向量），
        # 而用户画像使用单独的 persona_collection。
        self.vector_db = vector_db or VectorDBManager()
        # 为用户画像单独创建/获取一个集合
        self.persona_collection = self.vector_db.client.get_or_create_collection(
            name=persona_collection_name
        )
        self.embedder = embedder or ChineseCLIPEmbedder()

    # ------------------------------------------------------------------
    # 行为打分与时间衰减
    # ------------------------------------------------------------------
    def _base_weight(self, action_type: str) -> float:
        return self.ACTION_WEIGHTS.get(action_type, 0.0)

    @staticmethod
    def _time_decay_factor(
        ts: datetime,
        now: Optional[datetime] = None,
        half_life_hours: float = 24.0,
    ) -> float:
        """
        指数时间衰减因子：越早的行为影响越小。

        decay = 0.5 ** (Δt / half_life)
        """
        if now is None:
            now = datetime.utcnow()
        delta = now - ts
        hours = max(delta.total_seconds(), 0.0) / 3600.0
        if half_life_hours <= 0:
            return 1.0
        return 0.5 ** (hours / half_life_hours)

    def compute_effective_lr(
        self,
        event: UserBehaviorEvent,
        base_eta: float = 0.2,
        half_life_hours: float = 24.0,
    ) -> float:
        """
        计算该行为对画像更新的“有效学习率 η”。

        - 行为权重越大（如 purchase），η 越大；
        - 行为越新（时间衰减越小），η 越大；
        - 可追加与停留时长关联的放大因子。
        """
        w = self._base_weight(event.action_type)
        decay = self._time_decay_factor(event.timestamp, half_life_hours=half_life_hours)
        # 将负向权重绝对值用于学习率（方向由后续逻辑决定）
        magnitude = abs(w)
        # 简单线性归一 + 上限裁剪
        eta = base_eta * magnitude * decay
        return float(np.clip(eta, 0.0, 0.8))

    # ------------------------------------------------------------------
    # 画像向量的读取 / 写入（Chroma user_personas）
    # ------------------------------------------------------------------
    def get_persona_vector(self, user_id: str) -> Optional[np.ndarray]:
        """从 Chroma user_personas 中读取用户画像向量。"""
        try:
            res = self.persona_collection.get(ids=[user_id], include=["embeddings"])
        except Exception as exc:  # noqa: BLE001
            logger.error("获取用户画像失败 user_id=%s, err=%s", user_id, exc)
            return None

        emb_list = res.get("embeddings")
        # Chroma 可能返回 list[list[float]] 或 numpy.ndarray，需要显式判断长度而不是直接用 "or []"
        if emb_list is None:
            return None
        # 统一转为 Python list 再判断
        if isinstance(emb_list, np.ndarray):
            if emb_list.size == 0:
                return None
            first = emb_list[0]
        else:
            if not emb_list:
                return None
            first = emb_list[0]

        if first is None:
            return None
        return np.asarray(first, dtype=np.float32)

    def upsert_persona_vector(self, user_id: str, vector: np.ndarray) -> None:
        """将 persona_vector 写回 Chroma user_personas。"""
        try:
            self.persona_collection.upsert(
                ids=[user_id],
                embeddings=[vector.astype(float).tolist()],
                metadatas=[{"user_id": user_id, "updated_at": datetime.utcnow().isoformat()}],
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("写入用户画像失败 user_id=%s, err=%s", user_id, exc)

    # ------------------------------------------------------------------
    # Vector Shifting：单次行为驱动的画像更新
    # ------------------------------------------------------------------
    def _normalize(self, v: np.ndarray) -> np.ndarray:
        norm = float(np.linalg.norm(v))
        if norm == 0.0:
            return v
        return v / norm

    def update_persona_with_event(
        self,
        event: UserBehaviorEvent,
        item_vector: np.ndarray,
        base_eta: float = 0.2,
        half_life_hours: float = 24.0,
    ) -> Optional[np.ndarray]:
        """
        根据单条行为事件更新用户画像：

        - 正反馈（view/click/like/favorite/purchase）：
            V_new = Normalize((1 - η) * V_old + η * V_item)
        - 负反馈（dislike）：
            采用“远离”策略：
            V_new = Normalize(V_old - η * V_item)
        """
        # 取出旧画像；如不存在则以商品向量为初始画像
        old = self.get_persona_vector(event.user_id)
        if old is None:
            old = self._normalize(item_vector.astype(np.float32))

        eta = self.compute_effective_lr(event, base_eta=base_eta, half_life_hours=half_life_hours)
        if eta <= 0.0:
            logger.debug("行为权重过低，不更新画像: %s", event)
            return old

        w = self._base_weight(event.action_type)
        if w >= 0:
            new_vec = (1.0 - eta) * old + eta * item_vector
        else:
            # 负向反馈：让画像远离该商品向量
            new_vec = old - eta * item_vector

        new_vec = self._normalize(new_vec.astype(np.float32))
        self.upsert_persona_vector(event.user_id, new_vec)
        logger.info(
            "用户画像已更新 user_id=%s, action=%s, eta=%.4f, base_w=%.2f",
            event.user_id,
            event.action_type,
            eta,
            w,
        )
        return new_vec

    # ------------------------------------------------------------------
    # 画像 + 洞察统计输出，供前端“数据洞察中心”与 Rerank 使用
    # ------------------------------------------------------------------
    def build_rerank_context(
        self,
        user_id: str,
        recent_tags: Optional[List[str]] = None,
        recent_categories: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        输出一个紧凑的“画像上下文”，用于注入 DeepSeek Rerank Prompt：

        - persona_vector: 当前 Chroma 中的用户偏好中心向量（可选，为节省 token 可只给摘要信息）；
        - recent_tags / recent_categories: 近期高频风格标签与品类；
        - meta：时间戳等。
        """
        persona = self.get_persona_vector(user_id)
        # 为了控制 Prompt 长度，不直接塞入整条向量，而是给出截断信息
        persona_preview: Optional[List[float]] = None
        if persona is not None:
            # 只保留前 16 维作为“预览”，其余维度仍然存在于向量库中用于相似度计算
            persona_preview = persona[:16].round(4).tolist()  # type: ignore[assignment]

        return {
            "user_id": user_id,
            "persona_vector_preview": persona_preview,
            "recent_tags": recent_tags or [],
            "recent_categories": recent_categories or [],
            "updated_at": datetime.utcnow().isoformat(),
        }

