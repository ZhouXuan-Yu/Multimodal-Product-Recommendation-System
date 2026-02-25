#!/usr/bin/env python3
"""
训练协调器（training 包）
负责协调训练过程和可视化展示
"""

import sys
import time
import threading
import queue
from pathlib import Path
from typing import Dict, Any, Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.logger import get_logger

logger = get_logger(__name__)

class TrainingCoordinator:
    """训练协调器"""

    def __init__(self):
        self.training_active = False
        self.training_thread = None
        self.visualizer = None

        # 数据队列，用于传递训练状态到可视化界面
        self.status_queue = queue.Queue()
        self.gpu_stats_queue = queue.Queue()
        self.metrics_queue = queue.Queue()

        # 训练状态
        self.current_step = ""
        self.progress = 0.0
        self.training_stats = {}

    def set_visualizer(self, visualizer):
        """设置可视化界面引用"""
        self.visualizer = visualizer
        logger.info("可视化界面已连接到训练协调器")

    def start_training(self, training_config: Dict[str, Any]):
        """开始训练"""
        if self.training_active:
            logger.warning("训练已在进行中")
            return False

        self.training_active = True
        self.training_thread = threading.Thread(
            target=self._run_training_pipeline,
            args=(training_config,),
            daemon=True
        )
        self.training_thread.start()

        logger.info("训练已启动")
        return True

    def stop_training(self):
        """停止训练"""
        self.training_active = False
        if self.training_thread and self.training_thread.is_alive():
            self.training_thread.join(timeout=5.0)
        logger.info("训练已停止")

    def get_training_status(self) -> Dict[str, Any]:
        """获取训练状态"""
        return {
            'active': self.training_active,
            'current_step': self.current_step,
            'progress': self.progress,
            'stats': self.training_stats.copy()
        }

    def get_gpu_stats(self) -> Optional[Dict[str, Any]]:
        """获取最新的GPU统计"""
        try:
            return self.gpu_stats_queue.get_nowait()
        except queue.Empty:
            return None

    def get_metrics(self) -> Optional[Dict[str, Any]]:
        """获取最新的训练指标"""
        try:
            return self.metrics_queue.get_nowait()
        except queue.Empty:
            return None

    def _run_training_pipeline(self, config: Dict[str, Any]):
        """运行训练流水线"""
        try:
            from training.run_training_pipeline import TrainingPipeline

            # 创建训练流水线实例，并传入协调器引用
            pipeline = TrainingPipeline(coordinator=self)

            # 运行流水线
            self._update_status("初始化训练环境", 0.0)
            success = pipeline.run_full_pipeline()

            if success:
                self._update_status("训练成功完成", 1.0)
                logger.info("训练流水线执行成功")
            else:
                self._update_status("训练失败", -1.0)
                logger.error("训练流水线执行失败")

        except Exception as e:
            logger.error(f"训练流水线异常: {e}")
            self._update_status(f"训练异常: {e}", -1.0)
        finally:
            self.training_active = False

    def _update_status(self, step: str, progress: float):
        """更新训练状态"""
        self.current_step = step
        self.progress = max(0.0, min(1.0, progress))

        status_data = {
            'step': step,
            'progress': progress,
            'timestamp': time.time()
        }

        # 发送到队列
        try:
            self.status_queue.put_nowait(status_data)
        except queue.Full:
            pass  # 队列满时跳过

        logger.info(f"训练进度更新: {step} - {progress:.1f}")

    def _send_gpu_stats(self, stats: Dict[str, Any]):
        """发送GPU统计数据"""
        try:
            self.gpu_stats_queue.put_nowait(stats)
        except queue.Full:
            pass

    def _send_metrics(self, metrics: Dict[str, Any]):
        """发送训练指标"""
        try:
            self.metrics_queue.put_nowait(metrics)
        except queue.Full:
            pass

# 全局协调器实例
training_coordinator = TrainingCoordinator()

def get_coordinator() -> TrainingCoordinator:
    """获取全局训练协调器实例"""
    return training_coordinator



