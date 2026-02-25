"""
数据层模块
包含数据库连接、数据模型、数据访问对象等
"""

from .database import DatabaseManager
from .models import User, Product, UserAction, Recommendation

__all__ = ['DatabaseManager', 'User', 'Product', 'UserAction', 'Recommendation']

