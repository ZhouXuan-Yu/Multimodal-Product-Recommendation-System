#!/usr/bin/env python3
"""
多模态推荐系统训练流水线（training 包）
完整的数据下载、预处理、特征提取和模型训练流程
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
import time

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.logger import get_logger

logger = get_logger(__name__)

class TrainingPipeline:
    """训练流水线"""

    def __init__(self, coordinator=None):
        self.project_root = Path(__file__).parent.parent
        self.scripts_dir = self.project_root / "scripts"
        self.coordinator = coordinator  # 训练协调器

    def run_command(self, command, description=""):
        """运行命令并返回结果"""
        logger.info(f"执行: {description or command}")

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )

            if result.returncode == 0:
                logger.info("✓ 执行成功")
                return True, result.stdout
            else:
                logger.error(f"✗ 执行失败: {result.stderr}")
                return False, result.stderr

        except subprocess.TimeoutExpired:
            logger.error("✗ 执行超时")
            return False, "命令执行超时"
        except Exception as e:
            logger.error(f"✗ 执行异常: {e}")
            return False, str(e)

    def check_environment(self):
        """检查训练环境"""
        logger.info("检查训练环境...")

        # map package names to importable module names
        required_packages = {
            'numpy': 'numpy',
            'pandas': 'pandas',
            'scikit-learn': 'sklearn',
            'pillow': 'PIL',
            'matplotlib': 'matplotlib',
            'tqdm': 'tqdm',
            'requests': 'requests'
        }

        missing_packages = []
        for pkg_name, import_name in required_packages.items():
            try:
                __import__(import_name)
                logger.info(f"{pkg_name} installed")
            except ImportError:
                missing_packages.append(pkg_name)
                logger.warning(f"{pkg_name} not installed")

        if missing_packages:
            logger.error(f"缺少必要的包: {', '.join(missing_packages)}")
            logger.info("请运行: pip install -r requirements.txt")
            return False

        # 检查可选包
        optional_packages = ['torch', 'transformers', 'torchvision']
        for package in optional_packages:
            try:
                __import__(package)
                logger.info(f"{package} (optional) installed")
            except ImportError:
                logger.warning(f"{package} not installed (optional) - will use simplified methods")

        return True

    def download_dataset(self):
        """下载数据集"""
        logger.info("=" * 60)
        logger.info("步骤1: 下载数据集")
        logger.info("=" * 60)

        if self.coordinator:
            self.coordinator._update_status("下载数据集", 0.1)

        # 使用 training 包的下载器
        try:
            from training.download_dataset import DatasetDownloader
            downloader = DatasetDownloader()
            success = downloader.download_all()
        except Exception as e:
            logger.error(f"调用数据下载失败: {e}")
            success = False

        if success:
            logger.info("数据集下载完成")
            if self.coordinator:
                self.coordinator._update_status("数据集下载完成", 0.3)
            return True
        else:
            logger.error("数据集下载失败")
            if self.coordinator:
                self.coordinator._update_status("数据集下载失败", -1.0)
            return False

    def extract_features(self):
        """特征提取"""
        logger.info("=" * 60)
        logger.info("步骤2: 多模态特征提取")
        logger.info("=" * 60)

        if self.coordinator:
            self.coordinator._update_status("多模态特征提取", 0.4)

        # 使用训练管理器进行特征提取
        try:
            from training.train_manager import TrainManager
            manager = TrainManager()
            if self.coordinator:
                manager.initialize_coordinator()
            success = manager.run_feature_extraction()
        except Exception as e:
            logger.error(f"特征提取模块调用失败: {e}")
            success = False

        if success:
            logger.info("特征提取完成")
            if self.coordinator:
                self.coordinator._update_status("特征提取完成", 0.7)
            return True
        else:
            logger.error("特征提取失败")
            if self.coordinator:
                self.coordinator._update_status("特征提取失败", -1.0)
            return False

    def train_models(self):
        """训练模型"""
        logger.info("=" * 60)
        logger.info("步骤3: 训练推荐模型")
        logger.info("=" * 60)

        if self.coordinator:
            self.coordinator._update_status("训练推荐模型", 0.8)

        try:
            from training.train_manager import TrainManager
            manager = TrainManager()
            if self.coordinator:
                manager.initialize_coordinator()
            success = manager.run_model_training()
        except Exception as e:
            logger.error(f"训练模块调用失败: {e}")
            success = False

        if success:
            logger.info("模型训练完成")
            if self.coordinator:
                self.coordinator._update_status("训练完成", 1.0)
            return True
        else:
            logger.error("模型训练失败")
            if self.coordinator:
                self.coordinator._update_status("训练失败", -1.0)
            return False

    def initialize_database(self):
        """初始化数据库"""
        logger.info("=" * 60)
        logger.info("步骤4: 初始化数据库")
        logger.info("=" * 60)

        command = "python scripts/init_database.py"
        success, output = self.run_command(command, "初始化数据库")

        if success:
            logger.info("数据库初始化完成")
        else:
            logger.warning("数据库初始化失败，将使用模拟数据")

        return True  # 数据库失败不影响训练流程

    def run_full_pipeline(self):
        """运行完整流水线"""
        logger.info("Start training pipeline")
        logger.info("=" * 60)

        start_time = time.time()

        # 检查环境
        if not self.check_environment():
            logger.error("环境检查失败，请安装必要的依赖")
            return False

        # 执行流水线步骤
        steps = [
            ("下载数据集", self.download_dataset),
            ("特征提取", self.extract_features),
            ("训练模型", self.train_models),
            ("初始化数据库", self.initialize_database)
        ]

        success_count = 0
        for step_name, step_func in steps:
            try:
                if step_func():
                    success_count += 1
                    logger.info(f"{step_name} succeeded")
                else:
                    logger.error(f"{step_name} failed")
            except Exception as e:
                logger.error(f"❌ {step_name} 异常: {e}")

        # 总结
        end_time = time.time()
        duration = end_time - start_time

        logger.info("=" * 60)
        logger.info("流水线执行完成")
        logger.info(f"执行时长: {duration:.2f}s")
        logger.info(f"成功步骤: {success_count}/{len(steps)}")

        if success_count == len(steps):
            logger.info("All steps succeeded")
            logger.info("")
            logger.info("Next steps:")
            logger.info("1. Run python run.py to start the full system")
            logger.info("2. Check data/embeddings/ for feature files")
            logger.info("3. Check models/ for trained models")
            return True
        else:
            logger.warning(f"{len(steps) - success_count} steps failed")
            logger.info("请检查日志文件 logs/app.log 获取详细信息")
            return False

    def show_status(self):
        """显示当前状态"""
        logger.info("检查项目状态...")

        # 检查数据目录
        data_dir = self.project_root / "data"
        if data_dir.exists():
            processed_dir = data_dir / "processed"
            embeddings_dir = data_dir / "embeddings"

            products_file = processed_dir / "products.json"
            features_file = embeddings_dir / "fused_features_concat.pkl"

            if products_file.exists():
                logger.info("✓ 数据集已下载")
            else:
                logger.info("✗ 数据集未下载")

            if features_file.exists():
                logger.info("✓ 特征已提取")
            else:
                logger.info("✗ 特征未提取")
        else:
            logger.info("✗ 数据目录不存在")

        # 检查模型目录
        models_dir = self.project_root / "models"
        if models_dir.exists():
            cf_model = models_dir / "collaborative_filtering.pkl"
            cb_model = models_dir / "content_based.pkl"

            if cf_model.exists():
                logger.info("✓ 协同过滤模型已训练")
            else:
                logger.info("✗ 协同过滤模型未训练")

            if cb_model.exists():
                logger.info("✓ 基于内容模型已训练")
            else:
                logger.info("✗ 基于内容模型未训练")
        else:
            logger.info("✗ 模型目录不存在")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="多模态推荐系统训练流水线")
    parser.add_argument("action", choices=["run", "status", "download", "extract", "train"],
                       help="执行操作")
    parser.add_argument("--skip-db", action="store_true",
                       help="跳过数据库初始化")

    args = parser.parse_args()

    pipeline = TrainingPipeline()

    if args.action == "run":
        success = pipeline.run_full_pipeline()
        sys.exit(0 if success else 1)

    elif args.action == "status":
        pipeline.show_status()

    elif args.action == "download":
        success = pipeline.download_dataset()
        sys.exit(0 if success else 1)

    elif args.action == "extract":
        success = pipeline.extract_features()
        sys.exit(0 if success else 1)

    elif args.action == "train":
        success = pipeline.train_models()
        if not args.skip_db:
            pipeline.initialize_database()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()


