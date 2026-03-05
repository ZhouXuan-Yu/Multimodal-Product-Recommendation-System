"""模块五：PyQt5 管理监控大屏（侧边栏 + 顶部状态栏 + 仪表盘布局）。"""

from __future__ import annotations

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
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
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

        # 全局配色给到 pyqtgraph
        pg.setConfigOption("background", "#020617")  # deep dark
        pg.setConfigOption("foreground", "#e5e7eb")

        # 加载外部 QSS 皮肤（如果存在）
        self._load_stylesheet()

        root = QWidget()
        self.setCentralWidget(root)

        # 顶层：左右分栏布局（左侧导航 + 右侧主内容）
        root_layout = QHBoxLayout(root)

        # ======================
        # 左侧导航栏（品牌 + 按钮）
        # ======================
        sidebar = QVBoxLayout()

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
        # 右侧主内容区
        # ======================
        main = QVBoxLayout()

        # 顶部状态栏：摘要 + 最近更新时间占位
        top_bar = QHBoxLayout()

        self.title_label = QLabel("运营 & 推荐系统总览")
        self.title_label.setObjectName("TitleLabel")
        top_bar.addWidget(self.title_label)

        top_bar.addStretch()

        self.last_update_label = QLabel("最近刷新：--")
        self.last_update_label.setObjectName("SubStatusLabel")
        top_bar.addWidget(self.last_update_label)

        main.addLayout(top_bar)

        # 中部：summary 卡片 + 图表
        center_layout = QVBoxLayout()

        # 概览 summary
        self.summary_label = QLabel("加载中...")
        self.summary_label.setObjectName("SummaryLabel")
        self.summary_label.setWordWrap(True)
        center_layout.addWidget(self.summary_label)

        # 图表区域：两列布局
        charts_layout = QHBoxLayout()

        # 商品分类占比
        self.category_plot = pg.PlotWidget(title="商品分类占比（数量）")
        self.category_plot.setBackground("#020617")
        charts_layout.addWidget(self.category_plot, 1)

        # 近 30 天活跃度 / 下单趋势
        self.activity_plot = pg.PlotWidget(title="近 30 天活跃度与下单趋势")
        self.activity_plot.setBackground("#020617")
        charts_layout.addWidget(self.activity_plot, 1)

        center_layout.addLayout(charts_layout)

        main.addLayout(center_layout, 3)

        # 底部：左右两块表格（推荐效果指标 + 离线评估 / 用户画像）
        bottom_layout = QHBoxLayout()

        # 左：推荐效果指标表
        left_tables = QVBoxLayout()
        metrics_title = QLabel("推荐效果 & 业务指标")
        metrics_title.setObjectName("SectionTitle")
        left_tables.addWidget(metrics_title)

        self.metrics_table = QTableWidget(0, 2)
        self.metrics_table.setHorizontalHeaderLabels(["指标", "数值"])
        self._init_table_common(self.metrics_table)
        left_tables.addWidget(self.metrics_table, 2)

        # 离线实验 / 公开评估结果区
        self.eval_label = QLabel("公开测试集评估：暂无结果")
        self.eval_label.setObjectName("SubStatusLabel")
        left_tables.addWidget(self.eval_label)

        self.eval_table = QTableWidget(0, 3)
        self.eval_table.setHorizontalHeaderLabels(["K", "HitRate@K", "MAP@K"])
        self._init_table_common(self.eval_table)
        left_tables.addWidget(self.eval_table, 3)

        bottom_layout.addLayout(left_tables, 2)

        # 右：用户画像表
        right_tables = QVBoxLayout()
        users_title = QLabel("核心用户画像（活动度 TOP）")
        users_title.setObjectName("SectionTitle")
        right_tables.addWidget(users_title)

        self.user_table = QTableWidget(0, 3)
        self.user_table.setHorizontalHeaderLabels(["用户ID", "活跃度", "核心标签"])
        self._init_table_common(self.user_table)
        right_tables.addWidget(self.user_table)

        bottom_layout.addLayout(right_tables, 3)

        main.addLayout(bottom_layout, 2)

        # 将左右布局挂到 root
        root_layout.addLayout(sidebar, 2)
        root_layout.addLayout(main, 7)

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
        # 概览 summary：商品 + LLM 调用 + 推荐转化
        pstats = payload["product_stats"]
        lstats = payload["llm_stats"]
        estats = payload["effect_stats"]
        offline = payload.get("offline_eval") or {}
        self.summary_label.setText(
            "商品总数 {total} ｜ DeepSeek 调用 {calls} 次（≈ Token {tokens}）\n"
            "用户数 {users}（活跃 {active}）｜点击率 CTR {ctr:.1%} ｜ 转化率 CVR {cvr:.1%}".format(
                total=pstats.get("total", 0),
                calls=lstats.get("deepseek_calls", 0),
                tokens=lstats.get("estimated_tokens", 0),
                users=estats.get("total_users", 0),
                active=estats.get("active_users", 0),
                ctr=estats.get("ctr", 0.0),
                cvr=estats.get("cvr", 0.0),
            )
        )

        # 更新时间文案
        self.last_update_label.setText("最近刷新：来自本地日志 / JSON 当前快照")

        # 商品分类柱状图
        cats = list(pstats["category_dist"].keys())
        values = list(pstats["category_dist"].values())
        self.category_plot.clear()
        if values:
            xs = list(range(len(values)))
            bg = pg.BarGraphItem(x=xs, height=values, width=0.6, brush="#38bdf8")
            self.category_plot.addItem(bg)
            ax = self.category_plot.getAxis("bottom")
            ax.setTicks([list(enumerate(cats))])

        # 活跃度 & 下单趋势折线图
        daily = payload.get("daily_activity", [])
        self.activity_plot.clear()
        if daily:
            xs = list(range(len(daily)))
            events = [d.get("events", 0) for d in daily]
            orders = [d.get("orders", 0) for d in daily]
            days = [d.get("day", "") for d in daily]

            pen_events = pg.mkPen("#22c55e", width=2)  # 绿色：行为条数
            pen_orders = pg.mkPen("#f97316", width=2)  # 橙色：下单量
            self.activity_plot.plot(xs, events, pen=pen_events, name="行为数")
            self.activity_plot.plot(xs, orders, pen=pen_orders, name="订单数")
            ax = self.activity_plot.getAxis("bottom")
            tick_step = max(1, len(days) // 8)
            ticks = [(i, days[i]) for i in range(0, len(days), tick_step)]
            ax.setTicks([ticks])

        # 推荐效果指标表
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

        # 离线评估结果表
        if offline:
            ds = offline.get("dataset", "public_test")
            ts = offline.get("last_updated", "-")
            self.eval_label.setText(f"公开测试集评估（{ds}，更新于 {ts}）")
            rows = offline.get("rows", [])
            self.eval_table.setRowCount(len(rows))
            for i, r in enumerate(rows):
                self.eval_table.setItem(i, 0, QTableWidgetItem(str(r.get("k"))))
                hr = r.get("hit_rate")
                mp = r.get("map")
                self.eval_table.setItem(i, 1, QTableWidgetItem("-" if hr is None else f"{hr:.3f}"))
                self.eval_table.setItem(i, 2, QTableWidgetItem("-" if mp is None else f"{mp:.3f}"))
        else:
            self.eval_label.setText("公开测试集评估：暂无结果（缺少 data/metrics/recommender_eval.json）")
            self.eval_table.setRowCount(0)

        # 用户画像表
        users = payload["users"]
        self.user_table.setRowCount(len(users))
        for i, row in enumerate(users):
            self.user_table.setItem(i, 0, QTableWidgetItem(str(row["user_id"])))
            self.user_table.setItem(i, 1, QTableWidgetItem(str(row["activity_score"])))
            self.user_table.setItem(i, 2, QTableWidgetItem(str(row["core_tags"])))

        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("刷新数据")


if __name__ == "__main__":
    # 复用前面全局创建 / 获取到的 QApplication 实例
    w = DashboardWindow()
    w.show()
    sys.exit(_qt_app.exec_())
