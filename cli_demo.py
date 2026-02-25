#!/usr/bin/env python3
"""
多模态商品推荐系统 - 命令行演示版本
纯文本界面，避免编码问题
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def show_welcome():
    """显示欢迎信息"""
    print("=" * 60)
    print("  多模态商品推荐系统 - 命令行演示")
    print("  Multimodal Product Recommendation System")
    print("=" * 60)
    print()

def show_menu():
    """显示菜单"""
    print("请选择演示内容:")
    print("1. 系统架构概述")
    print("2. 界面设计展示")
    print("3. 功能特性说明")
    print("4. 示例数据展示")
    print("5. 运行环境检查")
    print("6. 启动完整系统")
    print("0. 退出")
    print()

def show_architecture():
    """显示系统架构"""
    print("\n[系统架构]")
    print("=" * 50)
    print("""
企业级分层架构:
├── 表示层 (UI)
│   ├── 现代化电商界面
│   ├── 商品卡片组件
│   └── 统计面板
├── 业务逻辑层 (Core)
│   ├── 推荐引擎
│   ├── 用户管理
│   └── 商品管理
├── 数据访问层 (Data)
│   ├── 数据库连接池
│   ├── ORM模型
│   └── 数据操作
└── 基础设施层 (Utils)
    ├── 配置管理
    ├── 日志系统
    └── 异常处理
    """)

def show_ui_design():
    """显示界面设计"""
    print("\n[界面设计]")
    print("=" * 50)
    print("""
现代化电商界面:
┌─────────────────────────────────────┐
│         顶部导航栏 (70px)             │
│  [Logo] [首页] [电子] [服装] [家居]   │
│  [搜索框] [搜索] [刷新] [用户] [统计] │
├─────────────────────────────────────┤
│                                     │
│        商品展示区域                   │
│   ┌─────┬─────┬─────┬─────┬─────┐   │
│   │卡片1 │卡片2 │卡片3 │卡片4 │卡片5 │   │
│   │     │     │     │     │     │   │
│   └─────┴─────┴─────┴─────┴─────┘   │
│                                     │
│   [滚动查看更多商品...]             │
│                                     │
└─────────────────────────────────────┘

+-------------------------------------+
|         统计面板 (独立窗口)          |
|  ┌─────┬─────┬─────┬─────┐         |
|  │今日推│点击率│收藏数│用户活│         |
|  │荐:1K│23.5%│89    │456  │         |
|  └─────┴─────┴─────┴─────┘         |
|                                     |
|  [图表] 点击率趋势分析             |
|  [饼图] 用户偏好分布               |
|  [柱状] 热门商品Top10              |
+-------------------------------------+
    """)

def show_features():
    """显示功能特性"""
    print("\n[核心功能]")
    print("=" * 50)
    print("""
✓ 用户系统
  - 用户注册和登录
  - 个人偏好设置
  - 行为历史记录

✓ 商品管理
  - 商品信息展示
  - 分类浏览功能
  - 智能搜索功能

✓ 推荐引擎
  - 多模态特征融合
  - 个性化推荐算法
  - 冷启动处理

✓ 数据可视化
  - 推荐效果统计
  - 图表展示分析
  - 实时数据更新

✓ 界面特性
  - 现代化设计
  - 响应式布局
  - 流畅动画效果
    """)

def show_sample_data():
    """显示示例数据"""
    print("\n[示例商品数据]")
    print("=" * 50)

    products = [
        {"id": "001", "name": "iPhone 15 Pro", "price": "¥8999", "rating": "4.8"},
        {"id": "002", "name": "MacBook Pro", "price": "¥19999", "rating": "4.9"},
        {"id": "003", "name": "Nike Air Max", "price": "¥899", "rating": "4.4"},
        {"id": "004", "name": "Dyson吸尘器", "price": "¥3999", "rating": "4.7"},
    ]

    print("<5")
    for product in products:
        print("<5")
    print("<5")
    print()

def check_environment():
    """检查运行环境"""
    print("\n[环境检查]")
    print("=" * 50)

    # 检查Python版本
    version = sys.version_info
    python_ok = version.major >= 3 and version.minor >= 8
    print(f"Python版本: {version.major}.{version.minor}.{version.micro} - {'✓' if python_ok else '✗'}")

    # 检查关键模块
    modules_to_check = ['numpy', 'matplotlib', 'PIL']
    for module in modules_to_check:
        try:
            __import__(module)
            print(f"{module}: ✓")
        except ImportError:
            print(f"{module}: ✗")

    # 检查可选模块
    try:
        import PyQt6
        print("PyQt6: ✓ (可运行完整GUI)")
    except ImportError:
        print("PyQt6: ✗ (将使用命令行模式)")

    try:
        import pymysql
        print("pymysql: ✓ (可连接数据库)")
    except ImportError:
        print("pymysql: ✗ (将使用模拟数据)")

    print()

def run_system():
    """启动系统"""
    print("\n[启动系统]")
    print("=" * 50)

    try:
        import subprocess
        result = subprocess.run([sys.executable, "run.py"], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("系统启动成功!")
        else:
            print("系统启动失败:")
            print(result.stderr)
    except Exception as e:
        print(f"启动失败: {e}")

def main():
    """主函数"""
    show_welcome()

    while True:
        show_menu()
        try:
            choice = input("请选择 (0-6): ").strip()

            if choice == "0":
                print("感谢使用，再见!")
                break
            elif choice == "1":
                show_architecture()
            elif choice == "2":
                show_ui_design()
            elif choice == "3":
                show_features()
            elif choice == "4":
                show_sample_data()
            elif choice == "5":
                check_environment()
            elif choice == "6":
                run_system()
            else:
                print("无效选择，请重新输入")

            input("\n按Enter键继续...")

        except KeyboardInterrupt:
            print("\n\n用户中断")
            break
        except Exception as e:
            print(f"发生错误: {e}")

if __name__ == "__main__":
    main()

