"""
核心业务逻辑模块
包含推荐引擎、用户管理、商品管理等核心功能
"""

from .recommendation_engine import RecommendationEngine
from .user_manager import UserManager
from .product_manager import ProductManager

__all__ = ['RecommendationEngine', 'UserManager', 'ProductManager']

