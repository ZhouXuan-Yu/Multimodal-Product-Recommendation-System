"""模块五：PyQt5 管理监控大屏（侧边栏 + 顶部状态栏 + 仪表盘布局）。"""

from __future__ import annotations

import math
import os
import sys
from typing import Any, Dict

from PyQt5.QtWidgets import QApplication

# 一定要在导入 pyqtgraph / 其他 Qt 组件之前就创建 QApplication
# 避免这些库在 import 过程中提前构造 QWidget 导致
# “QWidget: Must construct a QApplication before a QWidget”
_qt_app = QApplication.instance()
if _qt_app is None:
    _qt_app = QApplication(sys.argv)

import pyqtgraph as pg
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# 兼容两种运行方式：
# 1）在项目根目录：python -m module_admin_pyqt.main_window
# 2）在当前目录：python main_window.py
try:
    from module_admin_pyqt.local_data_monitor import (
        compute_daily_activity,
        compute_llm_usage,
        compute_offline_eval,
        compute_product_stats,
        compute_recommendation_effect,
        compute_user_table,
    )
except ModuleNotFoundError:
    from local_data_monitor import (
        compute_daily_activity,
        compute_llm_usage,
        compute_offline_eval,
        compute_product_stats,
        compute_recommendation_effect,
        compute_user_table,
    )


class DataWorker(QThread):
    """后台线程：异步读取本地 JSON/日志，避免 UI 卡顿。"""

    done = pyqtSignal(dict)

    def run(self) -> None:
        payload: Dict[str, Any] = {
            "product_stats": compute_product_stats(),
            "llm_stats": compute_llm_usage(),
            "users": compute_user_table(),
            "effect_stats": compute_recommendation_effect(),
            "daily_activity": compute_daily_activity(),
            "offline_eval": compute_offline_eval(),
        }
        self.done.emit(payload)


class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("管理员监控大屏")
        self.resize(1360, 860)

        # 全局配色给到 pyqtgraph（浅色学术风）
        pg.setConfigOption("background", "#FFFFFF")
        pg.setConfigOption("foreground", "#111827")

        # 加载外部 QSS 皮肤（如果存在）
        self._load_stylesheet()

        root = QWidget()
        self.setCentralWidget(root)

        # 顶层：左右分栏布局（左侧导航 + 右侧主内容），使用 QSplitter 便于拖拽调整宽度
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        splitter = QSplitter()
        splitter.setObjectName("RootSplitter")
        root_layout.addWidget(splitter)

        # ======================
        # 左侧导航栏（品牌 + 按钮）
        # ======================
        sidebar_container = QWidget()
        sidebar_container.setObjectName("Sidebar")
        sidebar = QVBoxLayout(sidebar_container)
        sidebar.setContentsMargins(16, 16, 16, 16)
        sidebar.setSpacing(12)

        self.brand_label = QLabel("Aprogress 管理后台")
        self.brand_label.setObjectName("BrandLabel")
        self.brand_label.setWordWrap(True)
        sidebar.addWidget(self.brand_label)

        self.overview_btn = QPushButton("总览仪表盘")
        self.overview_btn.setObjectName("NavButton")
        self.overview_btn.setCheckable(True)
        self.overview_btn.setChecked(True)
        sidebar.addWidget(self.overview_btn)

        # 预留其它导航入口
        self.nav_placeholder = QLabel("（后续可接入：模型监控 / 推荐实验等）")
        self.nav_placeholder.setObjectName("NavHint")
        self.nav_placeholder.setWordWrap(True)
        sidebar.addWidget(self.nav_placeholder)

        sidebar.addStretch()

        # 底部刷新按钮
        self.refresh_btn = QPushButton("刷新数据")
        self.refresh_btn.setObjectName("PrimaryButton")
        self.refresh_btn.clicked.connect(self.refresh)
        sidebar.addWidget(self.refresh_btn)

        # ======================
        # 右侧主内容区（Bento Grid 卡片布局）
        # ======================
        main_container = QWidget()
        main_container.setObjectName("MainArea")
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 顶部：4 个极简统计 Tile（学术智库风）
        tiles_card = QFrame()
        tiles_card.setObjectName("TilesCard")
        tiles_layout = QGridLayout(tiles_card)
        tiles_layout.setContentsMargins(12, 12, 12, 12)
        tiles_layout.setSpacing(12)

        def _build_tile(title: str) -> QLabel:
            tile = QFrame()
            tile.setObjectName("StatTile")
            v = QVBoxLayout(tile)
            label = QLabel(title)
            label.setObjectName("TileLabel")
            value = QLabel("--")
            value.setObjectName("TileValue")
            v.addWidget(label)
            v.addWidget(value)
            v.addStretch()
            col = tiles_layout.columnCount()
            tiles_layout.addWidget(tile, 0, col)
            return value

        self.tile_gmv = _build_tile("GMV 总成交额")
        self.tile_orders = _build_tile("订单总数")
        self.tile_active_users = _build_tile("活跃用户数")
        self.tile_ctr = _build_tile("CTR 点击率")

        main_layout.addWidget(tiles_card)

        # 中部：非对称 Bento Grid（左趋势面积图略收窄 + 右侧推荐效果 & 待办事项）
        middle_card = QFrame()
        middle_card.setObjectName("MiddleCard")
        middle_layout = QHBoxLayout(middle_card)
        middle_layout.setContentsMargins(12, 12, 12, 12)
        middle_layout.setSpacing(12)

        # 左：趋势面积图（活跃度 / 下单趋势）
        self.trend_plot = pg.PlotWidget(title="近 30 天趋势分析")
        self.trend_plot.setBackground("#FFFFFF")
        # 轻量坐标轴说明，增强“专业感”
        self.trend_plot.setLabel("left", "行为 / 订单数量")
        self.trend_plot.setLabel("bottom", "日期")
        # 向左略微收窄，为右侧指标区域腾出更多空间
        middle_layout.addWidget(self.trend_plot, 2)

        # 右：推荐效果 & 工作待办（上下堆叠）
        right_middle_layout = QVBoxLayout()

        metrics_title = QLabel("推荐效果 & 业务指标")
        metrics_title.setObjectName("SectionTitle")
        right_middle_layout.addWidget(metrics_title)

        self.metrics_table = QTableWidget(0, 2)
        self.metrics_table.setHorizontalHeaderLabels(["指标", "数值"])
        self._init_table_common(self.metrics_table)
        right_middle_layout.addWidget(self.metrics_table, 1)

        todo_title = QLabel("工作待办事项")
        todo_title.setObjectName("SectionTitle")
        right_middle_layout.addWidget(todo_title)

        self.todo_table = QTableWidget(0, 2)
        self.todo_table.setHorizontalHeaderLabels(["事项", "截止时间"])
        self._init_table_common(self.todo_table)
        right_middle_layout.addWidget(self.todo_table, 1)

        middle_layout.addLayout(right_middle_layout, 3)

        main_layout.addWidget(middle_card, 3)

        # 底部区域：核心用户画像（活动度 TOP）
        tables_card = QFrame()
        tables_card.setObjectName("TablesCard")
        bottom_layout = QVBoxLayout(tables_card)

        persona_title = QLabel("核心用户画像（活动度 TOP）")
        persona_title.setObjectName("SectionTitle")
        bottom_layout.addWidget(persona_title)

        self.user_table = QTableWidget(0, 4)
        self.user_table.setHorizontalHeaderLabels(["用户ID", "活跃度", "核心标签", "画像说明"])
        self._init_table_common(self.user_table)
        bottom_layout.addWidget(self.user_table)

        main_layout.addWidget(tables_card, 3)

        # 将左右 widget 加入 splitter，控制初始宽度比例
        splitter.addWidget(sidebar_container)
        splitter.addWidget(main_container)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self.worker: DataWorker | None = None
        self.refresh()

    # ----------------------
    # 辅助：加载 QSS / 初始化表格
    # ----------------------
    def _load_stylesheet(self) -> None:
        """从当前模块目录下加载 QSS 主题，不存在时走默认样式。"""
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            qss_path = os.path.join(base_dir, "admin_dashboard.qss")
        except Exception:
            return

        if os.path.exists(qss_path):
            try:
                with open(qss_path, "r", encoding="utf-8") as f:
                    self.setStyleSheet(f.read())
            except OSError:
                # 读取失败时忽略，保持默认样式
                pass

    def _init_table_common(self, table: QTableWidget) -> None:
        """统一配置表格的观感。"""
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        header = table.horizontalHeader()
        header.setStretchLastSection(True)
        table.verticalHeader().setVisible(False)

    def refresh(self) -> None:
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("刷新中...")
        self.worker = DataWorker()
        self.worker.done.connect(self.render_data)
        self.worker.start()

    def render_data(self, payload: dict[str, Any]) -> None:
        # 概览 summary：商品 + LLM 调用 + 推荐转化（中文文案）
        pstats = payload["product_stats"]
        lstats = payload["llm_stats"]
        estats = payload["effect_stats"]
        offline = payload.get("offline_eval") or {}
        summary_text = (
            "商品总数 {total} ｜ DeepSeek 调用 {calls} 次（≈ Token {tokens}）\n"
            "用户数 {users}（活跃 {active}）｜点击率 CTR {ctr:.1%} ｜ 转化率 CVR {cvr:.1%}"
        ).format(
            total=pstats.get("total", 0),
            calls=lstats.get("deepseek_calls", 0),
            tokens=lstats.get("estimated_tokens", 0),
            users=estats.get("total_users", 0),
            active=estats.get("active_users", 0),
            ctr=estats.get("ctr", 0.0),
            cvr=estats.get("cvr", 0.0),
        )

        # 用于底部说明 / 后续扩展，可以挂在某处辅助展示
        # 当前仅保留变量，避免 UI 过于拥挤
        _ = summary_text

        # 顶部 4 个 Tile 数据
        self.tile_gmv.setText(f"{estats.get('revenue', 0.0):.2f}")
        self.tile_orders.setText(str(estats.get("total_orders", 0)))
        self.tile_active_users.setText(str(estats.get("active_users", 0)))
        self.tile_ctr.setText(f"{estats.get('ctr', 0.0):.1%}")

        # 趋势面积图：活跃度 & 下单趋势（无网格线、无发光）
        daily = payload.get("daily_activity", [])
        self.trend_plot.clear()
        if daily:
            xs = list(range(len(daily)))
            events = [d.get("events", 0) for d in daily]
            orders = [d.get("orders", 0) for d in daily]
            days = [d.get("day", "") for d in daily]

            # 主色：深石板青（线）+ 鼠尾草绿（面积）
            pen_events = pg.mkPen("#2D3E50", width=2)  # 行为数：主色实线
            pen_orders = pg.mkPen("#6B8E23", width=2)  # 订单数：点缀色线

            # 行为数折线
            self.trend_plot.plot(xs, events, pen=pen_events, name="行为数")
            # 订单数面积图
            self.trend_plot.plot(
                xs,
                orders,
                pen=pen_orders,
                brush=pg.mkBrush(107, 142, 35, 40),  # 半透明鼠尾草绿，无发光
                fillLevel=0,
                name="订单数",
            )

            ax = self.trend_plot.getAxis("bottom")
            tick_step = max(1, len(days) // 8)
            ticks = [(i, days[i]) for i in range(0, len(days), tick_step)]
            ax.setTicks([ticks])
            # 去除网格线
            self.trend_plot.showGrid(x=False, y=False)

        # 推荐效果指标表（字段名统一中文）
        metrics_rows = [
            ("总用户数", estats.get("total_users", 0)),
            ("活跃用户数", estats.get("active_users", 0)),
            ("行为总数", estats.get("total_events", 0)),
            ("曝光 / 浏览次数", estats.get("views", 0)),
            ("点击次数", estats.get("clicks", 0)),
            ("下单行为次数", estats.get("purchases", 0)),
            ("订单总数", estats.get("total_orders", 0)),
            ("GMV / 总成交额", f"{estats.get('revenue', 0.0):.2f}"),
            ("平均客单价", f"{estats.get('avg_order_value', 0.0):.2f}"),
            ("CTR (点击率)", f"{estats.get('ctr', 0.0):.2%}"),
            ("CVR (转化率)", f"{estats.get('cvr', 0.0):.2%}"),
        ]
        self.metrics_table.setRowCount(len(metrics_rows))
        for i, (name, value) in enumerate(metrics_rows):
            self.metrics_table.setItem(i, 0, QTableWidgetItem(str(name)))
            self.metrics_table.setItem(i, 1, QTableWidgetItem(str(value)))

        # 用户画像表（标签可在此处做英文转中文映射），并附带一句话画像说明
        users = payload["users"]
        self.user_table.setRowCount(len(users))
        for i, row in enumerate(users):
            self.user_table.setItem(i, 0, QTableWidgetItem(str(row["user_id"])))
            self.user_table.setItem(i, 1, QTableWidgetItem(str(row["activity_score"])))
            core_tags = str(row["core_tags"])
            # 如后端返回英文标签，可在此扩展映射逻辑
            tag_map = {
                "high_value": "高价值用户",
                "new_user": "新用户",
                "churn_risk": "流失风险",
            }
            for en, zh in tag_map.items():
                core_tags = core_tags.replace(en, zh)
            self.user_table.setItem(i, 2, QTableWidgetItem(core_tags))

            persona_summary = str(row.get("persona_summary", "") or "")
            summary_item = QTableWidgetItem(persona_summary)
            # 在单元格中显示完整的一句话画像说明，同时通过 tooltip 保留完整文本
            summary_item.setToolTip(persona_summary)
            self.user_table.setItem(i, 3, summary_item)

        # 工作待办事项：根据当前数据给出几条运营 / 数据相关待办
        todo_rows = [
            ("复盘今日 CTR / CVR 异动", "今日"),
            ("检查高价值用户（活动度 TOP）运营触达情况", "本周内"),
            ("对低转化品类优化推荐策略", "本月内"),
        ]
        self.todo_table.setRowCount(len(todo_rows))
        for i, (task, deadline) in enumerate(todo_rows):
            self.todo_table.setItem(i, 0, QTableWidgetItem(task))
            self.todo_table.setItem(i, 1, QTableWidgetItem(deadline))

        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("刷新数据")


if __name__ == "__main__":
    # 复用前面全局创建 / 获取到的 QApplication 实例
    w = DashboardWindow()
    w.show()
    sys.exit(_qt_app.exec_())
