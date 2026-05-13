"""
过滤组件
支持关键字过滤、正则表达式过滤、白名单/黑名单模式、自定义高亮颜色
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QCheckBox, QPushButton, QGroupBox, QColorDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor


class FilterWidget(QGroupBox):
    """数据过滤组件"""

    # enabled, pattern, mode, highlight, bg_color, fg_color
    filter_changed = pyqtSignal(bool, str, str, bool, str, str)

    def __init__(self, parent=None):
        super().__init__("数据过滤", parent)
        self._highlight_bg = "#ffff00"  # 默认黄色背景
        self._highlight_fg = "#000000"  # 默认黑色文字
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 16, 8, 8)

        # 启用过滤
        enable_layout = QHBoxLayout()
        self._enable_cb = QCheckBox("启用过滤")
        self._enable_cb.toggled.connect(self._on_changed)
        enable_layout.addWidget(self._enable_cb)
        enable_layout.addStretch()
        layout.addLayout(enable_layout)

        # 过滤模式
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("模式:"))
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["白名单(仅显示匹配)", "黑名单(隐藏匹配)"])
        self._mode_combo.currentIndexChanged.connect(self._on_changed)
        mode_layout.addWidget(self._mode_combo)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # 过滤输入
        self._pattern_input = QLineEdit()
        self._pattern_input.setPlaceholderText("输入过滤关键字或正则表达式...")
        self._pattern_input.textChanged.connect(self._on_changed)
        layout.addWidget(self._pattern_input)

        # 选项
        options_layout = QHBoxLayout()
        self._regex_cb = QCheckBox("正则表达式")
        self._regex_cb.toggled.connect(self._on_changed)
        options_layout.addWidget(self._regex_cb)

        self._highlight_cb = QCheckBox("高亮匹配")
        self._highlight_cb.toggled.connect(self._on_changed)
        options_layout.addWidget(self._highlight_cb)

        options_layout.addStretch()
        layout.addLayout(options_layout)

        # 高亮颜色选择
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("高亮颜色:"))

        self._bg_color_btn = QPushButton("背景")
        self._bg_color_btn.setFixedWidth(50)
        self._bg_color_btn.setStyleSheet(
            f"background-color: {self._highlight_bg}; color: {self._highlight_fg};"
            "border: 1px solid #555; border-radius: 3px; padding: 2px 6px;"
        )
        self._bg_color_btn.clicked.connect(self._pick_bg_color)
        color_layout.addWidget(self._bg_color_btn)

        self._fg_color_btn = QPushButton("文字")
        self._fg_color_btn.setFixedWidth(50)
        self._fg_color_btn.setStyleSheet(
            f"background-color: {self._highlight_fg}; color: {self._highlight_bg};"
            "border: 1px solid #555; border-radius: 3px; padding: 2px 6px;"
        )
        self._fg_color_btn.clicked.connect(self._pick_fg_color)
        color_layout.addWidget(self._fg_color_btn)

        color_layout.addStretch()
        layout.addLayout(color_layout)

        # 重置按钮
        reset_btn = QPushButton("重置过滤")
        reset_btn.clicked.connect(self._reset)
        layout.addWidget(reset_btn)

    def _pick_bg_color(self):
        """选择高亮背景色"""
        color = QColorDialog.getColor(QColor(self._highlight_bg), self, "选择高亮背景色")
        if color.isValid():
            self._highlight_bg = color.name()
            self._bg_color_btn.setStyleSheet(
                f"background-color: {self._highlight_bg}; color: {self._highlight_fg};"
                "border: 1px solid #555; border-radius: 3px; padding: 2px 6px;"
            )
            self._on_changed()

    def _pick_fg_color(self):
        """选择高亮文字颜色"""
        color = QColorDialog.getColor(QColor(self._highlight_fg), self, "选择高亮文字颜色")
        if color.isValid():
            self._highlight_fg = color.name()
            self._fg_color_btn.setStyleSheet(
                f"background-color: {self._highlight_fg}; color: {self._highlight_bg};"
                "border: 1px solid #555; border-radius: 3px; padding: 2px 6px;"
            )
            self._on_changed()

    def _on_changed(self):
        enabled = self._enable_cb.isChecked()
        pattern = self._pattern_input.text().strip()
        mode = "whitelist" if self._mode_combo.currentIndex() == 0 else "blacklist"
        highlight = self._highlight_cb.isChecked()

        if enabled and pattern:
            self.filter_changed.emit(enabled, pattern, mode, highlight,
                                     self._highlight_bg, self._highlight_fg)
        elif not enabled:
            self.filter_changed.emit(False, "", "whitelist", False,
                                     self._highlight_bg, self._highlight_fg)

    def _reset(self):
        self._enable_cb.setChecked(False)
        self._pattern_input.clear()
        self._mode_combo.setCurrentIndex(0)
        self._regex_cb.setChecked(False)
        self._highlight_cb.setChecked(False)
        self.filter_changed.emit(False, "", "whitelist", False,
                                 self._highlight_bg, self._highlight_fg)

    def set_enabled(self, enabled: bool):
        """启用/禁用过滤功能"""
        self.setEnabled(enabled)

    def get_filter_state(self) -> dict:
        """获取当前过滤状态"""
        return {
            "enabled": self._enable_cb.isChecked(),
            "pattern": self._pattern_input.text().strip(),
            "mode": "whitelist" if self._mode_combo.currentIndex() == 0 else "blacklist",
            "highlight": self._highlight_cb.isChecked(),
            "bg_color": self._highlight_bg,
            "fg_color": self._highlight_fg,
        }

    def set_filter_state(self, state: dict):
        """恢复过滤状态（仅恢复 UI，不触发信号）"""
        if not state:
            return

        # blockSignals 防止设置过程中触发信号
        self._enable_cb.blockSignals(True)
        self._pattern_input.blockSignals(True)
        self._mode_combo.blockSignals(True)
        self._highlight_cb.blockSignals(True)

        enable = state.get("enabled", False)
        self._enable_cb.setChecked(enable)
        self._pattern_input.setText(state.get("pattern", ""))
        mode = state.get("mode", "whitelist")
        self._mode_combo.setCurrentIndex(0 if mode == "whitelist" else 1)
        self._highlight_cb.setChecked(state.get("highlight", False))

        bg = state.get("bg_color", "#ffff00")
        fg = state.get("fg_color", "#000000")
        if bg:
            self._highlight_bg = bg
            self._bg_color_btn.setStyleSheet(
                f"background-color: {bg}; color: {fg};"
                "border: 1px solid #555; border-radius: 3px; padding: 2px 6px;"
            )
        if fg:
            self._highlight_fg = fg
            self._fg_color_btn.setStyleSheet(
                f"background-color: {fg}; color: {bg};"
                "border: 1px solid #555; border-radius: 3px; padding: 2px 6px;"
            )

        # 恢复信号
        self._enable_cb.blockSignals(False)
        self._pattern_input.blockSignals(False)
        self._mode_combo.blockSignals(False)
        self._highlight_cb.blockSignals(False)
