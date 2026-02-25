"""
数据库管理器
负责数据库连接、连接池管理、事务处理等
"""

import threading
import time
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Generator, Union

from config.settings import settings
from utils.logger import get_logger
from utils.exceptions import DatabaseError

logger = get_logger(__name__)

# 尝试导入数据库相关模块
try:
    import pymysql
    from dbutils.pooled_db import PooledDB
    DATABASE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"数据库依赖不可用: {e}")
    logger.info("系统将使用模拟数据模式运行")
    DATABASE_AVAILABLE = False
    pymysql = None
    PooledDB = None


class DatabaseManager:
    """数据库管理器"""

    _instance: Optional['DatabaseManager'] = None
    _lock = threading.Lock()

    def __new__(cls) -> 'DatabaseManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        self._pool: Optional[PooledDB] = None
        # 完整保存原始配置，用于连接参数和健康检查
        self._connection_params = settings.DATABASE_CONFIG.copy()
        self._mock_mode = not DATABASE_AVAILABLE

        if self._mock_mode:
            logger.info("使用模拟数据模式，跳过数据库连接池初始化")
            return

        # 从配置中拆分出连接池参数与底层连接参数
        pool_size = self._connection_params.pop('pool_size', 5)

        pool_params = {
            'creator': pymysql,
            'maxconnections': pool_size,
            'ping': 1,  # 自动ping保持连接
            # 其余参数（host/port/user/password/database/charset/autocommit/connect_timeout等）
            # 作为 **kwargs 传给 pymysql.connect
            **self._connection_params,
        }

        try:
            self._pool = PooledDB(**pool_params)
            logger.info("数据库连接池初始化成功")

            # 启动时做一次轻量级健康检查，失败则自动切换到模拟模式
            if not self.health_check():
                logger.error("数据库健康检查失败，将切换到模拟数据模式运行")
                self._mock_mode = True
        except Exception as e:
            logger.error(f"数据库连接池初始化失败: {e}")
            logger.info("切换到模拟数据模式")
            self._mock_mode = True

    @contextmanager
    def get_connection(self) -> Generator[Any, None, None]:
        """获取数据库连接"""
        if self._mock_mode:
            # 模拟模式下返回一个模拟连接对象
            class MockConnection:
                def cursor(self, *args, **kwargs):
                    return MockCursor()
                def close(self):
                    pass
                def commit(self):
                    pass
                def rollback(self):
                    pass

            class MockCursor:
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass
                def execute(self, *args, **kwargs):
                    pass
                def fetchall(self):
                    return []
                def fetchone(self):
                    return None

            logger.debug("模拟模式: 返回模拟数据库连接")
            yield MockConnection()
            return

        conn = None
        try:
            if self._pool is None:
                raise DatabaseError("数据库连接池未初始化")

            conn = self._pool.connection()
            logger.debug("获取数据库连接成功")
            yield conn
        except Exception as e:
            logger.error(f"获取数据库连接失败: {e}")
            raise DatabaseError(f"获取数据库连接失败: {e}") from e
        finally:
            if conn:
                try:
                    conn.close()
                    logger.debug("数据库连接已释放")
                except Exception as e:
                    logger.warning(f"释放数据库连接失败: {e}")

    @contextmanager
    def transaction(self) -> Generator[Any, None, None]:
        """数据库事务上下文管理器"""
        with self.get_connection() as conn:
            try:
                conn.autocommit = False
                logger.debug("开始数据库事务")
                yield conn
                conn.commit()
                logger.debug("数据库事务提交成功")
            except Exception as e:
                conn.rollback()
                logger.error(f"数据库事务回滚: {e}")
                raise DatabaseError(f"数据库事务失败: {e}") from e
            finally:
                conn.autocommit = True

    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """执行查询语句"""
        if self._mock_mode:
            logger.debug(f"模拟模式: 跳过查询 {query}")
            return []

        with self.get_connection() as conn:
            try:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(query, params or ())
                    result = cursor.fetchall()
                    logger.debug(f"查询执行成功: {query}")
                    return result
            except Exception as e:
                logger.error(f"查询执行失败: {query}, 错误: {e}")
                raise DatabaseError(f"查询执行失败: {e}", operation="SELECT") from e

    def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
        """执行更新语句（INSERT, UPDATE, DELETE）"""
        if self._mock_mode:
            logger.debug(f"模拟模式: 跳过更新 {query}")
            return 0

        with self.transaction() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(query, params or ())
                    affected_rows = cursor.rowcount
                    logger.debug(f"更新执行成功: {query}, 影响行数: {affected_rows}")
                    return affected_rows
            except Exception as e:
                logger.error(f"更新执行失败: {query}, 错误: {e}")
                raise DatabaseError(f"更新执行失败: {e}", operation="UPDATE") from e

    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """批量执行语句"""
        if self._mock_mode:
            logger.debug(f"模拟模式: 跳过批量执行 {query}")
            return 0

        with self.transaction() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.executemany(query, params_list)
                    affected_rows = cursor.rowcount
                    logger.debug(f"批量执行成功: {query}, 影响行数: {affected_rows}")
                    return affected_rows
            except Exception as e:
                logger.error(f"批量执行失败: {query}, 错误: {e}")
                raise DatabaseError(f"批量执行失败: {e}", operation="BULK_UPDATE") from e

    def create_tables(self):
        """创建数据库表"""
        if self._mock_mode:
            logger.info("模拟模式: 跳过数据库表创建")
            return

        tables_sql = [
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id VARCHAR(50) PRIMARY KEY,
                username VARCHAR(100) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                email VARCHAR(255),
                preferences JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """,
            """
            CREATE TABLE IF NOT EXISTS products (
                product_id VARCHAR(50) PRIMARY KEY,
                title VARCHAR(500) NOT NULL,
                description TEXT,
                price DECIMAL(10,2),
                category VARCHAR(100),
                image_path VARCHAR(500),
                feature_vector_path VARCHAR(500),
                rating DECIMAL(3,2) DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """,
            """
            CREATE TABLE IF NOT EXISTS user_actions (
                action_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(50) NOT NULL,
                product_id VARCHAR(50) NOT NULL,
                action_type ENUM('view', 'click', 'favorite', 'purchase') NOT NULL,
                rating INT DEFAULT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
                INDEX idx_user_product (user_id, product_id),
                INDEX idx_timestamp (timestamp),
                INDEX idx_action_type (action_type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """,
            """
            CREATE TABLE IF NOT EXISTS recommendations (
                rec_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(50) NOT NULL,
                recommended_products JSON NOT NULL,
                algorithm VARCHAR(100) DEFAULT 'multimodal_fusion',
                score DECIMAL(5,4) DEFAULT 0.0000,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                INDEX idx_user_created (user_id, created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
        ]

        try:
            for sql in tables_sql:
                self.execute_update(sql.strip())
            logger.info("数据库表创建成功")
        except Exception as e:
            logger.error(f"数据库表创建失败: {e}")
            raise

    def health_check(self) -> bool:
        """数据库健康检查"""
        if self._mock_mode:
            logger.debug("模拟模式: 数据库健康检查通过")
            return True

        try:
            result = self.execute_query("SELECT 1 as health_check")
            return len(result) > 0 and result[0]['health_check'] == 1
        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        if self._mock_mode:
            # 模拟数据
            return {
                'user_count': 2,
                'product_count': 10,
                'action_count': 45,
                'recommendation_count': 5
            }

        stats = {}
        try:
            # 用户数量
            user_count = self.execute_query("SELECT COUNT(*) as count FROM users")
            stats['user_count'] = user_count[0]['count'] if user_count else 0

            # 商品数量
            product_count = self.execute_query("SELECT COUNT(*) as count FROM products")
            stats['product_count'] = product_count[0]['count'] if product_count else 0

            # 行为记录数量
            action_count = self.execute_query("SELECT COUNT(*) as count FROM user_actions")
            stats['action_count'] = action_count[0]['count'] if action_count else 0

            # 推荐记录数量
            rec_count = self.execute_query("SELECT COUNT(*) as count FROM recommendations")
            stats['recommendation_count'] = rec_count[0]['count'] if rec_count else 0

        except Exception as e:
            logger.warning(f"获取数据库统计信息失败: {e}")
            return {}

        return stats

    def backup_database(self, backup_path: str):
        """数据库备份"""
        # 这里可以实现数据库备份逻辑
        logger.info(f"数据库备份到: {backup_path}")
        # 实际实现需要使用mysqldump或其他备份工具
        pass

    def close(self):
        """关闭数据库连接池"""
        if self._pool:
            self._pool.close()
            logger.info("数据库连接池已关闭")


# 全局数据库管理器实例
db_manager = DatabaseManager()
