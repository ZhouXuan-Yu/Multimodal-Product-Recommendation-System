"""
系统配置文件
包含所有配置项的集中管理
"""

import os
from pathlib import Path
from typing import Dict, Any


class Settings:
    """系统配置类"""

    def __init__(self):
        # 项目根目录
        self.PROJECT_ROOT = Path(__file__).parent.parent

        # 环境配置
        self.ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
        self.DEBUG = self.ENVIRONMENT == 'development'

        # 数据库配置
        self.DATABASE_CONFIG = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', '3306')),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'multimodal_recommendation'),
            'charset': 'utf8mb4',
            'autocommit': True,
            'pool_size': 5,
            'connect_timeout': 10
        }

        # Redis配置（可选，用于缓存）
        self.REDIS_CONFIG = {
            'host': os.getenv('REDIS_HOST', 'localhost'),
            'port': int(os.getenv('REDIS_PORT', '6379')),
            'db': int(os.getenv('REDIS_DB', '0')),
            'password': os.getenv('REDIS_PASSWORD', ''),
            'socket_timeout': 5,
            'socket_connect_timeout': 5
        }

        # PyTorch配置
        self.PYTORCH_CONFIG = {
            'device': 'cuda' if os.getenv('USE_CUDA', 'false').lower() == 'true' else 'cpu',
            'num_workers': int(os.getenv('NUM_WORKERS', '4')),
            'batch_size': int(os.getenv('BATCH_SIZE', '32')),
            'max_seq_length': int(os.getenv('MAX_SEQ_LENGTH', '128'))
        }

        # 模型路径配置
        self.MODEL_PATHS = {
            'bert_model': os.path.join(self.PROJECT_ROOT, 'models', 'bert'),
            'resnet_model': os.path.join(self.PROJECT_ROOT, 'models', 'resnet'),
            'fusion_model': os.path.join(self.PROJECT_ROOT, 'models', 'fusion'),
            'embeddings': os.path.join(self.PROJECT_ROOT, 'data', 'embeddings')
        }

        # 界面配置
        self.UI_CONFIG = {
            'window_title': '多模态商品推荐系统',
            'window_size': (1400, 900),
            'theme': 'light',
            'language': 'zh_CN',
            'font_family': 'Microsoft YaHei',
            'font_size': 12
        }

        # 日志配置
        self.LOGGING_CONFIG = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'detailed': {
                    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                },
                'simple': {
                    'format': '%(levelname)s - %(message)s'
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': 'INFO',
                    'formatter': 'simple',
                    'stream': 'ext://sys.stdout'
                }
            },
            'root': {
                'level': 'DEBUG' if self.DEBUG else 'INFO',
                # 仅输出到控制台，便于在终端直接查看日志
                'handlers': ['console']
            },
            'loggers': {
                'multimodal_recommendation': {
                    'level': 'DEBUG' if self.DEBUG else 'INFO',
                    # 同样只绑定到控制台 handler
                    'handlers': ['console'],
                    'propagate': False
                }
            }
        }

        # API配置
        self.API_CONFIG = {
            'host': os.getenv('API_HOST', '0.0.0.0'),
            'port': int(os.getenv('API_PORT', '8000')),
            'workers': int(os.getenv('API_WORKERS', '4')),
            'reload': self.DEBUG
        }

        # 缓存配置
        self.CACHE_CONFIG = {
            'enabled': os.getenv('CACHE_ENABLED', 'true').lower() == 'true',
            'ttl': int(os.getenv('CACHE_TTL', '3600')),  # 1小时
            'max_size': int(os.getenv('CACHE_MAX_SIZE', '1000'))
        }

        # 推荐算法配置
        self.RECOMMENDATION_CONFIG = {
            'top_k': int(os.getenv('TOP_K', '10')),
            'similarity_threshold': float(os.getenv('SIMILARITY_THRESHOLD', '0.1')),
            'cold_start_strategy': os.getenv('COLD_START_STRATEGY', 'popular'),
            'diversity_weight': float(os.getenv('DIVERSITY_WEIGHT', '0.3')),
            'novelty_weight': float(os.getenv('NOVELTY_WEIGHT', '0.2'))
        }

    def get_database_url(self) -> str:
        """获取数据库连接URL"""
        config = self.DATABASE_CONFIG
        return f"mysql+pymysql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"

    def get_redis_url(self) -> str:
        """获取Redis连接URL"""
        config = self.REDIS_CONFIG
        password_part = f":{config['password']}@" if config['password'] else ""
        return f"redis://password_part{config['host']}:{config['port']}/{config['db']}"

    def ensure_directories(self):
        """确保必要的目录存在"""
        directories = [
            self.PROJECT_ROOT / 'logs',
            self.PROJECT_ROOT / 'data' / 'embeddings',
            self.PROJECT_ROOT / 'models' / 'bert',
            self.PROJECT_ROOT / 'models' / 'resnet',
            self.PROJECT_ROOT / 'models' / 'fusion',
            self.PROJECT_ROOT / 'data' / 'images'
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def validate_config(self) -> bool:
        """验证配置是否有效"""
        try:
            # 检查数据库配置
            required_db_keys = ['host', 'port', 'user', 'database']
            for key in required_db_keys:
                if not self.DATABASE_CONFIG.get(key):
                    raise ValueError(f"数据库配置缺少: {key}")

            # 检查模型路径
            for path_name, path in self.MODEL_PATHS.items():
                if not path:
                    raise ValueError(f"模型路径配置无效: {path_name}")

            return True
        except Exception as e:
            print(f"配置验证失败: {e}")
            return False


# 全局配置实例
settings = Settings()

# 初始化
settings.ensure_directories()

if not settings.validate_config():
    raise RuntimeError("配置验证失败，请检查配置文件")

