#!/usr/bin/env python3
"""
快速启动脚本
自动检测环境并运行合适的版本
"""

import sys
import os
from pathlib import Path

def check_environment():
    """检查运行环境"""
    try:
        import PyQt6
        # 尝试导入具体的模块来确保可用
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        return "full"
    except (ImportError, Exception) as e:
        print(f"PyQt6不可用: {e}")
        try:
            # 检查是否有其他GUI库
            import tkinter
            return "limited"
        except ImportError:
            return "cli"

def run_full_version():
    """运行完整版本"""
    print("检测到PyQt6环境，启动完整GUI版本...")

    try:
        os.system("python main_enterprise.py")
    except Exception as e:
        print(f"完整版本启动失败: {e}")
        print("尝试启动简化版本...")
        run_limited_version()

def run_limited_version():
    """运行简化版本"""
    print("PyQt6不可用，启动命令行演示版本...")
    os.system("python cli_demo.py")

def run_cli_version():
    """运行CLI版本"""
    print("GUI环境不可用，显示系统信息...")
    os.system("python -c \"from config.settings import settings; print('系统配置加载成功'); print(f'Python版本: {sys.version}'); print(f'项目根目录: {settings.PROJECT_ROOT}')\"")

def main():
    """主函数"""
    print("多模态商品推荐系统 - 快速启动")
    print("=" * 40)

    # 检测环境
    env_type = check_environment()
    print(f"检测到环境类型: {env_type}")

    if env_type == "full":
        run_full_version()
    elif env_type == "limited":
        run_limited_version()
    else:
        run_cli_version()

    print("\n启动完成！")

if __name__ == "__main__":
    main()
