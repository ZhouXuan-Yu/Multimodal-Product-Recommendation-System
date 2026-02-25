#!/usr/bin/env python3
"""
环境设置脚本
用于创建和配置Conda环境
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """运行命令并显示状态"""
    print(f"正在{description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description}成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description}失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False

def main():
    """主函数"""
    print("多模态商品推荐系统 - 环境设置脚本")
    print("=" * 50)

    project_root = Path(__file__).parent.parent

    # 检查Conda是否安装
    print("检查Conda安装...")
    try:
        result = subprocess.run(['conda', '--version'], capture_output=True, text=True)
        print(f"✓ Conda版本: {result.stdout.strip()}")
    except FileNotFoundError:
        print("✗ Conda未安装，请先安装Miniconda或Anaconda")
        print("下载地址: https://docs.conda.io/en/latest/miniconda.html")
        return 1

    # 创建Conda环境
    env_name = "jin"
    env_file = project_root / "requirements" / "environment.yml"

    if not env_file.exists():
        print(f"✗ 环境配置文件不存在: {env_file}")
        return 1

    # 检查环境是否已存在
    try:
        result = subprocess.run(['conda', 'env', 'list'], capture_output=True, text=True)
        if f"{env_name} " in result.stdout:
            print(f"环境 '{env_name}' 已存在")
            response = input("是否要重新创建环境? (y/N): ").strip().lower()
            if response == 'y':
                print("删除现有环境...")
                run_command(f"conda env remove -n {env_name}", f"删除环境 {env_name}")
            else:
                print("使用现有环境")
                return activate_environment(env_name)
    except:
        pass

    # 创建新环境
    if not run_command(f"conda env create -f {env_file}", f"创建Conda环境 {env_name}"):
        return 1

    return activate_environment(env_name)

def activate_environment(env_name):
    """激活环境并安装额外依赖"""
    print(f"\n环境 '{env_name}' 创建成功！")
    print("\n下一步:")
    print("1. 激活环境:")
    print(f"   conda activate {env_name}")
    print("\n2. 运行主程序:")
    print("   python main_enterprise.py")
    print("\n3. 如果遇到PyQt6问题，可以尝试:")
    print("   pip uninstall PyQt6 PyQt6-Qt6")
    print("   conda install pyqt")
    print("\n4. 或者使用备用启动脚本:")
    print("   python main.py (简化版本)")

    return 0

if __name__ == "__main__":
    sys.exit(main())

