#!/usr/bin/env python3
"""
GPU监控脚本（training 包）
实时监控GPU使用情况并保存统计数据
"""

import sys
import time
import json
from pathlib import Path
import argparse

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.logger import get_logger

logger = get_logger(__name__)

class GPUManager:
    """GPU管理器"""

    def __init__(self, coordinator=None):
        self.monitoring = False
        self.stats = []
        self.output_file = Path("data/embeddings/gpu_stats.json")
        self.coordinator = coordinator  # 训练协调器引用

        # 确保目录存在
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

    def check_gpu_availability(self):
        """检查GPU可用性"""
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                logger.info("GPU监控可用")
                logger.info(f"  GPU型号: {gpu.name}")
                logger.info(f"  GPU显存: {gpu.memoryTotal} MB")
                return True
            else:
                logger.warning("未检测到GPU")
                return False
        except ImportError:
            logger.error("GPUtil未安装，请运行: pip install GPUtil")
            return False
        except Exception as e:
            logger.error(f"GPU检测失败: {e}")
            return False

    def get_gpu_stats(self):
        """获取GPU统计信息"""
        try:
            import GPUtil
            import psutil

            gpus = GPUtil.getGPUs()
            if not gpus:
                return None

            gpu = gpus[0]

            # 获取CPU信息
            cpu_percent = psutil.cpu_percent(interval=1)

            # 获取内存信息
            memory = psutil.virtual_memory()

            stats = {
                'timestamp': time.time(),
                'gpu_id': gpu.id,
                'gpu_name': gpu.name,
                'gpu_load': gpu.load * 100,  # 转换为百分比
                'gpu_memory_used': gpu.memoryUsed,
                'gpu_memory_total': gpu.memoryTotal,
                'gpu_memory_free': gpu.memoryFree,
                'gpu_temperature': gpu.temperature,
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used': memory.used // (1024*1024),  # MB
                'memory_total': memory.total // (1024*1024)   # MB
            }

            return stats

        except Exception as e:
            logger.warning(f"获取GPU统计失败: {e}")
            return None

    def save_stats(self):
        """保存统计数据"""
        try:
            # 只保存最近1000条记录
            recent_stats = self.stats[-1000:] if len(self.stats) > 1000 else self.stats

            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(recent_stats, f, indent=2)

            logger.debug(f"已保存 {len(recent_stats)} 条GPU统计记录")

        except Exception as e:
            logger.error(f"保存GPU统计失败: {e}")

    def start_monitoring(self, interval=2.0):
        """开始监控"""
        if not self.check_gpu_availability():
            logger.error("无法启动GPU监控")
            return False

        logger.info(f"开始GPU监控 (间隔: {interval}秒)")
        logger.info("按Ctrl+C停止监控")

        self.monitoring = True

        try:
            while self.monitoring:
                stats = self.get_gpu_stats()
                if stats:
                    self.stats.append(stats)

                    # 实时显示
                    gpu_load = stats['gpu_load']
                    gpu_mem_used = stats['gpu_memory_used']
                    gpu_mem_total = stats['gpu_memory_total']
                    gpu_temp = stats['gpu_temperature']
                    cpu_percent = stats['cpu_percent']
                    mem_percent = stats['memory_percent']

                    logger.info(f"显存:{gpu_mem_used}/{gpu_mem_total}MB "
                                f"温度:{gpu_temp}°C "
                                f"CPU:{cpu_percent}% "
                                f"内存:{mem_percent}%")

                    # 保存数据
                    if len(self.stats) % 10 == 0:  # 每10次保存一次
                        self.save_stats()

                # 向协调器发送数据
                if self.coordinator:
                    try:
                        self.coordinator._send_gpu_stats(stats)
                    except Exception:
                        pass

                time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("用户停止GPU监控")
        except Exception as e:
            logger.error(f"GPU监控异常: {e}")
        finally:
            # 保存最终数据
            self.save_stats()
            logger.info(f"GPU监控结束，共收集 {len(self.stats)} 条数据")

        return True

    def show_stats_summary(self):
        """显示统计汇总"""
        if not self.stats:
            logger.info("没有统计数据")
            return

        logger.info("GPU监控统计汇总")
        logger.info("=" * 50)

        # 计算统计信息
        gpu_loads = [s['gpu_load'] for s in self.stats]
        gpu_temps = [s['gpu_temperature'] for s in self.stats]
        gpu_mem_used = [s['gpu_memory_used'] for s in self.stats]

        logger.info(f"监控时长: {len(self.stats) * 2} 秒")
        logger.info(f"GPU使用率 - 平均: {sum(gpu_loads)/len(gpu_loads):.1f}%, 峰值: {max(gpu_loads):.1f}%")
        logger.info(f"GPU温度 - 平均: {sum(gpu_temps)/len(gpu_temps):.1f}°C, 峰值: {max(gpu_temps)}°C")
        logger.info(f"显存使用 - 平均: {sum(gpu_mem_used)/len(gpu_mem_used):.0f}MB, 峰值: {max(gpu_mem_used)}MB")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="GPU监控工具")
    parser.add_argument("--interval", type=float, default=2.0,
                       help="监控间隔(秒)")
    parser.add_argument("--summary", action="store_true",
                       help="显示统计汇总")

    args = parser.parse_args()

    manager = GPUManager()

    if args.summary:
        # 显示汇总信息
        manager.stats = json.loads(manager.output_file.read_text()) if manager.output_file.exists() else []
        manager.show_stats_summary()
    else:
        # 开始监控
        manager.start_monitoring(args.interval)

if __name__ == "__main__":
    main()



