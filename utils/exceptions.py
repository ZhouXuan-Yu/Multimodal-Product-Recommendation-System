"""
异常处理模块
定义系统异常类和异常处理机制
"""

from typing import Optional, Dict, Any
from utils.logger import get_logger

logger = get_logger(__name__)


class MultimodalRecommendationError(Exception):
    """系统基础异常类"""

    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.details = details or {}

    def __str__(self):
        return f"[{self.error_code}] {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }


class DatabaseError(MultimodalRecommendationError):
    """数据库相关异常"""
    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        super().__init__(message, "DATABASE_ERROR", {"operation": operation, **kwargs})


class ModelError(MultimodalRecommendationError):
    """模型相关异常"""
    def __init__(self, message: str, model_name: Optional[str] = None, **kwargs):
        super().__init__(message, "MODEL_ERROR", {"model_name": model_name, **kwargs})


class ValidationError(MultimodalRecommendationError):
    """数据验证异常"""
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None, **kwargs):
        super().__init__(message, "VALIDATION_ERROR", {
            "field": field,
            "value": str(value) if value is not None else None,
            **kwargs
        })


class ConfigurationError(MultimodalRecommendationError):
    """配置相关异常"""
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        super().__init__(message, "CONFIGURATION_ERROR", {"config_key": config_key, **kwargs})


class FileOperationError(MultimodalRecommendationError):
    """文件操作异常"""
    def __init__(self, message: str, file_path: Optional[str] = None, operation: Optional[str] = None, **kwargs):
        super().__init__(message, "FILE_OPERATION_ERROR", {
            "file_path": file_path,
            "operation": operation,
            **kwargs
        })


class NetworkError(MultimodalRecommendationError):
    """网络相关异常"""
    def __init__(self, message: str, url: Optional[str] = None, status_code: Optional[int] = None, **kwargs):
        super().__init__(message, "NETWORK_ERROR", {
            "url": url,
            "status_code": status_code,
            **kwargs
        })


class AuthenticationError(MultimodalRecommendationError):
    """认证相关异常"""
    def __init__(self, message: str, user_id: Optional[str] = None, **kwargs):
        super().__init__(message, "AUTHENTICATION_ERROR", {"user_id": user_id, **kwargs})


class AuthorizationError(MultimodalRecommendationError):
    """授权相关异常"""
    def __init__(self, message: str, user_id: Optional[str] = None, resource: Optional[str] = None, **kwargs):
        super().__init__(message, "AUTHORIZATION_ERROR", {
            "user_id": user_id,
            "resource": resource,
            **kwargs
        })


def handle_exception(func):
    """异常处理装饰器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except MultimodalRecommendationError:
            # 重新抛出自定义异常
            raise
        except Exception as e:
            # 将未知异常转换为系统异常
            logger.error(f"未处理的异常: {type(e).__name__}: {e}", exc_info=True)
            raise MultimodalRecommendationError(
                f"系统内部错误: {type(e).__name__}",
                "INTERNAL_ERROR",
                {"original_error": str(e)}
            ) from e

    return wrapper


def safe_execute(func, default_value=None, log_error: bool = True):
    """安全执行函数，返回默认值而非抛出异常"""
    try:
        return func()
    except Exception as e:
        if log_error:
            logger.warning(f"安全执行失败: {type(e).__name__}: {e}")
        return default_value


class ErrorHandler:
    """错误处理器"""

    @staticmethod
    def log_error(error: Exception, context: Optional[Dict[str, Any]] = None):
        """记录错误信息"""
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {}
        }

        if isinstance(error, MultimodalRecommendationError):
            logger.error(f"业务异常: {error}", extra=error_info)
        else:
            logger.error(f"系统异常: {error}", extra=error_info, exc_info=True)

    @staticmethod
    def create_error_response(error: Exception) -> Dict[str, Any]:
        """创建错误响应"""
        if isinstance(error, MultimodalRecommendationError):
            return {
                "success": False,
                "error": error.to_dict()
            }
        else:
            return {
                "success": False,
                "error": {
                    "error_code": "INTERNAL_ERROR",
                    "message": "系统内部错误",
                    "details": {"original_error": str(error)}
                }
            }

    @staticmethod
    def should_retry(error: Exception, retry_count: int, max_retries: int) -> bool:
        """判断是否应该重试"""
        if retry_count >= max_retries:
            return False

        # 网络错误可以重试
        if isinstance(error, NetworkError):
            return True

        # 数据库连接错误可以重试
        if isinstance(error, DatabaseError):
            error_msg = str(error).lower()
            if 'connection' in error_msg or 'timeout' in error_msg:
                return True

        return False

