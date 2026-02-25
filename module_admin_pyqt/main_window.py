"""模块五：PyQt5 管理监控大屏。"""

from __future__ import annotations

import sys
from typing import Any

import pyqtgraph as pg
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from module_admin_pyqt.local_data_monitor import compute_llm_usage, compute_product_stats, compute_user_table


class DataWorker(QThread):
    """后台线程：异步读取本地 JSON/日志，避免 UI 卡顿。"""

    done = pyqtSignal(dict)

    def run(self) -> None:
        payload = {
            "product_stats": compute_product_stats(),
            "llm_stats": compute_llm_usage(),
            "users": compute_user_table(),
        }
        self.done.emit(payload)


class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("管理员监控大屏")
        self.resize(1200, 760)
        self.setStyleSheet("background-color:#0b1020;color:#e2e8f0;")

        root = QWidget()
        self.setCentralWidget(root)

        layout = QHBoxLayout(root)
        menu = QVBoxLayout()
        content = QVBoxLayout()

        self.refresh_btn = QPushButton("刷新数据")
        self.refresh_btn.clicked.connect(self.refresh)
        menu.addWidget(self.refresh_btn)
        menu.addStretch()

        self.summary_label = QLabel("加载中...")
        content.addWidget(self.summary_label)

        self.plot_widget = pg.PlotWidget(title="分类占比（数量）")
        self.plot_widget.setBackground("#0f172a")
        content.addWidget(self.plot_widget)

        self.user_table = QTableWidget(0, 3)
        self.user_table.setHorizontalHeaderLabels(["用户ID", "活跃度", "核心标签"])
        content.addWidget(self.user_table)

        layout.addLayout(menu, 1)
        layout.addLayout(content, 5)

        self.worker: DataWorker | None = None
        self.refresh()

    def refresh(self) -> None:
        self.worker = DataWorker()
        self.worker.done.connect(self.render_data)
        self.worker.start()

    def render_data(self, payload: dict[str, Any]) -> None:
        pstats = payload["product_stats"]
        lstats = payload["llm_stats"]
        self.summary_label.setText(
            f"商品总数: {pstats['total']} | DeepSeek调用: {lstats['deepseek_calls']} | 估算Token: {lstats['estimated_tokens']}"
        )

        cats = list(pstats["category_dist"].keys())
        values = list(pstats["category_dist"].values())
        self.plot_widget.clear()
        if values:
            bg = pg.BarGraphItem(x=list(range(len(values))), height=values, width=0.6, brush="#38bdf8")
            self.plot_widget.addItem(bg)
            ax = self.plot_widget.getAxis("bottom")
            ax.setTicks([list(enumerate(cats))])

        users = payload["users"]
        self.user_table.setRowCount(len(users))
        for i, row in enumerate(users):
            self.user_table.setItem(i, 0, QTableWidgetItem(str(row["user_id"])))
            self.user_table.setItem(i, 1, QTableWidgetItem(str(row["activity_score"])))
            self.user_table.setItem(i, 2, QTableWidgetItem(str(row["core_tags"])))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = DashboardWindow()
    w.show()
    sys.exit(app.exec_())
