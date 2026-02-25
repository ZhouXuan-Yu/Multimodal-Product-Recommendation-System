#!/usr/bin/env python3
"""
模型训练脚本（training 包）
实现多模态特征提取和推荐模型训练
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path
import argparse
from tqdm import tqdm
import pickle
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.logger import get_logger

# GPU监控工具
try:
    import GPUtil
    GPU_MONITORING_AVAILABLE = True
except ImportError:
    GPU_MONITORING_AVAILABLE = False

logger = get_logger(__name__)

class MultimodalFeatureExtractor:
    """多模态特征提取器"""

    def __init__(self, data_dir="data", model_dir="models", coordinator=None):
        self.data_dir = Path(data_dir)
        self.model_dir = Path(model_dir)
        self.processed_data_dir = self.data_dir / "processed"
        self.embeddings_dir = self.data_dir / "embeddings"
        self.coordinator = coordinator  # 训练协调器

        # 确保目录存在
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)

        # GPU监控
        self.gpu_stats = []

        # 尝试导入深度学习库
        self.torch_available = self._check_torch_availability()

    def monitor_gpu(self):
        """监控GPU使用情况"""
        if not GPU_MONITORING_AVAILABLE:
            return None

        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]  # 使用第一个GPU
                stats = {
                    'gpu_id': gpu.id,
                    'gpu_name': gpu.name,
                    'gpu_load': gpu.load * 100,
                    'gpu_memory_used': gpu.memoryUsed,
                    'gpu_memory_total': gpu.memoryTotal,
                    'gpu_memory_free': gpu.memoryFree,
                    'gpu_temperature': gpu.temperature
                }
                self.gpu_stats.append(stats)

                # 向协调器发送GPU统计数据
                if self.coordinator:
                    try:
                        self.coordinator._send_gpu_stats(stats)
                    except Exception:
                        pass

                return stats
        except Exception as e:
            logger.warning(f"GPU监控失败: {e}")

        return None

    def _check_torch_availability(self):
        """检查PyTorch和GPU是否可用"""
        try:
            import torch
            import torchvision
            from torchvision import models

            # 检查CUDA可用性
            if torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                current_device = torch.cuda.current_device()
                device_name = torch.cuda.get_device_name(current_device)
                logger.info(f"GPU可用: {gpu_count}个GPU，当前使用: {device_name}")
                logger.info("将使用GPU进行深度学习特征提取")

                # 设置默认设备为GPU
                torch.cuda.set_device(current_device)
                return True
            else:
                logger.warning("CUDA不可用，将尝试使用CPU")
                logger.info("请安装CUDA版本的PyTorch: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
                return False

        except ImportError as e:
            logger.error(f"PyTorch不可用: {e}")
            logger.info("请安装PyTorch: pip install torch torchvision torchaudio")
            logger.info("将使用简化特征提取方法")
            return False

    def load_data(self):
        """加载预处理后的数据"""
        logger.info("加载数据集...")

        try:
            # 加载商品数据
            products_file = self.processed_data_dir / "products.json"
            with open(products_file, 'r', encoding='utf-8') as f:
                self.products = json.load(f)

            # 加载用户数据
            users_file = self.processed_data_dir / "users.json"
            with open(users_file, 'r', encoding='utf-8') as f:
                self.users = json.load(f)

            # 加载交互数据
            interactions_file = self.processed_data_dir / "interactions.json"
            with open(interactions_file, 'r', encoding='utf-8') as f:
                self.interactions = json.load(f)

            logger.info(f"加载完成: {len(self.products)} 商品, {len(self.users)} 用户, {len(self.interactions)} 交互")

        except FileNotFoundError as e:
            logger.error(f"数据文件不存在: {e}")
            logger.info("请先运行 python training.download_dataset --dataset all")
            return False

        return True

    def extract_text_features(self):
        """提取文本特征"""
        logger.info("开始文本特征提取...")

        if not self.torch_available:
            # 使用简化的TF-IDF特征
            return self._extract_text_features_simple()

        try:
            from transformers import AutoTokenizer, AutoModel
            import torch

            # 加载预训练模型 (使用较小的模型以节省资源)
            model_name = "bert-base-uncased"
            logger.info(f"加载预训练模型: {model_name}")

            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModel.from_pretrained(model_name)
            model.eval()

            # 强制使用GPU，如果不可用则报错
            if not torch.cuda.is_available():
                raise RuntimeError("GPU不可用，无法进行深度学习特征提取。请安装CUDA版本的PyTorch")
            device = torch.device('cuda')
            model.to(device)
            logger.info(f"使用GPU设备: {torch.cuda.get_device_name(device)}")

            text_features = {}

            for product in tqdm(self.products, desc="提取文本特征"):
                text = product.get('description', '') + ' ' + product.get('title', '')
                if not text.strip():
                    text = product.get('title', 'unknown product')

                # 分词
                inputs = tokenizer(text, return_tensors='pt', truncation=True,
                                 max_length=128, padding=True)
                inputs = {k: v.to(device) for k, v in inputs.items()}

                # 提取特征
                with torch.no_grad():
                    outputs = model(**inputs)
                    # 使用[CLS]标记的输出作为句子特征
                    features = outputs.last_hidden_state[:, 0, :].cpu().numpy().flatten()

                text_features[product['product_id']] = features

                # GPU监控
                gpu_info = self.monitor_gpu()
                if gpu_info and len(self.gpu_stats) % 10 == 0:  # 每10个样本记录一次
                    logger.info(f"显存: {gpu_info['gpu_memory_used']}/{gpu_info['gpu_memory_total']}MB")

            # 保存特征
            features_file = self.embeddings_dir / "text_features.pkl"
            with open(features_file, 'wb') as f:
                pickle.dump(text_features, f)

            logger.info(f"文本特征提取完成，保存到: {features_file}")
            return text_features

        except Exception as e:
            logger.error(f"文本特征提取失败: {e}")
            return self._extract_text_features_simple()

    def _extract_text_features_simple(self):
        """简化的文本特征提取"""
        logger.info("使用简化的文本特征提取方法...")

        from sklearn.feature_extraction.text import TfidfVectorizer

        # 准备文本数据
        texts = []
        product_ids = []

        for product in self.products:
            text = product.get('description', '') + ' ' + product.get('title', '')
            if not text.strip():
                text = product.get('title', 'unknown product')

            texts.append(text)
            product_ids.append(product['product_id'])

        # TF-IDF向量化
        vectorizer = TfidfVectorizer(max_features=300, stop_words='english')
        features_matrix = vectorizer.fit_transform(texts)

        # 转换为字典格式
        text_features = {}
        for i, product_id in enumerate(product_ids):
            text_features[product_id] = features_matrix[i].toarray().flatten()

        # 保存特征
        features_file = self.embeddings_dir / "text_features_simple.pkl"
        with open(features_file, 'wb') as f:
            pickle.dump({
                'features': text_features,
                'vectorizer': vectorizer
            }, f)

        logger.info(f"简化文本特征提取完成，保存到: {features_file}")
        return text_features

    def extract_image_features(self):
        """提取图像特征"""
        logger.info("开始图像特征提取...")

        if not self.torch_available:
            # 使用简化的图像特征
            return self._extract_image_features_simple()

        try:
            import torch
            import torchvision.transforms as transforms
            from torchvision import models
            from PIL import Image

            # 加载预训练的ResNet模型
            logger.info("加载预训练ResNet模型...")
            model = models.resnet50(pretrained=True)
            model.eval()

            # 移除分类器，只保留特征提取部分
            model = torch.nn.Sequential(*list(model.children())[:-1])

            # 强制使用GPU，如果不可用则报错
            if not torch.cuda.is_available():
                raise RuntimeError("GPU不可用，无法进行深度学习特征提取。请安装CUDA版本的PyTorch")
            device = torch.device('cuda')
            model.to(device)
            logger.info(f"使用GPU设备: {torch.cuda.get_device_name(device)}")

            # 图像预处理
            preprocess = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                   std=[0.229, 0.224, 0.225]),
            ])

            image_features = {}

            for product in tqdm(self.products, desc="提取图像特征"):
                image_path = self.data_dir / "images" / product.get('image_path', '')

                if not image_path.exists():
                    # 如果图像不存在，使用随机特征
                    features = np.random.randn(2048)
                else:
                    try:
                        # 加载和预处理图像
                        image = Image.open(image_path).convert('RGB')
                        input_tensor = preprocess(image)
                        input_batch = input_tensor.unsqueeze(0).to(device)

                        # 提取特征
                        with torch.no_grad():
                            features = model(input_batch).cpu().numpy().flatten()

                    except Exception as e:
                        logger.warning(f"处理图像失败 {image_path}: {e}")
                        features = np.random.randn(2048)

                image_features[product['product_id']] = features

                # GPU监控
                gpu_info = self.monitor_gpu()
                if gpu_info and len(self.gpu_stats) % 5 == 0:  # 每5个样本记录一次
                    logger.info(f"显存: {gpu_info['gpu_memory_used']}/{gpu_info['gpu_memory_total']}MB")

            # 保存特征
            features_file = self.embeddings_dir / "image_features.pkl"
            with open(features_file, 'wb') as f:
                pickle.dump(image_features, f)

            logger.info(f"图像特征提取完成，保存到: {features_file}")
            return image_features

        except Exception as e:
            logger.error(f"图像特征提取失败: {e}")
            return self._extract_image_features_simple()

    def _extract_image_features_simple(self):
        """简化的图像特征提取"""
        logger.info("使用简化的图像特征提取方法...")

        # 简单的图像特征：基于文件名哈希或其他简单特征
        image_features = {}

        for product in self.products:
            # 使用简单的哈希作为特征
            product_id = product['product_id']
            # 创建简单的特征向量 (可以后续扩展)
            features = np.random.randn(128)  # 128维随机特征

            # 可以根据商品类别添加一些简单特征
            category = product.get('category', 'unknown')
            if '电子' in category or '电脑' in category:
                features[0] = 1.0  # 电子产品标记
            elif '服装' in category or '鞋' in category:
                features[1] = 1.0  # 服装标记
            elif '家居' in category:
                features[2] = 1.0  # 家居标记

            image_features[product_id] = features

        # 保存特征
        features_file = self.embeddings_dir / "image_features_simple.pkl"
        with open(features_file, 'wb') as f:
            pickle.dump(image_features, f)

        logger.info(f"简化图像特征提取完成，保存到: {features_file}")
        return image_features

    def fuse_features(self, text_features, image_features, method="concat"):
        """融合多模态特征"""
        logger.info(f"开始特征融合 (方法: {method})...")

        fused_features = {}

        for product_id in text_features.keys():
            text_feat = text_features[product_id]
            image_feat = image_features.get(product_id, np.zeros_like(text_feat))

            if method == "concat":
                # 拼接融合
                fused = np.concatenate([text_feat, image_feat])
            elif method == "average":
                # 平均融合 (需要特征维度相同)
                min_len = min(len(text_feat), len(image_feat))
                text_feat = text_feat[:min_len]
                image_feat = image_feat[:min_len]
                fused = (text_feat + image_feat) / 2
            else:
                fused = text_feat  # 默认使用文本特征

            fused_features[product_id] = fused

        # 保存融合特征
        features_file = self.embeddings_dir / f"fused_features_{method}.pkl"
        with open(features_file, 'wb') as f:
            pickle.dump(fused_features, f)

        logger.info(f"特征融合完成，保存到: {features_file}")
        return fused_features

    def extract_all_features(self):
        """提取所有特征"""
        logger.info("开始多模态特征提取流程...")

        # 提取文本特征
        text_features = self.extract_text_features()

        # 提取图像特征
        image_features = self.extract_image_features()

        # 特征融合
        fused_features = self.fuse_features(text_features, image_features, method="concat")

        logger.info("多模态特征提取完成！")
        return fused_features

class RecommendationTrainer:
    """推荐模型训练器"""

    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.embeddings_dir = self.data_dir / "embeddings"
        self.models_dir = Path("models")

        self.models_dir.mkdir(parents=True, exist_ok=True)

    def load_features_and_data(self):
        """加载特征和数据"""
        logger.info("加载特征和数据...")

        # 加载融合特征
        features_file = self.embeddings_dir / "fused_features_concat.pkl"
        if not features_file.exists():
            logger.error(f"特征文件不存在: {features_file}")
            return None, None, None

        with open(features_file, 'rb') as f:
            self.product_features = pickle.load(f)

        # 加载商品和用户数据
        processed_dir = self.data_dir / "processed"

        with open(processed_dir / "products.json", 'r', encoding='utf-8') as f:
            self.products = json.load(f)

        with open(processed_dir / "users.json", 'r', encoding='utf-8') as f:
            self.users = json.load(f)

        with open(processed_dir / "interactions.json", 'r', encoding='utf-8') as f:
            self.interactions = json.load(f)

        logger.info(f"数据加载完成: {len(self.product_features)} 商品特征")
        return self.product_features, self.products, self.users

    def build_user_profiles(self):
        """构建用户画像"""
        logger.info("构建用户画像...")

        user_profiles = {}

        for user in self.users:
            user_id = user['user_id']
            preferences = user.get('preferences', [])

            # 基于用户偏好创建简单画像
            profile = np.zeros(300)  # 假设文本特征维度

            # 根据偏好设置特征
            for pref in preferences:
                if '电子' in pref:
                    profile[:50] = 1.0
                elif '时尚' in pref or '服装' in pref:
                    profile[50:100] = 1.0
                elif '运动' in pref:
                    profile[100:150] = 1.0

            user_profiles[user_id] = profile

        # 保存用户画像
        profiles_file = self.embeddings_dir / "user_profiles.pkl"
        with open(profiles_file, 'wb') as f:
            pickle.dump(user_profiles, f)

        logger.info(f"用户画像构建完成，保存到: {profiles_file}")
        return user_profiles

    def train_collaborative_filtering(self):
        """训练协同过滤模型"""
        logger.info("训练协同过滤模型...")

        # 创建用户-商品评分矩阵
        user_ids = list(set([inter['user_id'] for inter in self.interactions]))
        product_ids = list(set([inter['product_id'] for inter in self.interactions]))

        user_id_map = {uid: i for i, uid in enumerate(user_ids)}
        product_id_map = {pid: i for i, pid in enumerate(product_ids)}

        # 构建评分矩阵
        ratings_matrix = np.zeros((len(user_ids), len(product_ids)))

        for inter in self.interactions:
            user_idx = user_id_map[inter['user_id']]
            product_idx = product_id_map[inter['product_id']]
            rating = inter.get('rating', 3.0)  # 默认评分为3
            ratings_matrix[user_idx, product_idx] = rating

        # 简单的基于用户的协同过滤
        # 计算用户相似度
        user_similarity = cosine_similarity(ratings_matrix)

        # 保存模型
        model_data = {
            'user_similarity': user_similarity,
            'user_ids': user_ids,
            'product_ids': product_ids,
            'user_id_map': user_id_map,
            'product_id_map': product_id_map,
            'ratings_matrix': ratings_matrix
        }

        model_file = self.models_dir / "collaborative_filtering.pkl"
        with open(model_file, 'wb') as f:
            pickle.dump(model_data, f)

        logger.info(f"协同过滤模型训练完成，保存到: {model_file}")
        return model_data
    def train_content_based_model(self):
        """训练基于内容的推荐模型"""
        logger.info("训练基于内容的推荐模型...")

        # 标准化商品特征
        product_ids = list(self.product_features.keys())
        features_matrix = np.array([self.product_features[pid] for pid in product_ids])

        scaler = StandardScaler()
        normalized_features = scaler.fit_transform(features_matrix)

        # 保存标准化后的特征
        normalized_features_dict = {
            pid: normalized_features[i] for i, pid in enumerate(product_ids)
        }

        model_data = {
            'product_features': normalized_features_dict,
            'scaler': scaler,
            'product_ids': product_ids
        }

        model_file = self.models_dir / "content_based.pkl"
        with open(model_file, 'wb') as f:
            pickle.dump(model_data, f)

        logger.info(f"基于内容推荐模型训练完成，保存到: {model_file}")

        # 保存训练指标
        self.save_training_metrics()

        return model_data

    def save_training_metrics(self):
        """保存训练指标"""
        logger.info("保存训练指标...")

        try:
            metrics_file = self.data_dir / "embeddings" / "model_metrics.json"

            # 计算各种指标
            metrics = {
                "training_timestamp": str(pd.Timestamp.now()),
                "gpu_stats_count": len(self.gpu_stats),
                "feature_extraction": {
                    "text_features_count": len(self.product_features) if hasattr(self, 'product_features') else 0,
                    "gpu_peak_usage": max([s.get('gpu_load', 0) for s in self.gpu_stats]) if self.gpu_stats else 0,
                    "gpu_avg_temperature": sum([s.get('gpu_temperature', 0) for s in self.gpu_stats]) / len(self.gpu_stats) if self.gpu_stats else 0
                },
                "models": {
                    "collaborative_filtering": {
                        "status": "trained",
                        "users_count": len(self.user_profiles) if hasattr(self, 'user_profiles') else 0,
                        "items_count": len(self.product_features) if hasattr(self, 'product_features') else 0
                    },
                    "content_based": {
                        "status": "trained",
                        "features_dimension": len(next(iter(self.product_features.values()))) if self.product_features else 0,
                        "products_count": len(self.product_features) if hasattr(self, 'product_features') else 0
                    }
                }
            }

            with open(metrics_file, 'w', encoding='utf-8') as f:
                json.dump(metrics, f, indent=2, ensure_ascii=False)

            logger.info(f"训练指标已保存到: {metrics_file}")

        except Exception as e:
            logger.error(f"保存训练指标失败: {e}")

    def train_all_models(self):
        """训练所有模型"""
        logger.info("开始训练所有推荐模型...")

        # 加载数据
        features, products, users = self.load_features_and_data()
        if features is None:
            return False

        # 构建用户画像
        user_profiles = self.build_user_profiles()

        # 训练协同过滤模型
        cf_model = self.train_collaborative_filtering()

        # 训练基于内容推荐模型
        cb_model = self.train_content_based_model()

        logger.info("所有模型训练完成！")
        return True

