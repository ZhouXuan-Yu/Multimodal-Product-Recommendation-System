"""
商品卡片组件
显示商品信息和交互功能
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont, QColor
import os

from ui.styles import (
    PRODUCT_CARD_STYLE, BUTTON_STYLE,
    PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_COLOR,
    SUCCESS_COLOR, WARNING_COLOR, ERROR_COLOR,
    TEXT_COLOR, LIGHT_TEXT, BORDER_COLOR
)


class ProductCard(QWidget):
    """商品卡片组件"""

    # 信号定义
    clicked = pyqtSignal(dict)  # 点击商品时发出信号，传递商品信息
    favorited = pyqtSignal(dict)  # 收藏商品时发出信号

    def __init__(self, product_data, parent=None):
        super().__init__(parent)
        self.product_data = product_data
        self.is_favorited = False
        # 收紧卡片尺寸，使整体列表更紧凑
        self._base_width = 300
        self._base_height = 380
        self._shadow: QGraphicsDropShadowEffect | None = None
        self.init_ui()

    def init_ui(self):
        """初始化界面 - 现代化设计"""
        # 统一基础尺寸，保持稳定的卡片大小（不再随鼠标悬停缩放）
        self.setFixedSize(self._base_width, self._base_height)
        self.setStyleSheet(PRODUCT_CARD_STYLE + """
        QWidget {
            padding: 14px;
            margin: 4px;
        }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # 商品图片区域 - 更大的图片展示
        self.image_label = QLabel()
        self.image_label.setFixedSize(268, 210)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("""
        QLabel {
            background: linear-gradient(135deg, #F8F9FA 0%, #E9ECEF 100%);
            border-radius: 8px;
            border: 2px solid #F0F0F0;
        }
        """)

        # 加载商品图片
        self.load_product_image()
        layout.addWidget(self.image_label)

        # 商品标题 - 更大的字体和更好的排版
        title_label = QLabel(self.product_data.get('title', '商品标题'))
        title_label.setWordWrap(True)
        title_label.setMaximumHeight(44)
        title_label.setStyleSheet("""
        QLabel {
            font-size: 16px;
            font-weight: 600;
            color: #262626;
            line-height: 1.4;
        }
        """)
        layout.addWidget(title_label)

        # 商品价格和评分水平布局
        price_rating_layout = QHBoxLayout()
        price_rating_layout.setSpacing(12)

        # 商品价格
        price = self.product_data.get('price', '¥99.00')
        price_label = QLabel(f"{price}")
        price_label.setStyleSheet(f"""
        QLabel {{
            font-size: 18px;
            font-weight: bold;
            color: {PRIMARY_COLOR};
        }}
        """)

        # 商品评分
        rating = self.product_data.get('rating', '4.5')
        rating_label = QLabel(f"★ {rating}")
        rating_label.setStyleSheet(f"""
        QLabel {{
            font-size: 14px;
            color: {ACCENT_COLOR};
            font-weight: 500;
            padding: 4px 8px;
            background-color: #FFF7E6;
            border-radius: 4px;
        }}
        """)

        price_rating_layout.addWidget(price_label)
        price_rating_layout.addWidget(rating_label)
        price_rating_layout.addStretch()
        layout.addLayout(price_rating_layout)

        # 商品描述预览 - 更现代的样式
        description = self.product_data.get('description', '商品描述...')
        desc_label = QLabel(description[:80] + "..." if len(description) > 80 else description)
        desc_label.setWordWrap(True)
        desc_label.setMaximumHeight(40)
        desc_label.setStyleSheet("""
        QLabel {
            font-size: 12px;
            color: #8C8C8C;
            line-height: 1.5;
            background-color: #FAFAFA;
            padding: 8px 12px;
            border-radius: 6px;
            border-left: 3px solid #FF6B35;
        }
        """)
        layout.addWidget(desc_label)

        # 添加一些间距
        layout.addSpacing(8)

        # 按钮区域 - 现代化设计
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        # 查看详情按钮 - 主操作按钮
        view_btn = QPushButton("查看详情")
        view_btn.setFixedHeight(40)
        view_btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {PRIMARY_COLOR};
            color: white;
            border: none;
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 500;
            min-width: 100px;
        }}
        QPushButton:hover {{
            background-color: #E55A2B;
        }}
        QPushButton:pressed {{
            background-color: #CC4A26;
        }}
        """)
        view_btn.clicked.connect(self.on_view_clicked)

        # 收藏按钮 - 次要操作按钮
        self.favorite_btn = QPushButton("♡ 收藏")
        self.favorite_btn.setFixedHeight(40)
        self.favorite_btn.setStyleSheet(f"""
        QPushButton {{
            background-color: white;
            color: {TEXT_COLOR};
            border: 2px solid {BORDER_COLOR};
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 500;
            min-width: 100px;
        }}
        QPushButton:hover {{
            border-color: {PRIMARY_COLOR};
            color: {PRIMARY_COLOR};
            background-color: #FFF8F3;
        }}
        """)
        self.favorite_btn.clicked.connect(self.on_favorite_clicked)

        button_layout.addWidget(view_btn)
        button_layout.addWidget(self.favorite_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # 阴影效果，增强立体感（保持静态，不随鼠标变化）
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(15, 23, 42, 60))
        self.setGraphicsEffect(shadow)
        self._shadow = shadow

    def load_product_image(self):
        """加载商品图片"""
        image_path = self.product_data.get('image_path', '')

        if image_path and os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            # 缩放图片以适应显示区域
            scaled_pixmap = pixmap.scaled(
                240, 190,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
        else:
            # 显示默认图片占位符
            self.image_label.setText("暂无图片")
            self.image_label.setStyleSheet("""
            QLabel {
                background-color: #F8F9FA;
                border-radius: 6px;
                border: 1px solid #E9ECEF;
                color: #6C757D;
                font-size: 12px;
            }
            """)

    def on_view_clicked(self):
        """查看详情按钮点击事件"""
        self.clicked.emit(self.product_data)

    def on_favorite_clicked(self):
        """收藏按钮点击事件 - 现代化切换"""
        self.is_favorited = not self.is_favorited
        if self.is_favorited:
            self.favorite_btn.setText("♥ 已收藏")
            self.favorite_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ERROR_COLOR};
                color: white;
                border: 2px solid {ERROR_COLOR};
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
                min-width: 100px;
            }}
            QPushButton:hover {{
                background-color: #D4380D;
                border-color: #D4380D;
            }}
            """)
        else:
            self.favorite_btn.setText("♡ 收藏")
            self.favorite_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                color: {TEXT_COLOR};
                border: 2px solid {BORDER_COLOR};
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
                min-width: 100px;
            }}
            QPushButton:hover {{
                border-color: {PRIMARY_COLOR};
                color: {PRIMARY_COLOR};
                background-color: #FFF8F3;
            }}
            """)

        self.favorited.emit(self.product_data)

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.product_data)
        super().mousePressEvent(event)

    # 不再重载 enterEvent / leaveEvent，去掉鼠标悬停缩放和动态阴影变化效果


# 示例商品数据结构
def create_sample_product(product_id, title, price="¥99.00", rating="4.5", description="", image_path=""):
    """创建示例商品数据"""
    return {
        'id': product_id,
        'title': title,
        'price': price,
        'rating': rating,
        'description': description or f"这是{title}的详细描述，包含商品的主要特点和使用场景。",
        'image_path': image_path,
        'category': '示例分类'
    }


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget, QLabel

    app = QApplication(sys.argv)

    # 创建示例商品
    sample_product = create_sample_product(
        1,
        "iPhone 15 Pro",
        "¥8999.00",
        "4.8",
        "苹果最新旗舰手机，A17 Pro芯片，超强性能"
    )

    # 创建商品卡片
    card = ProductCard(sample_product)

    # 创建测试窗口
    test_window = QWidget()
    test_window.setWindowTitle("商品卡片测试")
    test_window.setFixedSize(320, 420)

    layout = QVBoxLayout()
    layout.addWidget(QLabel("商品卡片预览："))
    layout.addWidget(card)
    test_window.setLayout(layout)

    test_window.show()
    sys.exit(app.exec())
