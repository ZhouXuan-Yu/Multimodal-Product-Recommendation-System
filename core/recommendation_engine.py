"""
推荐引擎
实现多模态融合的个性化推荐算法
"""

import os
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import random

import numpy as np

from config.settings import settings
from data.models import User, Product, UserAction, Recommendation
from utils.logger import get_logger
from utils.exceptions import ModelError, ValidationError

logger = get_logger(__name__)


class RecommendationEngine:
    """推荐引擎类"""

    def __init__(self):
        self.config = settings.RECOMMENDATION_CONFIG
        self.product_embeddings: Dict[str, np.ndarray] = {}
        self.user_profiles: Dict[str, np.ndarray] = {}
        self._load_embeddings()

    def _load_embeddings(self):
        """
        加载训练阶段生成的多模态商品向量和（可选）用户画像。

        优先从 data/embeddings/fused_features_concat.pkl 与 user_profiles.pkl 读取；
        如不存在或格式异常，则回退到基于产品表的随机向量，以保证系统可用。
        """
        embeddings_dir = Path(settings.MODEL_PATHS["embeddings"])
        product_file = embeddings_dir / "fused_features_concat.pkl"
        profiles_file = embeddings_dir / "user_profiles.pkl"

        try:
            logger.info(f"加载商品嵌入向量: {product_file}")

            if product_file.exists():
                with open(product_file, "rb") as f:
                    data = pickle.load(f)

                if isinstance(data, dict):
                    # 标准情况：product_id -> 向量
                    self.product_embeddings = {
                        str(pid): np.asarray(vec, dtype=np.float32)
                        for pid, vec in data.items()
                    }
                else:
                    logger.warning(
                        "融合特征文件格式异常（非 dict），将使用随机初始化商品向量"
                    )
                    self._init_random_product_embeddings()
            else:
                logger.warning(
                    f"未找到融合特征文件: {product_file}，将使用随机初始化商品向量"
                )
                self._init_random_product_embeddings()

            # 尝试加载用户画像（可选）
            if profiles_file.exists():
                try:
                    with open(profiles_file, "rb") as f:
                        profiles = pickle.load(f)

                    if isinstance(profiles, dict):
                        self.user_profiles = {
                            str(uid): np.asarray(vec, dtype=np.float32)
                            for uid, vec in profiles.items()
                        }
                        logger.info(
                            f"用户画像加载完成，共 {len(self.user_profiles)} 条"
                        )
                    else:
                        logger.warning("用户画像文件格式异常（非 dict），忽略")
                except Exception as e:
                    logger.warning(f"加载用户画像失败，将在运行时按行为计算: {e}")
            else:
                logger.info("未找到用户画像文件，将在运行时按行为计算用户画像")

            logger.info(
                f"商品嵌入加载完成，共 {len(self.product_embeddings)} 条"
            )

        except Exception as e:
            logger.warning(f"加载嵌入向量失败，将使用空嵌入集: {e}")
            self.product_embeddings = {}
            self.user_profiles = {}

    def _init_random_product_embeddings(self, dim: int = 128):
        """
        当真实嵌入文件缺失时，为现有商品生成随机向量。
        这样系统仍可工作（但推荐效果仅用于演示）。
        """
        try:
            products = Product.get_all(limit=1000)
            if not products:
                logger.warning("产品表为空，无法初始化随机商品向量")
                return

            self.product_embeddings = {
                p.product_id: np.random.randn(dim).astype(np.float32)
                for p in products
            }
            logger.info(
                f"已为 {len(self.product_embeddings)} 个商品生成随机嵌入（维度={dim}）"
            )
        except Exception as e:
            logger.warning(f"初始化随机商品向量失败: {e}")

    def generate_recommendations(self, user_id: str, top_k: Optional[int] = None) -> List[str]:
        """
        为用户生成个性化推荐

        Args:
            user_id: 用户ID
            top_k: 返回推荐数量，默认使用配置值

        Returns:
            推荐商品ID列表
        """
        if top_k is None:
            top_k = self.config['top_k']

        try:
            # 获取用户画像
            user_profile = self._get_user_profile(user_id)

            if user_profile is None:
                # 冷启动用户，使用热门商品推荐
                return self._cold_start_recommendations(top_k)

            # 计算相似度
            candidates = self._calculate_similarity(user_profile, top_k * 2)

            # 应用业务规则过滤
            filtered_candidates = self._apply_business_rules(user_id, candidates, top_k)

            # 应用多样性和新颖性
            final_recommendations = self._apply_diversity_and_novelty(
                user_id, filtered_candidates, top_k
            )

            # 保存推荐结果
            self._save_recommendations(user_id, final_recommendations)

            logger.info(f"为用户{user_id}生成{len(final_recommendations)}个推荐")
            return final_recommendations

        except Exception as e:
            logger.error(f"为用户{user_id}生成推荐失败: {e}")
            # 返回热门商品作为fallback
            return self._cold_start_recommendations(top_k)

    def _get_user_profile(self, user_id: str) -> Optional[np.ndarray]:
        """获取用户画像向量"""
        try:
            # 获取用户历史行为
            actions = UserAction.get_user_actions(user_id, limit=50)

            if not actions:
                return None

            # 基于历史交互的商品计算用户画像
            interacted_products = []
            weights = []

            for action in actions:
                if action.product_id in self.product_embeddings:
                    interacted_products.append(self.product_embeddings[action.product_id])

                    # 根据行为类型设置权重
                    weight = {
                        'view': 0.1,
                        'click': 0.3,
                        'favorite': 0.7,
                        'purchase': 1.0
                    }.get(action.action_type, 0.1)
                    weights.append(weight)

            if not interacted_products:
                return None

            # 加权平均得到用户画像
            weights = np.array(weights)
            weights = weights / weights.sum()  # 归一化

            user_profile = np.average(interacted_products, axis=0, weights=weights)
            return user_profile

        except Exception as e:
            logger.error(f"获取用户{user_id}画像失败: {e}")
            return None

    def _calculate_similarity(self, user_profile: np.ndarray, candidate_count: int) -> List[Tuple[str, float]]:
        """计算用户与商品的相似度"""
        try:
            similarities = []

            for product_id, product_embedding in self.product_embeddings.items():
                # 计算余弦相似度
                similarity = self._cosine_similarity(user_profile, product_embedding)
                similarities.append((product_id, similarity))

            # 按相似度排序
            similarities.sort(key=lambda x: x[1], reverse=True)

            return similarities[:candidate_count]

        except Exception as e:
            logger.error(f"计算相似度失败: {e}")
            return []

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        try:
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return dot_product / (norm1 * norm2)
        except Exception:
            return 0.0

    def _apply_business_rules(self, user_id: str, candidates: List[Tuple[str, float]], top_k: int) -> List[Tuple[str, float]]:
        """应用业务规则过滤候选集"""
        try:
            filtered_candidates = []

            # 获取用户已交互的商品
            user_actions = UserAction.get_user_actions(user_id)
            interacted_products = {action.product_id for action in user_actions}

            for product_id, score in candidates:
                # 过滤已购买的商品
                if any(action.product_id == product_id and action.action_type == 'purchase'
                      for action in user_actions):
                    continue

                # 应用相似度阈值
                if score < self.config['similarity_threshold']:
                    continue

                filtered_candidates.append((product_id, score))

            return filtered_candidates[:top_k]

        except Exception as e:
            logger.error(f"应用业务规则失败: {e}")
            return candidates[:top_k]

    def _apply_diversity_and_novelty(self, user_id: str, candidates: List[Tuple[str, float]], top_k: int) -> List[str]:
        """应用多样性和新颖性调整"""
        try:
            if not candidates:
                return []

            # 获取候选商品的分类信息
            product_categories = {}
            for product_id, _ in candidates:
                try:
                    product = Product.get_by_id(product_id)
                    if product:
                        product_categories[product_id] = product.category or 'unknown'
                except:
                    product_categories[product_id] = 'unknown'

            # 多样性选择：确保不同分类的商品
            category_count = defaultdict(int)
            selected_products = []

            # 首先选择最高分的商品
            candidates.sort(key=lambda x: x[1], reverse=True)

            for product_id, score in candidates:
                if len(selected_products) >= top_k:
                    break

                category = product_categories.get(product_id, 'unknown')

                # 控制每个分类的数量（最多不超过总数的1/3）
                max_per_category = max(1, top_k // 3)
                if category_count[category] >= max_per_category:
                    continue

                selected_products.append(product_id)
                category_count[category] += 1

            # 如果选择不足，用随机商品补充
            while len(selected_products) < top_k and candidates:
                remaining = [pid for pid, _ in candidates if pid not in selected_products]
                if remaining:
                    selected_products.append(random.choice(remaining))
                else:
                    break

            return selected_products

        except Exception as e:
            logger.error(f"应用多样性调整失败: {e}")
            return [pid for pid, _ in candidates[:top_k]]

    def _cold_start_recommendations(self, top_k: int) -> List[str]:
        """冷启动推荐：返回热门商品"""
        try:
            popular_products = UserAction.get_popular_products(limit=top_k * 2)
            return [item['product_id'] for item in popular_products[:top_k]]
        except Exception as e:
            logger.error(f"冷启动推荐失败: {e}")
            # 返回随机商品作为最后的fallback
            try:
                all_products = Product.get_all(limit=top_k * 2)
                selected = random.sample(all_products, min(len(all_products), top_k))
                return [p.product_id for p in selected]
            except:
                return []

    def _save_recommendations(self, user_id: str, product_ids: List[str]):
        """保存推荐结果"""
        try:
            recommendation = Recommendation()
            recommendation.user_id = user_id
            recommendation.recommended_products = product_ids
            recommendation.algorithm = "multimodal_fusion"
            recommendation.score = 0.85  # 示例评分

            recommendation.save()
            logger.debug(f"保存用户{user_id}的推荐结果")
        except Exception as e:
            logger.error(f"保存推荐结果失败: {e}")

    def update_user_profile(self, user_id: str, product_id: str, action_type: str, rating: Optional[int] = None):
        """更新用户画像（实时学习）"""
        try:
            # 记录用户行为
            action = UserAction()
            action.user_id = user_id
            action.product_id = product_id
            action.action_type = action_type
            action.rating = rating
            action.save()

            # 更新用户画像缓存
            if user_id in self.user_profiles:
                # 这里可以实现实时更新用户画像的逻辑
                pass

            logger.debug(f"更新用户{user_id}画像，行为:{action_type}，商品:{product_id}")

        except Exception as e:
            logger.error(f"更新用户画像失败: {e}")
            raise ModelError(f"更新用户画像失败: {e}")

    def get_similar_products(self, product_id: str, top_k: int = 5) -> List[str]:
        """获取相似商品（用于商品详情页推荐）"""
        try:
            if product_id not in self.product_embeddings:
                return []

            target_embedding = self.product_embeddings[product_id]
            similarities = []

            for pid, embedding in self.product_embeddings.items():
                if pid != product_id:
                    similarity = self._cosine_similarity(target_embedding, embedding)
                    similarities.append((pid, similarity))

            similarities.sort(key=lambda x: x[1], reverse=True)
            return [pid for pid, _ in similarities[:top_k]]

        except Exception as e:
            logger.error(f"获取相似商品失败: {e}")
            return []

    def get_recommendation_stats(self) -> Dict[str, Any]:
        """获取推荐系统统计信息"""
        try:
            stats = {
                'total_users': User.count(),
                'total_products': Product.count(),
                'total_actions': UserAction.count(),
                'total_recommendations': Recommendation.count(),
                'embedding_coverage': len(self.product_embeddings),
                'active_users_today': 0,  # 可以扩展实现
            }
            return stats
        except Exception as e:
            logger.error(f"获取推荐统计失败: {e}")
            return {}

