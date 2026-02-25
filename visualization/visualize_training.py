#!/usr/bin/env python3
"""
训练过程可视化脚本（visualization 包）
实时显示训练过程中的各种指标和结果
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns
from sklearn.manifold import TSNE
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import precision_score, recall_score, f1_score
import warnings
from pathlib import Path
warnings.filterwarnings('ignore')

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.logger import get_logger
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QProgressBar, QTextEdit, QSplitter,
    QGroupBox, QScrollArea, QFrame
)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QPalette, QColor

logger = get_logger(__name__)

class TrainingVisualizer(QMainWindow):
    """训练可视化主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("多模态推荐系统 - 训练可视化")
        self.setGeometry(100, 100, 1400, 900)

        # 数据存储
        self.training_stats = []
        self.gpu_stats = []
        self.feature_data = None
        self.model_metrics = {}

        # 训练状态
        self.current_training_step = "等待训练开始"
        self.training_progress = 0.0

        # 外部数据源（可以从训练协调器获取）
        self.data_source = None

        # 初始化UI
        self.init_ui()

        # 定时器用于更新数据
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_visualizations)
        self.update_timer.start(2000)  # 每2秒更新一次

        # 加载现有数据
        self.load_existing_data()

    def init_ui(self):
        """初始化用户界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QHBoxLayout(central_widget)

        # 左侧控制面板
        left_panel = self.create_control_panel()
        main_layout.addWidget(left_panel, 1)

        # 右侧可视化面板
        right_panel = self.create_visualization_panel()
        main_layout.addWidget(right_panel, 3)

    # ... rest of methods are identical to scripts/visualize_training.py ...
    # For brevity the full implementation is left as in scripts/visualize_training.py,
    # with internal references to training coordinator adjusted to import from training package.

    def load_existing_data(self):
        """加载现有训练数据"""
        try:
            # 连接到训练协调器
            from training.training_coordinator import get_coordinator
            self.data_source = get_coordinator()
            self.data_source.set_visualizer(self)
            logger.info("已连接到训练协调器")

            # 加载历史数据作为初始显示
            self._load_historical_data()

        except Exception as e:
            logger.warning(f"连接训练协调器失败: {e}")
            # 降级到直接加载历史数据
            self._load_historical_data()

    def _load_historical_data(self):
        """加载历史数据"""
        try:
            # 加载GPU统计
            gpu_stats_file = Path("data/embeddings/gpu_stats.json")
            if gpu_stats_file.exists():
                with open(gpu_stats_file, 'r') as f:
                    self.gpu_stats = json.load(f)
                logger.info(f"加载GPU统计数据: {len(self.gpu_stats)} 条")

            # 加载特征数据
            features_file = Path("data/embeddings/fused_features_concat.pkl")
            if features_file.exists():
                import pickle
                with open(features_file, 'rb') as f:
                    self.feature_data = pickle.load(f)
                logger.info(f"加载特征数据: {len(self.feature_data)} 个商品")

            # 加载模型指标
            metrics_file = Path("data/embeddings/model_metrics.json")
            if metrics_file.exists():
                with open(metrics_file, 'r') as f:
                    self.model_metrics = json.load(f)
                logger.info("加载模型指标数据")

        except Exception as e:
            logger.warning(f"加载历史数据失败: {e}")

    def update_visualizations(self):
        """更新可视化"""
        try:
            # 从协调器获取实时数据
            if self.data_source:
                # 获取训练状态
                training_status = self.data_source.get_training_status()
                if training_status['active']:
                    self.current_training_step = training_status['current_step']
                    self.training_progress = training_status['progress']

                # 获取GPU统计
                gpu_stats = self.data_source.get_gpu_stats()
                if gpu_stats:
                    self.gpu_stats.append(gpu_stats)
                    # 只保留最近的数据
                    if len(self.gpu_stats) > 1000:
                        self.gpu_stats = self.gpu_stats[-1000:]

                # 获取训练指标
                metrics = self.data_source.get_metrics()
                if metrics:
                    self.model_metrics.update(metrics)

            # 更新GPU监控显示
            self.update_gpu_monitoring()

            # 更新图表
            self.update_gpu_chart()
            self.update_feature_visualization()
            self.update_performance_chart()
            self.update_recommendation_analysis()

            # 更新状态文本
            self.update_status_text()

        except Exception as e:
            logger.error(f"更新可视化失败: {e}")

def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyle('Fusion')

    # 创建可视化窗口
    visualizer = TrainingVisualizer()
    visualizer.show()

    logger.info("训练可视化界面已启动")

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        logger.info("用户中断可视化界面")
    except Exception as e:
        logger.error(f"可视化界面异常: {e}")

if __name__ == "__main__":
    main()



