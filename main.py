"""
多模态商品推荐系统主程序
启动整个应用程序
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# 添加UI模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'ui'))

from ui.login_window import LoginWindow
from ui.main_window import MainWindow


def main():
    """主函数"""
    # 启用高DPI支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # 创建应用程序
    app = QApplication(sys.argv)

    # 设置应用程序信息
    app.setApplicationName("多模态商品推荐系统")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("毕业设计")

    # 显示登录窗口
    login_window = LoginWindow()

    # 如果登录成功，显示主窗口
    if login_window.exec() == login_window.DialogCode.Accepted:
        current_user = login_window.current_user

        # 创建主窗口
        main_window = MainWindow(current_user)
        main_window.show()

        # 启动应用程序事件循环
        return app.exec()
    else:
        # 登录取消，直接退出
        return 0


if __name__ == "__main__":
    sys.exit(main())

