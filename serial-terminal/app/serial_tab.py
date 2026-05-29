"""
串口会话 Tab 页面
每个 Tab 只包含数据显示区，过滤和发送面板在主窗口中全局共享
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout
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

        # 数据显示
        self._display_widget = SerialDisplayWidget()
        layout.addWidget(self._display_widget, 1)

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
        }

    def set_tab_config(self, config: dict):
        """恢复 Tab 配置"""
        if not config:
            return
        # 过滤
        self._filter_state = config.get("filter", self._filter_state)

    def cleanup(self):
        pass
