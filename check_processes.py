#!/usr/bin/env python3
"""
检查和管理系统进程
"""

import psutil
import os
import sys
from pathlib import Path

def get_python_processes():
    """获取Python进程信息"""
    python_processes = []

    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'cmdline']):
        try:
            if 'python' in proc.info['name'].lower():
                # 获取更多详细信息
                cpu_percent = proc.cpu_percent(interval=1.0)
                memory_mb = proc.memory_info().rss / 1024 / 1024

                # 获取命令行
                cmdline = ' '.join(proc.cmdline()) if proc.cmdline() else 'N/A'

                python_processes.append({
                    'pid': proc.pid,
                    'cpu_percent': cpu_percent,
                    'memory_mb': memory_mb,
                    'cmdline': cmdline[:100] + '...' if len(cmdline) > 100 else cmdline
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return python_processes

def show_processes():
    """显示Python进程"""
    print("Python进程监控")
    print("=" * 80)

    processes = get_python_processes()

    if not processes:
        print("没有找到Python进程")
        return

    print("<8")
    for proc in processes:
        print("<8")

    print("=" * 80)

    # 高CPU进程警告
    high_cpu = [p for p in processes if p['cpu_percent'] > 50]
    if high_cpu:
        print(f"\n[警告] 发现 {len(high_cpu)} 个高CPU占用进程 (>50%):")
        for proc in high_cpu:
            print(f"  PID {proc['pid']}: CPU {proc['cpu_percent']:.1f}%, 内存 {proc['memory_mb']:.1f}MB")

def kill_process(pid):
    """终止进程"""
    try:
        import signal
        os.kill(pid, signal.SIGTERM)
        print(f"已发送终止信号到进程 {pid}")
        return True
    except Exception as e:
        print(f"终止进程失败: {e}")
        return False

def main():
    """主函数"""
    if len(sys.argv) > 1:
        if sys.argv[1] == '--kill' and len(sys.argv) > 2:
            try:
                pid = int(sys.argv[2])
                kill_process(pid)
            except ValueError:
                print("无效的PID")
        elif sys.argv[1] == '--help':
            print("使用方法:")
            print("  python check_processes.py          # 查看进程")
            print("  python check_processes.py --kill PID # 终止进程")
        else:
            print("未知参数，使用 --help 查看帮助")
    else:
        show_processes()

if __name__ == "__main__":
    try:
        main()
    except ImportError:
        print("需要安装psutil: pip install psutil")
    except Exception as e:
        print(f"发生错误: {e}")
