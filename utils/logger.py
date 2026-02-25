"""
日志管理系统
提供统一的日志记录功能
"""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Optional

from config.settings import settings


def setup_logging():
    """设置日志系统"""
    try:
        # 创建日志目录
        log_dir = Path(settings.PROJECT_ROOT) / 'logs'
        log_dir.mkdir(exist_ok=True)

        # 配置日志
        logging.config.dictConfig(settings.LOGGING_CONFIG)

        # 获取根日志器
        logger = logging.getLogger('multimodal_recommendation')
        logger.info("日志系统初始化完成")

        return logger
    except Exception as e:
        # 如果配置失败，使用基本配置
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('app.log', encoding='utf-8')
            ]
        )
        logger = logging.getLogger('multimodal_recommendation')
        logger.error(f"日志系统配置失败，使用基本配置: {e}")
        return logger


def get_logger(name: str = 'multimodal_recommendation') -> logging.Logger:
    """获取指定名称的日志器"""
    return logging.getLogger(f'multimodal_recommendation.{name}')


class LoggerMixin:
    """日志混入类，为类提供日志功能"""

    @property
    def logger(self) -> logging.Logger:
        """获取类对应的日志器"""
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger


def log_execution_time(func):
    """装饰器：记录函数执行时间"""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(f"开始执行函数: {func.__name__}")
        import time
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"函数 {func.__name__} 执行完成，耗时: {execution_time:.3f}秒")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"函数 {func.__name__} 执行失败，耗时: {execution_time:.3f}秒，错误: {e}")
            raise

    return wrapper


def log_method_calls(cls):
    """类装饰器：自动记录方法调用"""
    for attr_name in dir(cls):
        attr = getattr(cls, attr_name)
        if callable(attr) and not attr_name.startswith('_'):
            setattr(cls, attr_name, log_execution_time(attr))
    return cls


# 全局日志器实例
logger = setup_logging()
