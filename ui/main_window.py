"""
主窗口模块
包含搜索栏、导航栏、商品展示区域和统计面板
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QScrollArea, QGridLayout, QLabel, QFrame, QMessageBox,
    QSplitter, QStackedWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QEasingCurve, QPropertyAnimation, QEvent, QTimer
from PyQt6.QtGui import QFont, QIcon, QPixmap
import sys
import os
import random

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui.styles import (
    MAIN_WINDOW_STYLE, SEARCH_BOX_STYLE, NAV_BAR_STYLE,
    SCROLL_AREA_STYLE, BUTTON_STYLE,
    PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_COLOR,
    SUCCESS_COLOR, WARNING_COLOR, ERROR_COLOR,
    TEXT_COLOR, LIGHT_TEXT, BORDER_COLOR
)
from ui.product_card import ProductCard, create_sample_product
from ui.stats_panel import StatDashboard

from core.product_manager import ProductManager
from core.recommendation_engine import RecommendationEngine
from core.user_manager import UserManager
from data.models import Product, User
from utils.logger import get_logger
from utils.exceptions import ModelError


logger = get_logger(__name__)


class Navigation(QWidget):
    """
    顶部导航栏组件

    - 负责切换主内容区页面（推荐流 / 统计大屏）
    - 同时承载用户信息与登出入口
    """

    pageChanged = pyqtSignal(int)          # 0: 推荐流, 1: 统计大屏
    categoryChanged = pyqtSignal(str)      # 商品分类切换
    logoutRequested = pyqtSignal()         # 登出请求

    def __init__(self, current_user: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.current_user = current_user
        self._build_ui()

    def _build_ui(self) -> None:
        border_color = globals().get('BORDER_COLOR', '#E1E4EA')
        primary_color = globals().get('PRIMARY_COLOR', '#005FB8')
        secondary_hover = globals().get('SECONDARY_COLOR', '#F5F7FA')
        text_color = globals().get('TEXT_COLOR', '#1A1A1B')

        self.setFixedHeight(70)
        self.setStyleSheet(f"""
        QWidget {{
            background-color: rgba(255, 255, 255, 0.96);
            border-bottom: 1px solid {border_color};
        }}
        """)

        nav_layout = QHBoxLayout(self)
        nav_layout.setContentsMargins(20, 10, 20, 10)
        nav_layout.setSpacing(20)

        # Logo 区域
        logo_layout = QVBoxLayout()
        logo_label = QLabel("Jin Recommender")
        logo_label.setStyleSheet(f"""
        QLabel {{
            font-size: 18px;
            font-weight: 700;
            letter-spacing: 0.5px;
            color: {primary_color};
        }}
        """)
        subtitle_label = QLabel("多模态商品个性化推荐系统")
        subtitle_label.setStyleSheet("""
        QLabel {
            font-size: 10px;
            color: #8C8C8C;
        }
        """)
        logo_layout.addWidget(logo_label)
        logo_layout.addWidget(subtitle_label)
        nav_layout.addLayout(logo_layout)

        # 顶部 Tab 导航（负责切换 QStackedWidget 页面）
        tab_container = QWidget()
        tab_layout = QHBoxLayout(tab_container)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(8)

        self.recommend_tab = QPushButton("推荐流")
        self.dashboard_tab = QPushButton("统计大屏")
        for btn in (self.recommend_tab, self.dashboard_tab):
            btn.setCheckable(True)
            btn.setFixedHeight(38)
            btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {text_color};
                border: none;
                border-radius: 19px;
                padding: 8px 20px;
                font-size: 14px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {secondary_hover};
            }}
            QPushButton:checked {{
                background-color: {primary_color};
                color: #FFFFFF;
            }}
            """)

        self.recommend_tab.setChecked(True)

        self.recommend_tab.clicked.connect(lambda: self._on_tab_clicked(0))
        self.dashboard_tab.clicked.connect(lambda: self._on_tab_clicked(1))

        tab_layout.addWidget(self.recommend_tab)
        tab_layout.addWidget(self.dashboard_tab)
        nav_layout.addWidget(tab_container)

        # 分类快速筛选（仍然使用原有的业务分类）
        categories = [
            ("🏠 全部", "all"),
            ("📱 电子", "electronics"),
            ("👕 服装", "fashion"),
            ("🏠 家居", "home"),
            ("📚 图书", "books"),
            ("🍎 食品", "food"),
        ]
        category_container = QWidget()
        category_layout = QHBoxLayout(category_container)
        category_layout.setContentsMargins(0, 0, 0, 0)
        category_layout.setSpacing(4)

        for text, category in categories:
            btn = QPushButton(text)
            btn.setFixedHeight(32)
            btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {text_color};
                border-radius: 16px;
                padding: 4px 12px;
                border: 1px solid transparent;
                font-size: 12px;
            }}
            QPushButton:hover {{
                border-color: {border_color};
                background-color: {secondary_hover};
            }}
            """)
            btn.clicked.connect(lambda checked, cat=category: self.categoryChanged.emit(cat))
            category_layout.addWidget(btn)

        nav_layout.addWidget(category_container)

        # 弹性空间
        nav_layout.addStretch()

        # 用户信息与操作
        user_layout = QHBoxLayout()
        user_layout.setSpacing(12)

        user_info_btn = QPushButton(f"👤 {self.current_user}")
        user_info_btn.setFixedHeight(36)
        user_info_btn.setStyleSheet(f"""
        QPushButton {{
            background-color: rgba(0,0,0,0.02);
            color: {text_color};
            border-radius: 18px;
            padding: 6px 14px;
            border: 1px solid {border_color};
            font-size: 12px;
        }}
        QPushButton:hover {{
            border-color: {primary_color};
        }}
        """)
        user_layout.addWidget(user_info_btn)

        logout_btn = QPushButton("登出")
        logout_btn.setFixedHeight(36)
        logout_btn.setStyleSheet(f"""
        QPushButton {{
            background-color: transparent;
            color: #8C8C8C;
            border-radius: 18px;
            padding: 6px 14px;
            border: 1px solid {border_color};
            font-size: 12px;
        }}
        QPushButton:hover {{
            border-color: {globals().get('ERROR_COLOR', '#FF4D4F')};
            color: {globals().get('ERROR_COLOR', '#FF4D4F')};
            background-color: #FFF2F0;
        }}
        """)
        logout_btn.clicked.connect(self.logoutRequested.emit)
        user_layout.addWidget(logout_btn)

        nav_layout.addLayout(user_layout)

    def _on_tab_clicked(self, index: int) -> None:
        """处理顶部 Tab 点击，发出页面切换信号"""
        if index == 0:
            self.recommend_tab.setChecked(True)
            self.dashboard_tab.setChecked(False)
        else:
            self.recommend_tab.setChecked(False)
            self.dashboard_tab.setChecked(True)
        self.pageChanged.emit(index)


class MainWindow(QMainWindow):
    """主窗口类（企业级 SPA 架构容器）"""

    def __init__(self, current_user="admin"):
        super().__init__()
        self.current_user = current_user  # 用户名（用于展示）
        self.current_user_id = current_user  # 默认使用用户名作为后端标识
        self.current_category = "all"
        self.current_products_list: list[dict] = []  # 当前网格中展示的商品
        self.current_grid_cols: int = 0             # 当前网格列数（自适应）

        # 前端示例商品（无后端或无数据时使用）
        self.sample_products = self.generate_sample_products()

        # 后端相关对象
        self.user_manager: UserManager | None = None
        self.product_manager: ProductManager | None = None
        self.rec_engine: RecommendationEngine | None = None
        self.home_recommendations: list[dict] = []
        self.backend_available: bool = False

        # 初始化后端管理器（允许在无数据库时自动降级）
        try:
            self.user_manager = UserManager()
            self.product_manager = ProductManager()
            self.rec_engine = RecommendationEngine()

            # 如果数据库中存在该用户名，则使用真实 user_id
            try:
                user = User.get_by_username(current_user)
                if user:
                    self.current_user_id = user.user_id
            except Exception as e:
                logger.warning(
                    f"查找用户 {current_user} 失败，将使用用户名作为标识: {e}"
                )
        except Exception as e:
            logger.warning(f"初始化后端管理器失败，将使用纯前端模式: {e}")
            self.user_manager = None
            self.product_manager = None
            self.rec_engine = None

        self.init_ui()

        # 尝试加载首页个性化推荐（如后端可用）
        self.load_home_recommendations()

    def init_ui(self):
        """初始化界面 - 现代化电商风格"""
        self.setWindowTitle(f"多模态商品推荐系统 - {self.current_user}")
        self.setGeometry(50, 50, 1600, 1000)
        self.setStyleSheet(MAIN_WINDOW_STYLE)

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局 - 垂直布局，包含顶部导航和主体内容
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部导航栏（独立组件）
        self.navigation = Navigation(self.current_user, self)
        main_layout.addWidget(self.navigation)

        # 主体内容区域：基于 QStackedWidget 的 SPA 结构
        self.stacked = QStackedWidget()
        self.stacked.setContentsMargins(0, 0, 0, 0)

        # 页面 0：商品推荐流
        self.products_page = self._build_products_page()
        self.stacked.addWidget(self.products_page)

        # 页面 1：统计大屏
        self.stats_page = StatDashboard(self)
        self.stacked.addWidget(self.stats_page)

        main_layout.addWidget(self.stacked)
        central_widget.setLayout(main_layout)

        # 连接导航信号
        self._connect_navigation()

    def _build_products_page(self) -> QWidget:
        """构建推荐流页面（搜索区 + 商品网格）"""
        content_container = QWidget()
        content_container.setStyleSheet(f"""
        QWidget {{
            background-color: {globals().get('SECONDARY_COLOR', '#F5F7FA')};
        }}
        """)

        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)

        # 搜索区域
        search_area = self.create_search_area()
        content_layout.addWidget(search_area)

        # 商品展示区域
        products_area = self.create_products_area()
        content_layout.addWidget(products_area)

        return content_container

    def _connect_navigation(self) -> None:
        """连接 Navigation 与主内容区的信号槽"""
        self.navigation.pageChanged.connect(self._on_page_changed)
        self.navigation.categoryChanged.connect(self.on_category_clicked)
        self.navigation.logoutRequested.connect(self.logout)

    def _on_page_changed(self, index: int) -> None:
        """处理顶部 Tab 导航触发的页面切换，带简洁动画"""
        current_index = self.stacked.currentIndex()
        if index == current_index:
            return

        old_widget = self.stacked.currentWidget()
        new_widget = self.stacked.widget(index)

        width = self.stacked.width() or 1
        direction = 1 if index > current_index else -1

        # 初始化新页面位置与透明度
        new_widget.move(direction * width, new_widget.y())
        new_widget.setWindowOpacity(0.0)
        self.stacked.setCurrentIndex(index)

        # 水平位移动画
        slide_anim = QPropertyAnimation(new_widget, b"pos", self)
        slide_anim.setDuration(260)
        slide_anim.setStartValue(new_widget.pos())
        slide_anim.setEndValue(old_widget.pos())
        slide_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # 淡入动画
        fade_anim = QPropertyAnimation(new_widget, b"windowOpacity", self)
        fade_anim.setDuration(260)
        fade_anim.setStartValue(0.0)
        fade_anim.setEndValue(1.0)
        fade_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        slide_anim.start()
        fade_anim.start()

    def create_left_content(self):
        """创建左侧内容区域"""
        content_widget = QWidget()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # 顶部搜索区域
        search_area = self.create_search_area()
        layout.addWidget(search_area)

        # 商品展示区域
        products_area = self.create_products_area()
        layout.addWidget(products_area)

        content_widget.setLayout(layout)
        return content_widget

    def create_search_area(self):
        """创建搜索区域"""
        search_widget = QWidget()
        search_widget.setFixedHeight(80)
        search_widget.setStyleSheet("""
        QWidget {
            background-color: white;
            border-radius: 8px;
            border: 1px solid #E0E0E0;
        }
        """)

        layout = QHBoxLayout()
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)

        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索商品...")
        self.search_input.setStyleSheet(SEARCH_BOX_STYLE)
        self.search_input.setFixedHeight(40)
        self.search_input.returnPressed.connect(self.search_products)

        # 搜索按钮
        search_btn = QPushButton("🔍 搜索")
        search_btn.setFixedSize(80, 40)
        search_btn.setStyleSheet(BUTTON_STYLE)
        search_btn.clicked.connect(self.search_products)

        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setFixedSize(80, 40)
        refresh_btn.setStyleSheet(f"""
        QPushButton {{
            background-color: #6C757D;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 12px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: #5A6268;
        }}
        """)
        refresh_btn.clicked.connect(self.refresh_products)

        layout.addWidget(self.search_input)
        layout.addWidget(search_btn)
        layout.addWidget(refresh_btn)
        layout.addStretch()

        search_widget.setLayout(layout)
        return search_widget

    def create_products_area(self):
        """创建商品展示区域"""
        products_widget = QWidget()
        products_widget.setStyleSheet("""
        QWidget {
            background-color: white;
            border-radius: 8px;
            border: 1px solid #E0E0E0;
        }
        """)

        layout = QVBoxLayout()
        # 整体内边距稍微收紧一点，避免留白过多
        layout.setContentsMargins(16, 16, 16, 16)

        # 商品区域标题（参考淘宝：更简洁的标题行）
        title_layout = QHBoxLayout()
        title_label = QLabel("为你推荐的商品")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333333;")

        self.product_count_label = QLabel(f"共 {len(self.sample_products)} 件商品")
        self.product_count_label.setStyleSheet("font-size: 12px; color: #666666;")

        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.product_count_label)
        layout.addLayout(title_layout)

        # 顶部 Banner 区域（类似淘宝首页自动轮播，但更轻量，不突兀）
        banner_area = self.create_banner_area()
        layout.addWidget(banner_area)

        # 商品网格滚动区域
        self.create_products_grid(layout)

        products_widget.setLayout(layout)
        return products_widget

    def create_banner_area(self) -> QWidget:
        """创建顶部自动轮播 Banner 区域，参考淘宝首页大图轮播"""
        banner_widget = QWidget()
        # 整体高度降低一点，更紧凑
        banner_widget.setFixedHeight(170)
        banner_widget.setStyleSheet("""
        QWidget {
            background-color: white;
            border-radius: 8px;
            border: 1px solid #E0E0E0;
        }
        """)

        layout = QVBoxLayout(banner_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)

        self.banner_stack = QStackedWidget()
        self.banner_stack.setContentsMargins(0, 0, 0, 0)

        # 简单示例 Banner，可以后续替换为真实运营活动图
        banners = [
            ("精选电子好物", "为你推荐最新的数码产品，手机 / 电脑 / 耳机一站购齐", "#FF6A3C"),
            ("服饰焕新季", "发现当季流行穿搭，运动休闲、通勤正装随心选", "#FF9F0A"),
            ("品质家居", "打造舒适居家空间，家电 / 家具 / 收纳等一应俱全", "#17A2B8"),
        ]

        for title, subtitle, color in banners:
            # 外层页面保持透明背景，只放一个居中的彩色卡片，更像淘宝的运营位
            page = QWidget()
            page.setStyleSheet("QWidget { background-color: transparent; }")

            page_layout = QHBoxLayout(page)
            page_layout.setContentsMargins(4, 4, 4, 4)
            page_layout.setSpacing(0)

            # 内部真正的彩色 Banner 卡片
            from PyQt6.QtWidgets import QFrame

            card = QFrame()
            card.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 10px;
            }}
            """)

            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(24, 18, 24, 18)
            card_layout.setSpacing(6)

            title_label = QLabel(title)
            title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 700;
                color: #FFFFFF;
            }
            """)

            subtitle_label = QLabel(subtitle)
            subtitle_label.setWordWrap(True)
            subtitle_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: rgba(255,255,255,0.92);
            }
            """)

            card_layout.addWidget(title_label)
            card_layout.addWidget(subtitle_label)
            card_layout.addStretch()

            # 左右预留少量留白，不让彩色块充满整个区域，看起来更轻盈
            page_layout.addSpacing(4)
            page_layout.addWidget(card)
            page_layout.addSpacing(4)

            self.banner_stack.addWidget(page)

        layout.addWidget(self.banner_stack)

        # 自动轮播定时器（无需鼠标交互）
        if not hasattr(self, "banner_timer"):
            self.banner_timer = QTimer(self)
            self.banner_timer.setInterval(4000)  # 4 秒切换一次
            self.banner_timer.timeout.connect(self._rotate_banner)
            self.banner_timer.start()

        return banner_widget

    def create_products_grid(self, parent_layout):
        """创建商品网格 - 现代化全宽布局 + 自适应列数"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(f"""
        QScrollArea {{
            border: none;
            background-color: {globals().get('SECONDARY_COLOR', '#FAFAFA')};
        }}
        QScrollArea QWidget {{
            background-color: transparent;
        }}
        """)

        # 商品容器
        self.products_container = QWidget()
        self.products_container.setStyleSheet(f"background-color: {globals().get('SECONDARY_COLOR', '#FAFAFA')};")
        # 监听尺寸变化，用于自适应列数布局
        self.products_container.installEventFilter(self)

        # 使用网格布局，自适应 3-5 列显示商品（间距略微收紧）
        self.products_grid = QGridLayout()
        self.products_grid.setSpacing(16)
        self.products_grid.setContentsMargins(10, 10, 10, 10)

        # 初始加载商品
        self.load_products()

        self.products_container.setLayout(self.products_grid)
        scroll_area.setWidget(self.products_container)

        parent_layout.addWidget(scroll_area)

    def _rotate_banner(self) -> None:
        """顶部 Banner 自动轮播"""
        stack = getattr(self, "banner_stack", None)
        if not stack:
            return

        count = stack.count()
        if count <= 1:
            return

        current = stack.currentIndex()
        stack.setCurrentIndex((current + 1) % count)

    def _calculate_grid_columns(self) -> int:
        """
        根据当前容器宽度计算自适应列数
        - 最少 3 列，最多 5 列
        """
        # 若容器还未布局好，使用窗口宽度做一次估算
        if not hasattr(self, "products_container") or self.products_container.width() <= 0:
            approx_width = max(self.width() - 200, 900)
        else:
            approx_width = self.products_container.width()

        # 单个卡片宽度（含间距），与 ProductCard 中的 setFixedSize 对齐
        card_width = 300
        spacing = self.products_grid.horizontalSpacing() or 20

        # 预留一些内边距
        available = max(approx_width - 60, 600)

        # 计算最大可容纳列数，并限制在 3-5 之间
        rough_cols = max(1, int(available // (card_width + spacing)))
        cols = max(3, min(5, rough_cols))
        return cols

    def load_products(self, products=None):
        """加载商品到网格 - 自适应 3-5 列布局"""
        # 清空现有商品
        self.clear_products_grid()

        # 使用提供的商品或默认商品
        products_to_show = products or self.sample_products
        self.current_products_list = products_to_show

        # 计算网格布局（自适应列数）
        max_cols = self._calculate_grid_columns()
        self.current_grid_cols = max_cols
        row = 0
        col = 0

        for product in products_to_show:
            card = ProductCard(product)
            card.clicked.connect(self.on_product_clicked)
            card.favorited.connect(self.on_product_favorited)

            self.products_grid.addWidget(card, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        # 更新商品数量显示
        self.product_count_label.setText(f"共 {len(products_to_show)} 件商品")

    def clear_products_grid(self):
        """清空商品网格"""
        while self.products_grid.count():
            child = self.products_grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def eventFilter(self, obj, event):
        """
        监听商品容器尺寸变化，动态调整网格列数

        说明：
            - 当窗口放大 / 缩小时，自动在 3 / 4 / 5 列之间平滑切换
            - 避免出现卡片“挤压折叠”或留白过多的问题
        """
        if obj is getattr(self, "products_container", None) and event.type() == QEvent.Type.Resize:
            if self.current_products_list:
                new_cols = self._calculate_grid_columns()
                if new_cols != self.current_grid_cols:
                    self.load_products(self.current_products_list)

        return super().eventFilter(obj, event)

    def generate_sample_products(self):
        """生成示例商品数据"""
        products = []

        # 电子产品
        electronics = [
            ("iPhone 15 Pro", "¥8999", "4.8", "苹果旗舰手机，A17 Pro芯片，专业级摄像头"),
            ("MacBook Pro 16寸", "¥19999", "4.9", "苹果专业笔记本，M3 Max芯片，超强性能"),
            ("iPad Air", "¥4799", "4.7", "苹果平板电脑，M2芯片，多任务处理"),
            ("Sony WH-1000XM5", "¥2999", "4.6", "索尼旗舰降噪耳机，Hi-Res音质"),
            ("Dell XPS 13", "¥8999", "4.5", "戴尔轻薄笔记本，13寸屏幕，Intel 13代处理器"),
        ]

        # 服装鞋包
        fashion = [
            ("Nike Air Max", "¥899", "4.4", "耐克经典跑鞋，舒适透气，时尚百搭"),
            ("Adidas Ultraboost", "¥1299", "4.6", "阿迪达斯旗舰跑鞋，Boost科技，专业运动"),
            ("Levi's牛仔裤", "¥399", "4.3", "李维斯经典牛仔裤，优质面料，耐穿耐洗"),
            ("Gucci手袋", "¥8999", "4.8", "古驰时尚手袋，精湛工艺，奢华气质"),
            ("H&M连衣裙", "¥199", "4.2", "H&M时尚连衣裙，简约设计，舒适面料"),
        ]

        # 家居用品
        home_goods = [
            ("Dyson吸尘器", "¥3999", "4.7", "戴森无绳吸尘器，强力吸力，智能控制"),
            ("Philips空气净化器", "¥1999", "4.5", "飞利浦空气净化器，HEPA滤网，除甲醛"),
            ("MUJI收纳箱", "¥89", "4.3", "无印良品收纳箱，简约设计，实用耐用"),
            ("IKEA书桌", "¥899", "4.4", "宜家学习桌，人体工学设计，稳固耐用"),
            ("Haier冰箱", "¥2999", "4.6", "海尔双门冰箱，大容量，节能省电"),
        ]

        all_products = electronics + fashion + home_goods

        for i, (title, price, rating, desc) in enumerate(all_products, 1):
            product = create_sample_product(i, title, price, rating, desc)
            products.append(product)

        return products

    def _product_to_card_data(self, product: Product) -> dict:
        """将后端 Product 模型转换为商品卡片展示所需的数据结构"""
        price = product.price if product.price is not None else 0.0
        rating = getattr(product, "rating", 0.0) or 0.0

        return {
            "id": product.product_id,
            "title": product.title or "商品",
            "price": f"¥{price:.2f}",
            "rating": f"{rating:.1f}",
            "description": product.description or "",
            "image_path": product.image_path or "",
            "category": product.category or "",
        }

    def load_home_recommendations(self):
        """
        尝试从推荐引擎加载首页个性化推荐。
        若后端或嵌入不可用，则保持使用示例商品。
        """
        if not self.rec_engine:
            self.backend_available = False
            return

        try:
            product_ids = self.rec_engine.generate_recommendations(
                self.current_user_id, top_k=20
            )
            if not product_ids:
                self.backend_available = False
                return

            products: list[dict] = []
            for pid in product_ids:
                try:
                    p = Product.get_by_id(pid)
                    if p:
                        products.append(self._product_to_card_data(p))
                except Exception as e:
                    logger.warning(f"加载商品 {pid} 失败: {e}")

            if products:
                self.home_recommendations = products
                self.backend_available = True
                # 直接在首页展示个性化推荐
                self.load_products(self.home_recommendations)
            else:
                self.backend_available = False

        except Exception as e:
            logger.warning(f"加载首页个性化推荐失败，将使用示例数据: {e}")
            self.backend_available = False

    def on_nav_item_changed(self, current, previous):
        """导航项改变事件（当前 UI 未使用 QListWidget 导航，保留以兼容旧布局）"""
        if not current:
            return
 
        category_name = current.data(Qt.ItemDataRole.UserRole)
 
        # 映射分类名称到类别
        category_map = {
            "首页推荐": "all",
            "电子产品": "electronics",
            "服装鞋包": "fashion",
            "家居用品": "home",
            "图书文具": "books",
            "食品饮料": "food",
            "我的收藏": "favorites",
            "推荐历史": "history",
            "偏好设置": "settings",
        }
 
        category = category_map.get(category_name, "all")
        self.current_category = category
        self.filter_products_by_category(category)

    def filter_products_by_category(self, category):
        """按分类过滤商品"""
        if category == "all":
            # 首页优先展示个性化推荐（如果可用）
            if getattr(self, "backend_available", False) and self.home_recommendations:
                filtered_products = self.home_recommendations
            else:
                filtered_products = self.sample_products
        elif category == "electronics":
            filtered_products = [p for p in self.sample_products if p['id'] <= 5]
        elif category == "fashion":
            filtered_products = [p for p in self.sample_products if 6 <= p['id'] <= 10]
        elif category == "home":
            filtered_products = [p for p in self.sample_products if 11 <= p['id'] <= 15]
        elif category == "favorites":
            # 模拟收藏的商品（实际应用中从数据库获取）
            filtered_products = random.sample(self.sample_products, 3)
        elif category == "history":
            # 模拟浏览历史（实际应用中从数据库获取）
            filtered_products = random.sample(self.sample_products, 5)
        else:
            filtered_products = self.sample_products

        self.load_products(filtered_products)

    def search_products(self):
        """搜索商品"""
        query = self.search_input.text().strip().lower()
        if not query:
            # 恢复当前分类的默认列表
            self.filter_products_by_category(self.current_category)
            return

        # 根据当前来源选择搜索列表
        base_list = (
            self.home_recommendations
            if getattr(self, "backend_available", False)
            and self.current_category == "all"
            and self.home_recommendations
            else self.sample_products
        )

        # 简单的关键词搜索
        filtered_products = [
            product
            for product in base_list
            if query in product.get("title", "").lower()
            or query in product.get("description", "").lower()
        ]

        self.load_products(filtered_products)

    def refresh_products(self):
        """刷新商品列表"""
        # 按当前分类刷新
        self.filter_products_by_category(self.current_category)
        QMessageBox.information(self, "提示", "商品列表已刷新")

    def on_product_clicked(self, product_data):
        """商品点击事件"""
        QMessageBox.information(
            self,
            "商品详情",
            f"商品：{product_data['title']}\n"
            f"价格：{product_data['price']}\n"
            f"评分：{product_data['rating']} ⭐\n\n"
            f"描述：{product_data['description']}"
        )

    def on_product_favorited(self, product_data):
        """商品收藏事件"""
        print(f"用户 {self.current_user} 收藏了商品：{product_data['title']}")

        # 记录到推荐引擎（如果后端可用）
        if self.rec_engine:
            try:
                product_id = str(
                    product_data.get("id") or product_data.get("product_id")
                )
                self.rec_engine.update_user_profile(
                    user_id=self.current_user_id,
                    product_id=product_id,
                    action_type="favorite",
                )
            except ModelError as e:
                logger.warning(f"记录收藏行为失败（模型错误）: {e}")
            except Exception as e:
                logger.warning(f"记录收藏行为失败: {e}")

    def show_stats_panel(self):
        """
        兼容旧接口：切换到统计大屏页面

        说明：
            - 按新设计规范，不再使用独立弹窗作为主统计页面
            - 这里直接委托给顶部 Navigation 的统计 Tab
        """
        if hasattr(self, "navigation"):
            self.navigation._on_tab_clicked(1)

    def on_category_clicked(self, category):
        """分类按钮点击事件"""
        self.current_category = category
        self.filter_products_by_category(category)

    def logout(self):
        """登出"""
        from PyQt6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self, '确认登出',
            '确定要登出吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.close()
            # 这里可以添加返回登录界面的逻辑

    def connect_signals(self):
        """连接信号"""
        # 当前分类切换主要通过顶部导航按钮 `on_category_clicked` 处理
        # 预留接口：如果后续重新启用 QListWidget 导航，可在此统一连接信号
        return


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    main_window = MainWindow("admin")
    main_window.show()
    sys.exit(app.exec())
