"""
测试基础类
提供测试的基础设置和工具方法
"""

import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class BaseTestCase(unittest.TestCase):
    """测试基础类"""

    def setUp(self):
        """测试前准备"""
        self.logger = get_logger(self.__class__.__name__)
        self.logger.info(f"开始测试: {self.__class__.__name__}.{self._testMethodName}")

        # 保存原始设置
        self.original_settings = {}

    def tearDown(self):
        """测试后清理"""
        self.logger.info(f"结束测试: {self.__class__.__name__}.{self._testMethodName}")

        # 恢复原始设置
        for key, value in self.original_settings.items():
            setattr(settings, key, value)

    def mock_database_connection(self):
        """模拟数据库连接"""
        from data.database import db_manager

        # 创建模拟连接
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # 设置模拟返回值
        mock_cursor.fetchone.return_value = None
        mock_cursor.fetchall.return_value = []
        mock_cursor.rowcount = 0

        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None

        # 替换数据库管理器的连接方法
        original_get_connection = db_manager.get_connection
        db_manager.get_connection = MagicMock(return_value=mock_conn)

        # 保存原始方法以便恢复
        self.addCleanup(lambda: setattr(db_manager, 'get_connection', original_get_connection))

        return mock_conn, mock_cursor

    def create_test_user(self, user_id="test_user", username="testuser", password="testpass"):
        """创建测试用户"""
        from data.models import User
        user = User.create_user(user_id, username, password)
        return user

    def create_test_product(self, product_id="test_product", title="测试商品", price=99.99):
        """创建测试商品"""
        from data.models import Product
        product = Product()
        product.product_id = product_id
        product.title = title
        product.price = price
        product.category = "测试分类"
        return product

    def assertDictContains(self, subset, dictionary, msg=None):
        """断言字典包含子集"""
        for key, value in subset.items():
            self.assertIn(key, dictionary, msg)
            self.assertEqual(value, dictionary[key], msg)


class DatabaseTestCase(BaseTestCase):
    """数据库测试基础类"""

    def setUp(self):
        super().setUp()

        # 设置测试数据库
        os.environ['DB_NAME'] = 'multimodal_recommendation_test'

        from data.database import db_manager

        # 创建测试表
        try:
            db_manager.create_tables()
        except Exception as e:
            self.logger.warning(f"创建测试表失败: {e}")

    def tearDown(self):
        super().tearDown()

        # 清理测试数据
        try:
            from data.database import db_manager
            # 这里可以添加清理测试数据的逻辑
            pass
        except Exception as e:
            self.logger.warning(f"清理测试数据失败: {e}")


def run_tests():
    """运行所有测试"""
    # 发现并运行测试
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent
    suite = loader.discover(start_dir, pattern='test_*.py')

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)

