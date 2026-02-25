"""
多模态商品推荐系统 - 企业级架构主入口
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """主函数"""
    try:
        # 初始化系统
        from config.settings import settings
        from utils.logger import setup_logging, get_logger
        from data.database import db_manager
        from ui.main_window import MainWindow

        # 设置日志
        setup_logging()
        logger = get_logger(__name__)

        logger.info("=" * 50)
        logger.info("多模态商品推荐系统启动")
        logger.info("=" * 50)

        # 验证配置
        if not settings.validate_config():
            logger.error("配置验证失败，请检查配置文件")
            return 1

        logger.info("配置验证通过")

        # 初始化数据库
        logger.info("初始化数据库...")
        try:
            db_manager.create_tables()
            logger.info("数据库初始化成功")
        except ImportError as e:
            logger.warning(f"数据库依赖缺失，使用模拟数据模式: {e}")
            logger.info("程序将继续运行，但某些功能可能受限")
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            logger.info("程序将继续运行，使用模拟数据")
            # 不返回错误，继续运行

        # 启动GUI界面
        logger.info("启动用户界面...")
        from PyQt6.QtWidgets import QApplication

        app = QApplication(sys.argv)

        # 设置应用程序信息
        app.setApplicationName(settings.UI_CONFIG['window_title'])
        app.setApplicationVersion("1.0.0")

        # 显示登录窗口
        from ui.login_window import LoginWindow

        login_window = LoginWindow()
        if login_window.exec() == login_window.DialogCode.Accepted:
            current_user = login_window.current_user
            logger.info(f"用户 {current_user} 登录成功")

            # 创建主窗口（企业级 SPA 主界面）
            main_window = MainWindow(current_user)
            main_window.show()

            # 启动应用程序事件循环
            return app.exec()
        else:
            logger.info("用户取消登录")
            return 0

    except Exception as e:
        print(f"系统启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
