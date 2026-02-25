"""
数据模型定义
包含所有数据库表的ORM模型
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import hashlib

from data.database import db_manager
from utils.logger import get_logger
from utils.exceptions import ValidationError, DatabaseError

logger = get_logger(__name__)


class BaseModel:
    """基础模型类"""

    table_name: str = ""
    primary_key: str = ""

    @classmethod
    def _validate_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证数据"""
        return data

    @classmethod
    def _to_dict(cls, row: Dict[str, Any]) -> Dict[str, Any]:
        """将数据库行转换为字典"""
        return dict(row)

    @classmethod
    def create(cls, **kwargs) -> 'BaseModel':
        """创建新记录"""
        instance = cls()
        instance.__dict__.update(kwargs)
        return instance

    def save(self) -> bool:
        """保存到数据库"""
        try:
            data = self._validate_data(self.__dict__)
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['%s'] * len(data))
            values = tuple(data.values())

            query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"
            db_manager.execute_update(query, values)

            # 如果有自增主键，获取插入的ID
            if hasattr(self, 'id'):
                # 这里可以获取最后插入的ID，但需要具体实现
                pass

            logger.debug(f"保存{self.table_name}记录成功")
            return True
        except Exception as e:
            logger.error(f"保存{self.table_name}记录失败: {e}")
            raise DatabaseError(f"保存记录失败: {e}")

    @classmethod
    def get_by_id(cls, id_value: Any) -> Optional['BaseModel']:
        """根据ID获取记录"""
        try:
            query = f"SELECT * FROM {cls.table_name} WHERE {cls.primary_key} = %s"
            result = db_manager.execute_query(query, (id_value,))

            if result:
                data = cls._to_dict(result[0])
                return cls.create(**data)
            return None
        except Exception as e:
            logger.error(f"获取{cls.table_name}记录失败: {e}")
            raise DatabaseError(f"获取记录失败: {e}")

    @classmethod
    def get_all(cls, limit: int = 100, offset: int = 0) -> List['BaseModel']:
        """获取所有记录"""
        try:
            query = f"SELECT * FROM {cls.table_name} LIMIT %s OFFSET %s"
            results = db_manager.execute_query(query, (limit, offset))

            return [cls.create(**cls._to_dict(row)) for row in results]
        except Exception as e:
            logger.error(f"获取{cls.table_name}所有记录失败: {e}")
            raise DatabaseError(f"获取记录失败: {e}")

    @classmethod
    def count(cls) -> int:
        """统计记录数量"""
        try:
            query = f"SELECT COUNT(*) as count FROM {cls.table_name}"
            result = db_manager.execute_query(query)
            return result[0]['count'] if result else 0
        except Exception as e:
            logger.error(f"统计{cls.table_name}记录数量失败: {e}")
            return 0


class User(BaseModel):
    """用户模型"""

    table_name = "users"
    primary_key = "user_id"

    def __init__(self):
        self.user_id: str = ""
        self.username: str = ""
        self.password_hash: str = ""
        self.email: Optional[str] = None
        self.preferences: Dict[str, Any] = {}
        self.created_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None

    @staticmethod
    def hash_password(password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()

    @classmethod
    def create_user(cls, user_id: str, username: str, password: str, email: Optional[str] = None) -> 'User':
        """创建用户"""
        user = cls()
        user.user_id = user_id
        user.username = username
        user.password_hash = cls.hash_password(password)
        user.email = email
        user.preferences = {}
        return user

    def verify_password(self, password: str) -> bool:
        """验证密码"""
        return self.password_hash == self.hash_password(password)

    @classmethod
    def get_by_username(cls, username: str) -> Optional['User']:
        """根据用户名获取用户"""
        try:
            query = "SELECT * FROM users WHERE username = %s"
            result = db_manager.execute_query(query, (username,))

            if result:
                data = cls._to_dict(result[0])
                return cls.create(**data)
            return None
        except Exception as e:
            logger.error(f"根据用户名获取用户失败: {e}")
            return None

    def update_preferences(self, preferences: Dict[str, Any]):
        """更新用户偏好"""
        self.preferences.update(preferences)
        try:
            query = "UPDATE users SET preferences = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s"
            db_manager.execute_update(query, (json.dumps(self.preferences), self.user_id))
            logger.debug(f"用户{self.user_id}偏好更新成功")
        except Exception as e:
            logger.error(f"用户{self.user_id}偏好更新失败: {e}")
            raise DatabaseError(f"更新用户偏好失败: {e}")


class Product(BaseModel):
    """商品模型"""

    table_name = "products"
    primary_key = "product_id"

    def __init__(self):
        self.product_id: str = ""
        self.title: str = ""
        self.description: Optional[str] = None
        self.price: Optional[float] = None
        self.category: Optional[str] = None
        self.image_path: Optional[str] = None
        self.feature_vector_path: Optional[str] = None
        self.rating: float = 0.0
        self.created_at: Optional[datetime] = None

    @classmethod
    def get_by_category(cls, category: str, limit: int = 50) -> List['Product']:
        """根据分类获取商品"""
        try:
            query = "SELECT * FROM products WHERE category = %s LIMIT %s"
            results = db_manager.execute_query(query, (category, limit))
            return [cls.create(**cls._to_dict(row)) for row in results]
        except Exception as e:
            logger.error(f"根据分类获取商品失败: {e}")
            return []

    @classmethod
    def search(cls, keyword: str, limit: int = 50) -> List['Product']:
        """搜索商品"""
        try:
            search_pattern = f"%{keyword}%"
            query = """
                SELECT * FROM products
                WHERE title LIKE %s OR description LIKE %s
                LIMIT %s
            """
            results = db_manager.execute_query(query, (search_pattern, search_pattern, limit))
            return [cls.create(**cls._to_dict(row)) for row in results]
        except Exception as e:
            logger.error(f"搜索商品失败: {e}")
            return []

    def update_rating(self, new_rating: float):
        """更新商品评分"""
        try:
            query = "UPDATE products SET rating = %s WHERE product_id = %s"
            db_manager.execute_update(query, (new_rating, self.product_id))
            self.rating = new_rating
            logger.debug(f"商品{self.product_id}评分更新为{new_rating}")
        except Exception as e:
            logger.error(f"商品{self.product_id}评分更新失败: {e}")
            raise DatabaseError(f"更新商品评分失败: {e}")


class UserAction(BaseModel):
    """用户行为模型"""

    table_name = "user_actions"
    primary_key = "action_id"

    ACTION_TYPES = ['view', 'click', 'favorite', 'purchase']

    def __init__(self):
        self.action_id: Optional[int] = None
        self.user_id: str = ""
        self.product_id: str = ""
        self.action_type: str = ""
        self.rating: Optional[int] = None
        self.timestamp: Optional[datetime] = None

    @classmethod
    def _validate_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证数据"""
        if data.get('action_type') not in cls.ACTION_TYPES:
            raise ValidationError(f"无效的行为类型: {data.get('action_type')}")
        return data

    @classmethod
    def get_user_actions(cls, user_id: str, limit: int = 100) -> List['UserAction']:
        """获取用户行为记录"""
        try:
            query = """
                SELECT * FROM user_actions
                WHERE user_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """
            results = db_manager.execute_query(query, (user_id, limit))
            return [cls.create(**cls._to_dict(row)) for row in results]
        except Exception as e:
            logger.error(f"获取用户{user_id}行为记录失败: {e}")
            return []

    @classmethod
    def get_user_favorites(cls, user_id: str) -> List[str]:
        """获取用户收藏的商品ID"""
        try:
            query = """
                SELECT product_id FROM user_actions
                WHERE user_id = %s AND action_type = 'favorite'
                ORDER BY timestamp DESC
            """
            results = db_manager.execute_query(query, (user_id,))
            return [row['product_id'] for row in results]
        except Exception as e:
            logger.error(f"获取用户{user_id}收藏失败: {e}")
            return []

    @classmethod
    def get_popular_products(cls, limit: int = 10) -> List[Dict[str, Any]]:
        """获取热门商品"""
        try:
            query = """
                SELECT product_id, COUNT(*) as action_count
                FROM user_actions
                WHERE action_type IN ('click', 'favorite', 'purchase')
                GROUP BY product_id
                ORDER BY action_count DESC
                LIMIT %s
            """
            results = db_manager.execute_query(query, (limit,))
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"获取热门商品失败: {e}")
            return []


class Recommendation(BaseModel):
    """推荐结果模型"""

    table_name = "recommendations"
    primary_key = "rec_id"

    def __init__(self):
        self.rec_id: Optional[int] = None
        self.user_id: str = ""
        self.recommended_products: List[str] = []
        self.algorithm: str = "multimodal_fusion"
        self.score: float = 0.0
        self.created_at: Optional[datetime] = None

    @classmethod
    def _validate_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证数据"""
        if 'recommended_products' in data:
            if isinstance(data['recommended_products'], list):
                data['recommended_products'] = json.dumps(data['recommended_products'])
        return data

    @classmethod
    def _to_dict(cls, row: Dict[str, Any]) -> Dict[str, Any]:
        """转换数据库行"""
        data = dict(row)
        if 'recommended_products' in data and data['recommended_products']:
            try:
                data['recommended_products'] = json.loads(data['recommended_products'])
            except:
                data['recommended_products'] = []
        return data

    @classmethod
    def get_user_recommendations(cls, user_id: str, limit: int = 5) -> List['Recommendation']:
        """获取用户推荐记录"""
        try:
            query = """
                SELECT * FROM recommendations
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """
            results = db_manager.execute_query(query, (user_id, limit))
            return [cls.create(**cls._to_dict(row)) for row in results]
        except Exception as e:
            logger.error(f"获取用户{user_id}推荐记录失败: {e}")
            return []

    @classmethod
    def get_latest_recommendation(cls, user_id: str) -> Optional['Recommendation']:
        """获取用户最新推荐"""
        try:
            query = """
                SELECT * FROM recommendations
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """
            result = db_manager.execute_query(query, (user_id,))
            if result:
                return cls.create(**cls._to_dict(result[0]))
            return None
        except Exception as e:
            logger.error(f"获取用户{user_id}最新推荐失败: {e}")
            return None

