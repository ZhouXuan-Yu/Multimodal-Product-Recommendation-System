#!/usr/bin/env python3
"""
训练管理器（training 包）
负责管理训练过程，协调各个模块
"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.logger import get_logger

logger = get_logger(__name__)

class TrainManager:
    """训练管理器"""

    def __init__(self):
        self.coordinator = None

    def initialize_coordinator(self):
        """初始化训练协调器"""
        from training.training_coordinator import get_coordinator
        self.coordinator = get_coordinator()
        logger.info("训练协调器已初始化")

    def run_feature_extraction(self):
        """运行特征提取"""
        logger.info("开始特征提取...")

        try:
            from training.train_model import MultimodalFeatureExtractor

            # 创建特征提取器，传入协调器
            extractor = MultimodalFeatureExtractor(coordinator=self.coordinator)

            if extractor.load_data():
                extractor.extract_all_features()
                logger.info("特征提取完成")
                return True
            else:
                logger.error("特征提取失败：无法加载数据")
                return False

        except Exception as e:
            logger.error(f"特征提取异常: {e}")
            return False

    def run_model_training(self):
        """运行模型训练"""
        logger.info("开始模型训练...")

        try:
            from training.train_model import RecommendationTrainer

            # 创建训练器
            trainer = RecommendationTrainer()

            if trainer.load_features_and_data():
                trainer.train_all_models()
                logger.info("模型训练完成")
                return True
            else:
                logger.error("模型训练失败：无法加载特征数据")
                return False

        except Exception as e:
            logger.error(f"模型训练异常: {e}")
            return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="训练管理器")
    parser.add_argument("--mode", choices=["extract", "train", "all"],
                       default="all", help="训练模式")
    parser.add_argument("--coordinator", action="store_true",
                       help="使用训练协调器")

    args = parser.parse_args()

    manager = TrainManager()

    if args.coordinator:
        manager.initialize_coordinator()

    success = True

    if args.mode in ["extract", "all"]:
        if not manager.run_feature_extraction():
            success = False

    if args.mode in ["train", "all"]:
        if not manager.run_model_training():
            success = False

    if success:
        logger.info("训练管理器执行完成")
        return 0
    else:
        logger.error("训练管理器执行失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())


