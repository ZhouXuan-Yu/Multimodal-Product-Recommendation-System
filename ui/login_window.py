"""
登录窗口模块
提供用户登录和注册功能
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui.styles import DIALOG_STYLE, BUTTON_STYLE, SEARCH_BOX_STYLE, LABEL_STYLE


class LoginWindow(QDialog):
    """登录窗口类"""

    def __init__(self):
        super().__init__()
        self.user_credentials = {
            "admin": "admin",  # 默认管理员账户
            "user1": "123456",  # 示例用户
        }
        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("多模态商品推荐系统 - 登录")
        self.setFixedSize(400, 500)
        self.setStyleSheet(DIALOG_STYLE)

        # 主布局
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # 标题
        title_label = QLabel("多模态商品推荐系统")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #4A90E2; margin-bottom: 10px;")
        layout.addWidget(title_label)

        subtitle_label = QLabel("基于多模态融合的个性化推荐")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("font-size: 12px; color: #666666; margin-bottom: 30px;")
        layout.addWidget(subtitle_label)

        # 用户名输入
        username_layout = QVBoxLayout()
        username_label = QLabel("用户名")
        username_label.setStyleSheet("font-weight: bold; color: #333333;")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名")
        self.username_input.setStyleSheet(SEARCH_BOX_STYLE)
        self.username_input.setFixedHeight(40)
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        layout.addLayout(username_layout)

        # 密码输入
        password_layout = QVBoxLayout()
        password_label = QLabel("密码")
        password_label.setStyleSheet("font-weight: bold; color: #333333;")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet(SEARCH_BOX_STYLE)
        self.password_input.setFixedHeight(40)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        layout.addLayout(password_layout)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)

        self.login_btn = QPushButton("登录")
        self.login_btn.setFixedHeight(45)
        self.login_btn.setStyleSheet(BUTTON_STYLE)
        self.login_btn.clicked.connect(self.login)

        self.register_btn = QPushButton("注册")
        self.register_btn.setFixedHeight(45)
        self.register_btn.setStyleSheet(f"""
        QPushButton {{
            background-color: #28a745;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 12px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: #218838;
        }}
        QPushButton:pressed {{
            background-color: #1e7e34;
        }}
        """)
        self.register_btn.clicked.connect(self.register)

        button_layout.addWidget(self.login_btn)
        button_layout.addWidget(self.register_btn)
        layout.addLayout(button_layout)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("color: #E0E0E0; margin: 20px 0;")
        layout.addWidget(line)

        # 演示账户提示
        demo_label = QLabel("演示账户：admin/admin 或 user1/123456")
        demo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        demo_label.setStyleSheet("font-size: 11px; color: #999999; font-style: italic;")
        layout.addWidget(demo_label)

        self.setLayout(layout)

        # 设置默认焦点
        self.username_input.setFocus()

    def login(self):
        """登录处理"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "提示", "请输入用户名和密码")
            return

        if username in self.user_credentials and self.user_credentials[username] == password:
            QMessageBox.information(self, "成功", f"欢迎回来，{username}！")
            self.current_user = username
            self.accept()  # 关闭对话框并返回Accepted
        else:
            QMessageBox.warning(self, "错误", "用户名或密码错误")

    def register(self):
        """注册处理"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "提示", "请输入用户名和密码")
            return

        if username in self.user_credentials:
            QMessageBox.warning(self, "错误", "用户名已存在")
            return

        if len(password) < 6:
            QMessageBox.warning(self, "错误", "密码长度至少6位")
            return

        # 添加新用户
        self.user_credentials[username] = password
        QMessageBox.information(self, "成功", "注册成功，请登录")
        self.username_input.clear()
        self.password_input.clear()
        self.username_input.setFocus()


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    login_window = LoginWindow()
    if login_window.exec() == QDialog.DialogCode.Accepted:
        print(f"登录成功，用户：{login_window.current_user}")
    else:
        print("登录取消")

