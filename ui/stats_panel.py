"""
统计面板组件
显示推荐系统的数据统计和可视化图表
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QGridLayout, QGraphicsDropShadowEffect,
    QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
import random

from ui.styles import (
    STATS_PANEL_STYLE, BORDER_COLOR,
    PRIMARY_COLOR, SECONDARY_COLOR, TEXT_COLOR, LIGHT_TEXT
)


class StatsPanel(QWidget):
    """统计面板组件 - 可嵌入主界面的统计大屏基础类"""

    def __init__(self, parent=None):
        super().__init__(parent)
        # 使用磨砂卡片风格（稍带冷色渐变，避免整页纯白）
        self.setStyleSheet(STATS_PANEL_STYLE)

        # 添加阴影效果，模拟 Fluent 亚克力卡片的悬浮感
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 12)
        self.setGraphicsEffect(shadow)

        self.init_ui()


class StatDashboard(StatsPanel):
    """
    企业级数据可视化大屏组件

    说明：
        - 适配主界面中的 QStackedWidget，用于构建「统计大屏」页面
        - 目前直接复用 StatsPanel 的实现，后续可以在此类中扩展企业定制逻辑
    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def init_ui(self):
        """
        初始化界面 - 多模块数据分析大屏

        结构：
            - 顶部标题 + 时间/场景筛选
            - 滚动区域内按模块纵向排布：
                1) 基础概览
                2) 用户行为与推荐漏斗
                3) 推荐效果对比
                4) 多模态与模型分析
                5) 异常监控
        """
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 顶部标题与全局筛选
        header_layout = QHBoxLayout()

        title_block = QVBoxLayout()
        title_row = QHBoxLayout()
        title_icon = QLabel("📊")
        title_icon.setStyleSheet("font-size: 24px;")
        title_label = QLabel("多模态推荐数据分析大屏")
        title_label.setStyleSheet(f"""
        QLabel {{
            font-size: 20px;
            font-weight: bold;
            color: {TEXT_COLOR};
        }}
        """)
        title_row.addWidget(title_icon)
        title_row.addWidget(title_label)
        title_row.addStretch()

        subtitle_label = QLabel("全局监控推荐请求、用户行为、多模态贡献与异常风险")
        subtitle_label.setStyleSheet(f"""
        QLabel {{
            font-size: 11px;
            color: {LIGHT_TEXT};
        }}
        """)

        title_block.addLayout(title_row)
        title_block.addWidget(subtitle_label)
        header_layout.addLayout(title_block)

        header_layout.addStretch()

        # 时间范围与场景筛选（占位，后续可接真实数据）
        time_filter = QComboBox()
        time_filter.addItems(["近7天", "近30天", "今日", "昨日"])
        time_filter.setCurrentIndex(0)
        time_filter.setFixedHeight(28)
        time_filter.setStyleSheet(f"""
        QComboBox {{
            background-color: #FFFFFF;
            border-radius: 14px;
            padding: 2px 10px;
            border: 1px solid {BORDER_COLOR};
            font-size: 11px;
            color: {TEXT_COLOR};
            min-width: 96px;
        }}
        QComboBox::drop-down {{
            border: none;
        }}
        """)

        scene_filter = QComboBox()
        scene_filter.addItems(["全部场景", "首页推荐", "详情页推荐", "购物车推荐"])
        scene_filter.setCurrentIndex(0)
        scene_filter.setFixedHeight(28)
        scene_filter.setStyleSheet(time_filter.styleSheet())

        header_layout.addWidget(time_filter)
        header_layout.addWidget(scene_filter)

        layout.addLayout(header_layout)

        # 创建滚动区域承载各分析模块
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
        QScrollArea {
            border: none;
            background-color: transparent;
        }
        """)

        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(18)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # 1) 基础概览
        self.add_section_title(content_layout, "一、基础概览", "核心运营指标与用户画像")
        self.add_basic_stats(content_layout)
        self.add_overview_charts(content_layout)

        # 2) 用户行为与推荐漏斗
        self.add_section_title(content_layout, "二、用户行为与推荐漏斗", "曝光-点击-加购-下单全链路转化")
        self.add_behavior_section(content_layout)

        # 3) 推荐效果对比
        self.add_section_title(content_layout, "三、推荐效果对比", "时间/场景维度下的效果对比")
        self.add_effect_compare_section(content_layout)

        # 4) 多模态与模型分析
        self.add_section_title(content_layout, "四、多模态与模型分析", "多模态特征贡献与模型版本表现")
        self.add_multimodal_section(content_layout)

        # 5) 异常监控
        self.add_section_title(content_layout, "五、异常监控", "关键指标异常波动与事件列表")
        self.add_anomaly_section(content_layout)

        content_widget.setLayout(content_layout)
        scroll_area.setWidget(content_widget)

        layout.addWidget(scroll_area)
        self.setLayout(layout)

    def add_section_title(self, layout: QVBoxLayout, title: str, subtitle: str) -> None:
        """模块标题行"""
        wrapper = QWidget()
        h = QHBoxLayout(wrapper)
        h.setContentsMargins(0, 8, 0, 4)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
        QLabel {{
            font-size: 14px;
            font-weight: 600;
            color: {TEXT_COLOR};
        }}
        """)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet(f"""
        QLabel {{
            font-size: 11px;
            color: {LIGHT_TEXT};
        }}
        """)

        text_block = QVBoxLayout()
        text_block.setContentsMargins(0, 0, 0, 0)
        text_block.setSpacing(2)
        text_block.addWidget(title_label)
        text_block.addWidget(subtitle_label)

        h.addLayout(text_block)
        h.addStretch()

        layout.addWidget(wrapper)

    def add_basic_stats(self, layout):
        """添加基础概览中的核心统计卡片"""
        # 统计卡片网格 - 2x2 布局
        grid_layout = QGridLayout()
        grid_layout.setSpacing(16)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        # 统计项目数据（模拟数据）
        stats_data = [
            ("今日推荐", "1,247", "#4A90E2"),
            ("点击率", "23.5%", "#28a745"),
            ("收藏数", "89", "#FFC107"),
            ("用户活跃", "456", "#FF6B6B"),
        ]

        for i, (label, value, color) in enumerate(stats_data):
            card = self.create_stat_card(label, value, color)
            grid_layout.addWidget(card, i // 2, i % 2)

        layout.addLayout(grid_layout)

    def create_stat_card(self, label, value, color):
        """创建统计卡片 - 现代化设计"""
        card = QFrame()
        # 不固定宽度，允许在 2x2 网格中自适应拉伸（去掉 hover 动画，保持静态大屏风格）
        card.setMinimumHeight(110)
        card.setStyleSheet(f"""
        QFrame {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                       stop:0 {color}22,
                                       stop:1 {color}05);
            border: 1px solid {color}40;
            border-radius: 12px;
        }}
        """)

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(15, 15, 15, 15)
        card_layout.setSpacing(8)

        # 数值标签
        value_label = QLabel(value)
        value_label.setStyleSheet(f"""
        QLabel {{
            font-size: 24px;
            font-weight: bold;
            color: {color};
        }}
        """)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 文本标签
        text_label = QLabel(label)
        text_label.setStyleSheet(f"""
        QLabel {{
            font-size: 13px;
            color: {LIGHT_TEXT};
            font-weight: 500;
        }}
        """)
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_layout.addWidget(value_label)
        card_layout.addWidget(text_label)
        card.setLayout(card_layout)

        return card

    def add_charts(self, layout):
        """添加图表"""
        # 使用 2x2 网格布局，营造数据大屏感
        grid = QGridLayout()
        grid.setSpacing(16)
        grid.setContentsMargins(0, 0, 0, 0)

        # 左上：点击率趋势
        ctr_chart = self.create_ctr_chart()
        grid.addWidget(ctr_chart, 0, 0)

        # 右上：用户偏好分布
        preference_chart = self.create_preference_chart()
        grid.addWidget(preference_chart, 0, 1)

        # 下方：TOP10 排行（跨两列）
        top_products_chart = self.create_top_products_chart()
        grid.addWidget(top_products_chart, 1, 0, 1, 2)

        layout.addLayout(grid)

    def create_ctr_chart(self):
        """创建点击率趋势图 - 现代化设计"""
        chart_widget = QWidget()
        chart_widget.setMinimumHeight(260)
        chart_widget.setStyleSheet(f"""
        QWidget {{
            background-color: #FFFFFF;
            border-radius: 12px;
            border: 1px solid {BORDER_COLOR};
        }}
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("📈 点击率趋势分析 (近7天)")
        title.setStyleSheet(f"""
        QLabel {{
            font-size: 16px;
            font-weight: bold;
            color: {TEXT_COLOR};
            margin-bottom: 10px;
        }}
        """)
        layout.addWidget(title)

        # 创建matplotlib图表
        figure = plt.Figure(figsize=(6, 3), dpi=96)
        canvas = FigureCanvas(figure)

        ax = figure.add_subplot(111)

        # 生成示例数据
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        ctr_values = [22.1, 23.5, 21.8, 24.2, 25.1, 23.8, 24.6]

        ax.plot(days, ctr_values, marker='o', linewidth=2, markersize=6, color='#4A90E2')
        ax.fill_between(days, ctr_values, alpha=0.3, color='#4A90E230')
        ax.set_ylabel('CTR (%)')
        ax.set_title('Daily CTR Trend', fontsize=12)
        ax.grid(True, alpha=0.25, linestyle="--")
        figure.tight_layout()

        layout.addWidget(canvas)
        chart_widget.setLayout(layout)

        return chart_widget

    def create_preference_chart(self):
        """创建用户偏好分布图 - 现代化设计"""
        chart_widget = QWidget()
        chart_widget.setMinimumHeight(260)
        chart_widget.setStyleSheet(f"""
        QWidget {{
            background-color: white;
            border-radius: 12px;
            border: 1px solid {BORDER_COLOR};
        }}
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("🥧 用户偏好分布")
        title.setStyleSheet(f"""
        QLabel {{
            font-size: 16px;
            font-weight: bold;
            color: {TEXT_COLOR};
            margin-bottom: 10px;
        }}
        """)
        layout.addWidget(title)

        # 创建matplotlib图表
        figure = plt.Figure(figsize=(6, 3), dpi=96)
        canvas = FigureCanvas(figure)

        ax = figure.add_subplot(111)

        # 示例数据
        categories = ['电子产品', '服装鞋包', '家居用品', '图书文具', '食品饮料', '其他']
        preferences = [35, 25, 15, 10, 10, 5]
        colors = ['#4A90E2', '#28a745', '#FFC107', '#FF6B6B', '#9C27B0', '#607D8B']

        wedges, texts, autotexts = ax.pie(
            preferences,
            labels=categories,
            autopct='%1.1f%%',
            colors=colors,
            startangle=120,
            wedgeprops=dict(width=0.55, edgecolor='white'),
            pctdistance=0.8
        )
        for text in texts:
            text.set_fontsize(9)
        for autotext in autotexts:
            autotext.set_color("white")
            autotext.set_fontsize(9)

        ax.set_title('User Preferences Distribution', fontsize=12)
        figure.tight_layout()

        layout.addWidget(canvas)
        chart_widget.setLayout(layout)

        return chart_widget

    def create_top_products_chart(self):
        """创建热门商品Top10图表 - 现代化设计"""
        chart_widget = QWidget()
        chart_widget.setMinimumHeight(300)
        chart_widget.setStyleSheet(f"""
        QWidget {{
            background-color: white;
            border-radius: 12px;
            border: 1px solid {BORDER_COLOR};
        }}
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("🏆 热门商品TOP10排行")
        title.setStyleSheet(f"""
        QLabel {{
            font-size: 16px;
            font-weight: bold;
            color: {TEXT_COLOR};
            margin-bottom: 10px;
        }}
        """)
        layout.addWidget(title)

        # 创建matplotlib图表
        figure = plt.Figure(figsize=(6, 3.5), dpi=96)
        canvas = FigureCanvas(figure)

        ax = figure.add_subplot(111)

        # 示例数据
        products = ['iPhone 15', 'MacBook Pro', 'AirPods', 'iPad Air', 'Apple Watch',
                   'Nike鞋子', 'Adidas外套', 'Sony耳机', 'Dell笔记本', '华为手机']
        scores = [95, 87, 82, 78, 75, 72, 68, 65, 62, 58]

        y_pos = np.arange(len(products))
        ax.barh(y_pos, scores, color='#4A90E2', alpha=0.7)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(products, fontsize=8)
        ax.set_xlabel('热度分数')
        ax.set_title('Top 10 Popular Products', fontsize=12)
        ax.grid(True, alpha=0.3, axis='x')

        layout.addWidget(canvas)
        chart_widget.setLayout(layout)

        return chart_widget

    def add_overview_charts(self, layout: QVBoxLayout) -> None:
        """基础概览图表：请求/点击趋势 + 用户画像分布"""
        row = QHBoxLayout()
        row.setSpacing(16)

        traffic_chart = self.create_traffic_chart()
        traffic_chart.setMinimumWidth(420)
        row.addWidget(traffic_chart, 3)

        profile_chart = self.create_user_profile_chart()
        profile_chart.setMinimumWidth(360)
        row.addWidget(profile_chart, 2)

        wrapper = QWidget()
        wrapper.setLayout(row)
        layout.addWidget(wrapper)

    def create_traffic_chart(self):
        """创建推荐请求 & 点击趋势图（基础概览）"""
        chart_widget = QWidget()
        chart_widget.setMinimumHeight(260)
        chart_widget.setStyleSheet(f"""
        QWidget {{
            background-color: #FFFFFF;
            border-radius: 12px;
            border: 1px solid {BORDER_COLOR};
        }}
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("📈 推荐请求 & 点击趋势 (近7天)")
        title.setStyleSheet(f"""
        QLabel {{
            font-size: 16px;
            font-weight: bold;
            color: {TEXT_COLOR};
            margin-bottom: 10px;
        }}
        """)
        layout.addWidget(title)

        figure = plt.Figure(figsize=(6, 3), dpi=96)
        canvas = FigureCanvas(figure)
        ax = figure.add_subplot(111)

        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        requests = [1200, 1350, 1280, 1420, 1550, 1600, 1500]
        clicks = [260, 290, 280, 320, 360, 370, 350]

        ax2 = ax.twinx()

        ax.bar(days, requests, color='#E5F1FF', edgecolor='#4A90E2', alpha=0.8, label='推荐请求数')
        ax2.plot(days, clicks, marker='o', linewidth=2, markersize=6, color='#4A90E2', label='点击数')

        ax.set_ylabel('请求数')
        ax2.set_ylabel('点击数')
        ax.set_title('Traffic & Clicks', fontsize=12)
        ax.grid(True, alpha=0.25, linestyle="--")

        lines, labels = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax2.legend(lines + lines2, labels + labels2, loc='upper left', fontsize=8)

        figure.tight_layout()

        layout.addWidget(canvas)
        chart_widget.setLayout(layout)

        return chart_widget

    def create_user_profile_chart(self):
        """创建用户画像分布（环形图）"""
        chart_widget = QWidget()
        chart_widget.setMinimumHeight(260)
        chart_widget.setStyleSheet(f"""
        QWidget {{
            background-color: #FFFFFF;
            border-radius: 12px;
            border: 1px solid {BORDER_COLOR};
        }}
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("👥 用户分群画像")
        title.setStyleSheet(f"""
        QLabel {{
            font-size: 16px;
            font-weight: bold;
            color: {TEXT_COLOR};
            margin-bottom: 10px;
        }}
        """)
        layout.addWidget(title)

        figure = plt.Figure(figsize=(4, 3), dpi=96)
        canvas = FigureCanvas(figure)
        ax = figure.add_subplot(111)

        segments = ['新用户', '老用户', '高价值用户', '沉睡用户']
        values = [30, 45, 15, 10]
        colors = ['#4A90E2', '#52C41A', '#FAAD14', '#9C27B0']

        wedges, texts, autotexts = ax.pie(
            values,
            labels=segments,
            autopct='%1.1f%%',
            colors=colors,
            startangle=120,
            wedgeprops=dict(width=0.55, edgecolor='white'),
            pctdistance=0.8
        )
        for text in texts:
            text.set_fontsize(8)
        for autotext in autotexts:
            autotext.set_color("white")
            autotext.set_fontsize(8)

        ax.set_title('User Segments Distribution', fontsize=11)
        figure.tight_layout()

        layout.addWidget(canvas)
        chart_widget.setLayout(layout)

        return chart_widget

    def add_behavior_section(self, layout: QVBoxLayout) -> None:
        """用户行为 & 推荐漏斗模块"""
        row = QHBoxLayout()
        row.setSpacing(16)

        funnel = self.create_funnel_chart()
        funnel.setMinimumWidth(380)
        row.addWidget(funnel, 2)

        behavior = self.create_behavior_chart()
        behavior.setMinimumWidth(400)
        row.addWidget(behavior, 3)

        wrapper = QWidget()
        wrapper.setLayout(row)
        layout.addWidget(wrapper)

    def create_funnel_chart(self) -> QWidget:
        """推荐漏斗：曝光-点击-加购-下单"""
        chart_widget = QWidget()
        chart_widget.setMinimumHeight(260)
        chart_widget.setStyleSheet(f"""
        QWidget {{
            background-color: #FFFFFF;
            border-radius: 12px;
            border: 1px solid {BORDER_COLOR};
        }}
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("🔻 推荐转化漏斗")
        title.setStyleSheet(f"""
        QLabel {{
            font-size: 16px;
            font-weight: bold;
            color: {TEXT_COLOR};
            margin-bottom: 10px;
        }}
        """)
        layout.addWidget(title)

        figure = plt.Figure(figsize=(4, 3), dpi=96)
        canvas = FigureCanvas(figure)
        ax = figure.add_subplot(111)

        stages = ["曝光", "点击", "加购", "下单"]
        values = [10000, 2800, 1200, 600]
        percents = [f"{v / values[0] * 100:.1f}%" for v in values]

        y = np.arange(len(stages))
        colors = ['#4A90E2', '#5C9EF2', '#52C41A', '#3BAF1A']

        ax.barh(y, values, color=colors, alpha=0.9)
        ax.set_yticks(y)
        ax.set_yticklabels(stages)
        ax.invert_yaxis()
        ax.set_xlabel('人数 / 次数')
        ax.grid(axis='x', alpha=0.3, linestyle='--')

        for i, (v, p) in enumerate(zip(values, percents)):
            ax.text(v * 1.02, i, p, va='center', fontsize=9, color='#555555')

        ax.set_title('Recommendation Funnel', fontsize=11)
        figure.tight_layout()

        layout.addWidget(canvas)
        chart_widget.setLayout(layout)

        return chart_widget

    def create_behavior_chart(self) -> QWidget:
        """按用户分群的行为指标对比"""
        chart_widget = QWidget()
        chart_widget.setMinimumHeight(260)
        chart_widget.setStyleSheet(f"""
        QWidget {{
            background-color: #FFFFFF;
            border-radius: 12px;
            border: 1px solid {BORDER_COLOR};
        }}
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("📊 行为指标对比（分人群）")
        title.setStyleSheet(f"""
        QLabel {{
            font-size: 16px;
            font-weight: bold;
            color: {TEXT_COLOR};
            margin-bottom: 10px;
        }}
        """)
        layout.addWidget(title)

        figure = plt.Figure(figsize=(5, 3), dpi=96)
        canvas = FigureCanvas(figure)
        ax = figure.add_subplot(111)

        groups = ["新用户", "老用户", "高价值用户"]
        ctr = [0.18, 0.24, 0.32]
        cvr = [0.03, 0.06, 0.09]

        x = np.arange(len(groups))
        width = 0.35

        ax.bar(x - width / 2, [v * 100 for v in ctr], width, label='CTR(%)', color='#4A90E2')
        ax.bar(x + width / 2, [v * 100 for v in cvr], width, label='CVR(%)', color='#52C41A')

        ax.set_xticks(x)
        ax.set_xticklabels(groups)
        ax.set_ylabel('比率 (%)')
        ax.set_title('Behavior by Segment', fontsize=11)
        ax.legend(fontsize=8)
        ax.grid(axis='y', alpha=0.3, linestyle='--')

        figure.tight_layout()

        layout.addWidget(canvas)
        chart_widget.setLayout(layout)

        return chart_widget

    def add_effect_compare_section(self, layout: QVBoxLayout) -> None:
        """推荐效果对比模块"""
        row = QHBoxLayout()
        row.setSpacing(16)

        time_chart = self.create_effect_time_chart()
        row.addWidget(time_chart, 3)

        scene_chart = self.create_effect_scene_chart()
        row.addWidget(scene_chart, 2)

        wrapper = QWidget()
        wrapper.setLayout(row)
        layout.addWidget(wrapper)

        layout.addWidget(self.create_top_products_chart())

    def create_effect_time_chart(self) -> QWidget:
        """本期 vs 上期 CTR 时间对比"""
        chart_widget = QWidget()
        chart_widget.setMinimumHeight(260)
        chart_widget.setStyleSheet(f"""
        QWidget {{
            background-color: #FFFFFF;
            border-radius: 12px;
            border: 1px solid {BORDER_COLOR};
        }}
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("⏱ 时间维度效果对比（CTR）")
        title.setStyleSheet(f"""
        QLabel {{
            font-size: 16px;
            font-weight: bold;
            color: {TEXT_COLOR};
            margin-bottom: 10px;
        }}
        """)
        layout.addWidget(title)

        figure = plt.Figure(figsize=(5, 3), dpi=96)
        canvas = FigureCanvas(figure)
        ax = figure.add_subplot(111)

        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        last_week = [21.0, 22.5, 21.2, 23.0, 23.8, 22.9, 23.5]
        this_week = [22.1, 23.5, 21.8, 24.2, 25.1, 23.8, 24.6]

        ax.plot(days, last_week, marker='o', linestyle='--', color='#B0BEC5', label='上周 CTR')
        ax.plot(days, this_week, marker='o', linewidth=2, color='#4A90E2', label='本周 CTR')

        ax.set_ylabel('CTR (%)')
        ax.set_title('CTR Week-over-Week', fontsize=11)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.25, linestyle="--")

        figure.tight_layout()

        layout.addWidget(canvas)
        chart_widget.setLayout(layout)

        return chart_widget

    def create_effect_scene_chart(self) -> QWidget:
        """场景维度效果对比"""
        chart_widget = QWidget()
        chart_widget.setMinimumHeight(260)
        chart_widget.setStyleSheet(f"""
        QWidget {{
            background-color: #FFFFFF;
            border-radius: 12px;
            border: 1px solid {BORDER_COLOR};
        }}
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("🗂 场景 CTR/CVR 对比")
        title.setStyleSheet(f"""
        QLabel {{
            font-size: 16px;
            font-weight: bold;
            color: {TEXT_COLOR};
            margin-bottom: 10px;
        }}
        """)
        layout.addWidget(title)

        figure = plt.Figure(figsize=(4, 3), dpi=96)
        canvas = FigureCanvas(figure)
        ax = figure.add_subplot(111)

        scenes = ['首页', '详情页', '购物车', 'Push']
        ctr = [0.25, 0.21, 0.28, 0.18]
        cvr = [0.06, 0.05, 0.08, 0.04]

        x = np.arange(len(scenes))
        width = 0.35

        ax.bar(x - width / 2, [v * 100 for v in ctr], width, label='CTR(%)', color='#4A90E2')
        ax.bar(x + width / 2, [v * 100 for v in cvr], width, label='CVR(%)', color='#52C41A')

        ax.set_xticks(x)
        ax.set_xticklabels(scenes)
        ax.set_ylabel('比率 (%)')
        ax.set_title('Effect by Scene', fontsize=11)
        ax.legend(fontsize=8)
        ax.grid(axis='y', alpha=0.3, linestyle='--')

        figure.tight_layout()

        layout.addWidget(canvas)
        chart_widget.setLayout(layout)

        return chart_widget

    def add_multimodal_section(self, layout: QVBoxLayout) -> None:
        """多模态与模型分析模块"""
        row = QHBoxLayout()
        row.setSpacing(16)

        feature_chart = self.create_feature_importance_chart()
        row.addWidget(feature_chart, 3)

        coverage_chart = self.create_modality_coverage_chart()
        row.addWidget(coverage_chart, 2)

        wrapper = QWidget()
        wrapper.setLayout(row)
        layout.addWidget(wrapper)

    def create_feature_importance_chart(self) -> QWidget:
        """多模态特征重要性条形图"""
        chart_widget = QWidget()
        chart_widget.setMinimumHeight(260)
        chart_widget.setStyleSheet(f"""
        QWidget {{
            background-color: #FFFFFF;
            border-radius: 12px;
            border: 1px solid {BORDER_COLOR};
        }}
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("🧠 多模态特征重要性")
        title.setStyleSheet(f"""
        QLabel {{
            font-size: 16px;
            font-weight: bold;
            color: {TEXT_COLOR};
            margin-bottom: 10px;
        }}
        """)
        layout.addWidget(title)

        figure = plt.Figure(figsize=(5, 3), dpi=96)
        canvas = FigureCanvas(figure)
        ax = figure.add_subplot(111)

        features = ['图像向量', '文本向量', '行为序列', '用户画像', '统计特征']
        importance = [0.32, 0.28, 0.22, 0.10, 0.08]

        x = np.arange(len(features))
        ax.bar(x, importance, color='#4A90E2')
        ax.set_xticks(x)
        ax.set_xticklabels(features, rotation=15, ha='right', fontsize=8)
        ax.set_ylabel('重要性得分')
        ax.set_title('Feature Importance (示意)', fontsize=11)
        ax.grid(axis='y', alpha=0.3, linestyle='--')

        figure.tight_layout()

        layout.addWidget(canvas)
        chart_widget.setLayout(layout)

        return chart_widget

    def create_modality_coverage_chart(self) -> QWidget:
        """多模态特征覆盖率"""
        chart_widget = QWidget()
        chart_widget.setMinimumHeight(260)
        chart_widget.setStyleSheet(f"""
        QWidget {{
            background-color: #FFFFFF;
            border-radius: 12px;
            border: 1px solid {BORDER_COLOR};
        }}
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("📦 多模态特征覆盖率")
        title.setStyleSheet(f"""
        QLabel {{
            font-size: 16px;
            font-weight: bold;
            color: {TEXT_COLOR};
            margin-bottom: 10px;
        }}
        """)
        layout.addWidget(title)

        figure = plt.Figure(figsize=(4, 3), dpi=96)
        canvas = FigureCanvas(figure)
        ax = figure.add_subplot(111)

        modalities = ['有图片', '有文本', '有行为序列', '完整多模态']
        coverage = [0.95, 0.88, 0.72, 0.65]

        x = np.arange(len(modalities))
        ax.bar(x, [v * 100 for v in coverage], color='#52C41A')
        ax.set_xticks(x)
        ax.set_xticklabels(modalities, rotation=15, ha='right', fontsize=8)
        ax.set_ylabel('覆盖率 (%)')
        ax.set_ylim(0, 100)
        ax.set_title('Modality Coverage (示意)', fontsize=11)
        ax.grid(axis='y', alpha=0.3, linestyle='--')

        figure.tight_layout()

        layout.addWidget(canvas)
        chart_widget.setLayout(layout)

        return chart_widget

    def add_anomaly_section(self, layout: QVBoxLayout) -> None:
        """异常监控模块"""
        row = QHBoxLayout()
        row.setSpacing(16)

        anomaly_chart = self.create_anomaly_chart()
        row.addWidget(anomaly_chart, 3)

        anomaly_list = self.create_anomaly_list()
        row.addWidget(anomaly_list, 2)

        wrapper = QWidget()
        wrapper.setLayout(row)
        layout.addWidget(wrapper)

    def create_anomaly_chart(self) -> QWidget:
        """关键指标异常波动折线图"""
        chart_widget = QWidget()
        chart_widget.setMinimumHeight(260)
        chart_widget.setStyleSheet(f"""
        QWidget {{
            background-color: #FFFFFF;
            border-radius: 12px;
            border: 1px solid {BORDER_COLOR};
        }}
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("⚠ CTR 异常监控（示意）")
        title.setStyleSheet(f"""
        QLabel {{
            font-size: 16px;
            font-weight: bold;
            color: {TEXT_COLOR};
            margin-bottom: 10px;
        }}
        """)
        layout.addWidget(title)

        figure = plt.Figure(figsize=(5, 3), dpi=96)
        canvas = FigureCanvas(figure)
        ax = figure.add_subplot(111)

        hours = np.arange(0, 24)
        base_ctr = 24 + 2 * np.sin(hours / 24 * 2 * np.pi)
        noise = np.random.normal(0, 0.4, size=len(hours))
        ctr = base_ctr + noise

        anomaly_indices = [10, 19]
        ctr[anomaly_indices[0]] -= 6
        ctr[anomaly_indices[1]] -= 5

        ax.plot(hours, ctr, color='#4A90E2', linewidth=2, label='CTR')
        ax.set_xlabel('小时')
        ax.set_ylabel('CTR (%)')
        ax.grid(True, alpha=0.25, linestyle='--')
        ax.set_title('CTR Realtime Monitoring', fontsize=11)

        ax.scatter(
            hours[anomaly_indices],
            ctr[anomaly_indices],
            color='#FF4D4F',
            s=40,
            zorder=5,
            label='异常'
        )
        for idx in anomaly_indices:
            ax.text(
                hours[idx],
                ctr[idx] - 2,
                "异常",
                color='#FF4D4F',
                fontsize=8,
                ha='center'
            )

        ax.legend(fontsize=8, loc='lower right')
        figure.tight_layout()

        layout.addWidget(canvas)
        chart_widget.setLayout(layout)

        return chart_widget

    def create_anomaly_list(self) -> QWidget:
        """异常事件列表卡片（示意数据）"""
        container = QWidget()
        container.setMinimumHeight(260)

        v = QVBoxLayout()
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)

        title = QLabel("📋 异常事件列表（示例）")
        title.setStyleSheet(f"""
        QLabel {{
            font-size: 14px;
            font-weight: bold;
            color: {TEXT_COLOR};
        }}
        """)
        v.addWidget(title)

        anomalies = [
            ("高", "CTR 突然下降", "10:00 - 10:15", "详情页推荐", "模型更新后点击率低于历史均值 3σ"),
            ("中", "请求延迟升高", "19:00 - 19:30", "首页推荐", "晚高峰 QPS 飙升，检索延迟增加"),
            ("低", "数据缺失预警", "昨日", "多模态特征", "部分新上架商品缺失图片向量"),
        ]

        level_color = {
            "高": "#FF4D4F",
            "中": "#FAAD14",
            "低": "#52C41A",
        }

        for level, title_text, time_text, scene, desc in anomalies:
            card = QFrame()
            card.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border-radius: 10px;
                border: 1px solid {BORDER_COLOR};
            }}
            """)
            card_layout = QVBoxLayout()
            card_layout.setContentsMargins(10, 8, 10, 8)
            card_layout.setSpacing(4)

            top_row = QHBoxLayout()
            level_label = QLabel(level)
            level_label.setFixedWidth(26)
            level_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            level_label.setStyleSheet(f"""
            QLabel {{
                font-size: 11px;
                font-weight: bold;
                color: white;
                border-radius: 9px;
                padding: 2px 4px;
                background-color: {level_color.get(level, '#999999')};
            }}
            """)

            title_label = QLabel(title_text)
            title_label.setStyleSheet(f"""
            QLabel {{
                font-size: 12px;
                font-weight: 500;
                color: {TEXT_COLOR};
            }}
            """)

            top_row.addWidget(level_label)
            top_row.addSpacing(6)
            top_row.addWidget(title_label)
            top_row.addStretch()

            meta_label = QLabel(f"{time_text} · {scene}")
            meta_label.setStyleSheet(f"""
            QLabel {{
                font-size: 10px;
                color: {LIGHT_TEXT};
            }}
            """)

            desc_label = QLabel(desc)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet(f"""
            QLabel {{
                font-size: 10px;
                color: {LIGHT_TEXT};
            }}
            """)

            card_layout.addLayout(top_row)
            card_layout.addWidget(meta_label)
            card_layout.addWidget(desc_label)
            card.setLayout(card_layout)

            v.addWidget(card)

        v.addStretch()
        container.setLayout(v)

        return container

    def update_stats(self, new_data=None):
        """更新统计数据"""
        # 这里可以根据实际数据更新统计信息
        if new_data:
            print(f"更新统计数据: {new_data}")
        # 重新绘制图表
        self.update()


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    stats_panel = StatsPanel()

    # 测试窗口
    from PyQt6.QtWidgets import QVBoxLayout, QWidget
    test_window = QWidget()
    test_window.setWindowTitle("统计面板测试")
    test_window.setFixedSize(400, 800)

    layout = QVBoxLayout()
    layout.addWidget(stats_panel)
    test_window.setLayout(layout)

    test_window.show()
    sys.exit(app.exec())
