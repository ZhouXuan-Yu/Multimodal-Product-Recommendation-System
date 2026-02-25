"""
界面样式定义文件
包含所有UI组件的样式设置
"""

# 主色调定义 - Modern Enterprise 风格
# 主色：科技深蓝 / 极客黑组合
PRIMARY_COLOR = "#005FB8"  # 科技深蓝（主按钮、链接等）
SECONDARY_COLOR = "#F5F7FA"  # 浅灰背景，用于页面底色
ACCENT_COLOR = "#FAAD14"  # 高亮强调色（辅助）
SUCCESS_COLOR = "#52C41A"  # 成功绿
WARNING_COLOR = "#FAAD14"  # 警示橙
ERROR_COLOR = "#FF4D4F"  # 价格红 / 错误色
TEXT_COLOR = "#1A1A1B"  # 极深灰，接近极客黑
LIGHT_TEXT = "#8C8C8C"  # 次级文字
BORDER_COLOR = "#E1E4EA"  # 冷灰边框
CARD_SHADOW = "0 18px 45px rgba(15, 23, 42, 0.08)"  # 柔和大阴影，提升企业级质感

# 主窗口样式 - 现代化电商风格
# 说明：
#   - 字体优先使用 Windows 常见中文字体，保证在中文环境下显示清晰、不走样
#   - 英文字体退化到 Segoe UI / system-ui
MAIN_WINDOW_STYLE = f"""
QMainWindow {{
    background-color: {SECONDARY_COLOR};
    border: none;
}}

QWidget {{
    font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", "SimHei", "Heiti SC", system-ui, sans-serif;
    font-size: 13px;
    color: {TEXT_COLOR};
}}

QScrollBar:vertical {{
    background-color: {SECONDARY_COLOR};
    width: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background-color: #D9D9D9;
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: #BFBFBF;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    border: none;
    background: none;
}}
"""

# 按钮样式 - 现代化设计
BUTTON_STYLE = f"""
QPushButton {{
    background-color: {PRIMARY_COLOR};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: 500;
    min-width: 80px;
}}

QPushButton:hover {{
    background-color: #E55A2B;
}}

QPushButton:pressed {{
    background-color: #CC4A26;
}}

QPushButton:disabled {{
    background-color: #F5F5F5;
    color: #D9D9D9;
}}

QPushButton.secondary {{
    background-color: white;
    color: {TEXT_COLOR};
    border: 1px solid {BORDER_COLOR};
}}

QPushButton.secondary:hover {{
    background-color: {SECONDARY_COLOR};
    border-color: {PRIMARY_COLOR};
}}
"""

# 搜索框样式
SEARCH_BOX_STYLE = f"""
QLineEdit {{
    border: 2px solid #E0E0E0;
    border-radius: 20px;
    padding: 8px 16px;
    font-size: 14px;
    background-color: white;
}}

QLineEdit:focus {{
    border-color: {PRIMARY_COLOR};
}}
"""

# 商品卡片样式 - 现代化电商风格（去除鼠标悬停动态效果，更稳定）
PRODUCT_CARD_STYLE = f"""
QWidget {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #FFFFFF,
                                stop:1 #F3F6FC);
    border-radius: 14px;
    border: 1px solid {BORDER_COLOR};
}}
"""

# 导航栏样式
NAV_BAR_STYLE = f"""
QListWidget {{
    background-color: white;
    border: none;
    outline: none;
}}

QListWidget::item {{
    padding: 12px 16px;
    border-bottom: 1px solid #F0F0F0;
    color: {TEXT_COLOR};
}}

QListWidget::item:hover {{
    background-color: {SECONDARY_COLOR};
}}

QListWidget::item:selected {{
    background-color: {PRIMARY_COLOR};
    color: white;
}}
"""

# 标签样式
LABEL_STYLE = f"""
QLabel {{
    color: {TEXT_COLOR};
    font-size: 12px;
}}

QLabel.title {{
    font-size: 16px;
    font-weight: bold;
    color: {TEXT_COLOR};
}}

QLabel.subtitle {{
    font-size: 14px;
    color: {LIGHT_TEXT};
}}
"""

# 滚动区域样式
SCROLL_AREA_STYLE = """
QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollArea QWidget {
    background-color: transparent;
}

QScrollBar:vertical {
    background-color: #F5F5F5;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #CCCCCC;
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #AAAAAA;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}
"""

# 统计面板样式
STATS_PANEL_STYLE = f"""
QWidget {{
    /* 半透明磨砂卡片风格，用于统计面板等悬浮组件 */
    background-color: rgba(255, 255, 255, 220);
    border-radius: 16px;
    border: 1px solid #E0E0E0;
}}

QLabel.title {{
    font-size: 14px;
    font-weight: bold;
    color: {TEXT_COLOR};
    margin-bottom: 8px;
}}
"""

# 弹窗样式
DIALOG_STYLE = f"""
QDialog {{
    background-color: white;
    border-radius: 8px;
}}

QLabel {{
    color: {TEXT_COLOR};
}}
"""
