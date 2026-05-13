"""
串口会话 Tab 页面
每个 Tab 只包含数据显示区，过滤和发送面板在主窗口中全局共享
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCheckBox
)
from PyQt6.QtCore import Qt

from app.display_widget import SerialDisplayWidget


class SerialTabWidget(QWidget):
    """串口会话 Tab 页面"""

    def __init__(self, tab_id: int, parent=None):
        super().__init__(parent)
        self._tab_id = tab_id
        self._filter_state = {
            "enabled": False, "pattern": "", "mode": "whitelist",
            "highlight": False, "bg_color": "#ffff00", "fg_color": "#000000",
        }
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 显示模式工具栏
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("显示:"))
        self._display_mode_combo = QComboBox()
        self._display_mode_combo.addItems(["ASCII", "HEX", "HEX+ASCII"])
        self._display_mode_combo.currentTextChanged.connect(
            self._on_display_mode_changed
        )
        toolbar.addWidget(self._display_mode_combo)
        toolbar.addStretch()
        self._ts_cb = QCheckBox("时间戳")
        self._ts_cb.setChecked(True)
        self._ts_cb.toggled.connect(self._on_ts_toggled)
        toolbar.addWidget(self._ts_cb)
        layout.addLayout(toolbar)

        # 数据显示
        self._display_widget = SerialDisplayWidget()
        layout.addWidget(self._display_widget, 1)

    def _on_display_mode_changed(self, mode: str):
        self._display_widget.set_display_mode(mode)

    def _on_ts_toggled(self, visible: bool):
        self._display_widget.set_timestamp_visible(visible)

    def on_data_received(self, data: bytes):
        self._display_widget.append_data(data, is_tx=False)

    def on_data_sent(self, data: str, fmt: str):
        if fmt == "HEX":
            try:
                hex_str = data.replace(" ", "")
                if len(hex_str) % 2 == 0:
                    tx_data = bytes.fromhex(hex_str)
                    self._display_widget.append_data(tx_data, is_tx=True)
            except ValueError:
                pass
        else:
            self._display_widget.append_data(data.encode("utf-8", errors="replace"), is_tx=True)

    @property
    def tab_title(self) -> str:
        return f"窗口 {self._tab_id}"

    @property
    def display_widget(self) -> SerialDisplayWidget:
        return self._display_widget

    def get_tab_config(self) -> dict:
        """获取当前 Tab 的完整配置"""
        return {
            "filter": self._filter_state,
            "display_mode": self._display_mode_combo.currentText(),
            "show_timestamp": self._ts_cb.isChecked(),
        }

    def set_tab_config(self, config: dict):
        """恢复 Tab 配置"""
        if not config:
            return
        # 过滤
        self._filter_state = config.get("filter", self._filter_state)
        # 显示模式
        mode = config.get("display_mode", "ASCII")
        idx = self._display_mode_combo.findText(mode)
        if idx >= 0:
            self._display_mode_combo.setCurrentIndex(idx)
        # 时间戳
        show_ts = config.get("show_timestamp", True)
        self._ts_cb.setChecked(show_ts)

    def cleanup(self):
        pass
