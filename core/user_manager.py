"""
用户管理器
负责用户注册、登录、偏好管理等功能
"""

from typing import Optional, Dict, Any, List
import uuid

from data.models import User, UserAction
from utils.logger import get_logger
from utils.exceptions import AuthenticationError, ValidationError, DatabaseError

logger = get_logger(__name__)


class UserManager:
    """用户管理器"""

    def __init__(self):
        self.current_user: Optional[User] = None

    def register_user(self, username: str, password: str, email: Optional[str] = None) -> User:
        """
        用户注册

        Args:
            username: 用户名
            password: 密码
            email: 邮箱（可选）

        Returns:
            新创建的用户对象

        Raises:
            ValidationError: 用户名已存在或其他验证错误
        """
        try:
            # 验证输入
            self._validate_registration_data(username, password, email)

            # 检查用户名是否已存在
            if User.get_by_username(username):
                raise ValidationError("用户名已存在", field="username", value=username)

            # 生成用户ID
            user_id = str(uuid.uuid4())

            # 创建用户
            user = User.create_user(user_id, username, password, email)
            user.save()

            logger.info(f"用户注册成功: {username} (ID: {user_id})")
            return user

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"用户注册失败: {e}")
            raise DatabaseError(f"用户注册失败: {e}")

    def authenticate_user(self, username: str, password: str) -> User:
        """
        用户登录认证

        Args:
            username: 用户名
            password: 密码

        Returns:
            用户对象

        Raises:
            AuthenticationError: 用户名或密码错误
        """
        try:
            # 获取用户
            user = User.get_by_username(username)
            if not user:
                raise AuthenticationError("用户名不存在", user_id=username)

            # 验证密码
            if not user.verify_password(password):
                raise AuthenticationError("密码错误", user_id=user.user_id)

            self.current_user = user
            logger.info(f"用户登录成功: {username}")

            return user

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"用户认证失败: {e}")
            raise AuthenticationError("认证过程出错")

    def logout_user(self):
        """用户登出"""
        if self.current_user:
            logger.info(f"用户登出: {self.current_user.username}")
            self.current_user = None

    def get_current_user(self) -> Optional[User]:
        """获取当前登录用户"""
        return self.current_user

    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]):
        """
        更新用户偏好设置

        Args:
            user_id: 用户ID
            preferences: 偏好设置字典
        """
        try:
            user = User.get_by_id(user_id)
            if not user:
                raise ValidationError("用户不存在", field="user_id", value=user_id)

            user.update_preferences(preferences)
            logger.info(f"用户{user_id}偏好更新成功")

        except Exception as e:
            logger.error(f"更新用户偏好失败: {e}")
            raise DatabaseError(f"更新用户偏好失败: {e}")

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户档案信息"""
        try:
            user = User.get_by_id(user_id)
            if not user:
                return None

            # 获取用户行为统计
            actions = UserAction.get_user_actions(user_id, limit=1000)

            profile = {
                'user_id': user.user_id,
                'username': user.username,
                'email': user.email,
                'preferences': user.preferences,
                'registration_date': user.created_at,
                'total_actions': len(actions),
                'favorite_categories': self._analyze_favorite_categories(actions),
                'activity_stats': self._calculate_activity_stats(actions)
            }

            return profile

        except Exception as e:
            logger.error(f"获取用户档案失败: {e}")
            return None

    def _analyze_favorite_categories(self, actions: List[UserAction]) -> Dict[str, int]:
        """分析用户偏好的商品分类"""
        from data.models import Product

        category_count = {}
        product_cache = {}  # 缓存商品信息

        for action in actions:
            if action.action_type in ['favorite', 'purchase', 'click']:
                # 获取商品分类
                if action.product_id not in product_cache:
                    try:
                        product = Product.get_by_id(action.product_id)
                        product_cache[action.product_id] = product.category if product else 'unknown'
                    except:
                        product_cache[action.product_id] = 'unknown'

                category = product_cache[action.product_id]
                category_count[category] = category_count.get(category, 0) + 1

        return dict(sorted(category_count.items(), key=lambda x: x[1], reverse=True))

    def _calculate_activity_stats(self, actions: List[UserAction]) -> Dict[str, Any]:
        """计算用户活跃度统计"""
        if not actions:
            return {'total_actions': 0, 'avg_daily_actions': 0, 'most_active_day': None}

        # 按行为类型统计
        action_types = {}
        for action in actions:
            action_types[action.action_type] = action_types.get(action.action_type, 0) + 1

        # 计算日均活跃度（简单估算）
        total_actions = len(actions)
        avg_daily_actions = total_actions / 30  # 假设30天的数据

        return {
            'total_actions': total_actions,
            'avg_daily_actions': round(avg_daily_actions, 2),
            'action_distribution': action_types,
            'most_common_action': max(action_types.items(), key=lambda x: x[1])[0] if action_types else None
        }

    def get_user_recommendation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取用户推荐历史"""
        from data.models import Recommendation

        try:
            recommendations = Recommendation.get_user_recommendations(user_id, limit)

            history = []
            for rec in recommendations:
                history.append({
                    'recommendation_id': rec.rec_id,
                    'products_count': len(rec.recommended_products),
                    'algorithm': rec.algorithm,
                    'score': rec.score,
                    'created_at': rec.created_at,
                    'products': rec.recommended_products
                })

            return history

        except Exception as e:
            logger.error(f"获取用户推荐历史失败: {e}")
            return []

    def _validate_registration_data(self, username: str, password: str, email: Optional[str] = None):
        """验证注册数据"""
        # 用户名验证
        if not username or len(username.strip()) < 3:
            raise ValidationError("用户名长度至少3个字符", field="username", value=username)

        if not username.replace('_', '').replace('-', '').isalnum():
            raise ValidationError("用户名只能包含字母、数字、下划线和连字符", field="username", value=username)

        # 密码验证
        if not password or len(password) < 6:
            raise ValidationError("密码长度至少6个字符", field="password")

        # 邮箱验证（如果提供）
        if email:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                raise ValidationError("邮箱格式不正确", field="email", value=email)

    def reset_user_password(self, user_id: str, old_password: str, new_password: str):
        """重置用户密码"""
        try:
            user = User.get_by_id(user_id)
            if not user:
                raise ValidationError("用户不存在", field="user_id", value=user_id)

            # 验证旧密码
            if not user.verify_password(old_password):
                raise AuthenticationError("旧密码错误", user_id=user_id)

            # 验证新密码
            if len(new_password) < 6:
                raise ValidationError("新密码长度至少6个字符", field="new_password")

            # 更新密码
            user.password_hash = User.hash_password(new_password)
            user.save()

            logger.info(f"用户{user_id}密码重置成功")

        except (ValidationError, AuthenticationError):
            raise
        except Exception as e:
            logger.error(f"重置用户密码失败: {e}")
            raise DatabaseError(f"重置密码失败: {e}")

    def get_user_stats(self) -> Dict[str, Any]:
        """获取用户系统统计信息"""
        try:
            total_users = User.count()
            active_users = 0  # 可以扩展计算活跃用户

            # 计算新注册用户（最近7天）
            # 这里可以添加更复杂的统计逻辑

            return {
                'total_users': total_users,
                'active_users': active_users,
                'new_users_today': 0,  # 暂时设为0
                'user_retention_rate': 0.0  # 暂时设为0
            }

        except Exception as e:
            logger.error(f"获取用户统计失败: {e}")
            return {
                'total_users': 0,
                'active_users': 0,
                'new_users_today': 0,
                'user_retention_rate': 0.0
            }


# 全局用户管理器实例
user_manager = UserManager()

