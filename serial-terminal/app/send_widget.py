"""
数据发送组件
支持 HEX/字符串发送、快捷指令管理（含备注和循环发送）、定时发送、发送历史
"""

from typing import Optional
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QTextEdit, QListWidget,
    QListWidgetItem, QGroupBox, QSpinBox, QCheckBox,
    QSplitter, QMessageBox, QMenu, QInputDialog, QFileDialog,
    QFrame, QDialog, QDialogButtonBox, QFormLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont


class QuickCommandItem:
    """快捷指令数据模型"""

    def __init__(self, name: str = "", data: str = "", format_type: str = "hex",
                 note: str = "", cycle_ms: int = 0):
        self.name = name
        self.data = data
        self.format_type = format_type  # hex / string
        self.note = note  # 备注
        self.cycle_ms = cycle_ms  # 循环发送周期(ms)，0表示不循环

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "data": self.data,
            "format": self.format_type,
            "note": self.note,
            "cycle_ms": self.cycle_ms,
        }

    @staticmethod
    def from_dict(d: dict) -> "QuickCommandItem":
        return QuickCommandItem(
            name=d.get("name", ""),
            data=d.get("data", ""),
            format_type=d.get("format", "hex"),
            note=d.get("note", ""),
            cycle_ms=d.get("cycle_ms", 0),
        )


class CommandEditDialog(QDialog):
    """指令编辑对话框"""

    def __init__(self, parent=None, cmd: Optional[QuickCommandItem] = None):
        super().__init__(parent)
        self.setWindowTitle("编辑指令" if cmd else "添加指令")
        self.setMinimumWidth(420)
        self._cmd = cmd
        self._setup_ui()
        if cmd:
            self._load_cmd(cmd)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("如：查询状态")
        form.addRow("指令名称:", self._name_input)

        self._data_input = QLineEdit()
        self._data_input.setPlaceholderText("如：7E 01 00 00 或 hello")
        self._data_input.setFont(QFont("Consolas", 10))
        form.addRow("指令数据:", self._data_input)

        self._format_combo = QComboBox()
        self._format_combo.addItems(["HEX", "字符串"])
        form.addRow("数据格式:", self._format_combo)

        self._note_input = QLineEdit()
        self._note_input.setPlaceholderText("备注说明（可选）")
        form.addRow("备注:", self._note_input)

        # 循环发送
        cycle_layout = QHBoxLayout()
        self._cycle_cb = QCheckBox("启用循环发送")
        cycle_layout.addWidget(self._cycle_cb)
        cycle_layout.addWidget(QLabel("周期(ms):"))
        self._cycle_spin = QSpinBox()
        self._cycle_spin.setRange(100, 60000)
        self._cycle_spin.setValue(1000)
        self._cycle_spin.setSuffix(" ms")
        cycle_layout.addWidget(self._cycle_spin)
        cycle_layout.addStretch()
        form.addRow("", cycle_layout)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_cmd(self, cmd: QuickCommandItem):
        self._name_input.setText(cmd.name)
        self._data_input.setText(cmd.data)
        self._format_combo.setCurrentIndex(0 if cmd.format_type == "hex" else 1)
        self._note_input.setText(cmd.note)
        if cmd.cycle_ms > 0:
            self._cycle_cb.setChecked(True)
            self._cycle_spin.setValue(cmd.cycle_ms)

    def get_command(self) -> QuickCommandItem:
        return QuickCommandItem(
            name=self._name_input.text().strip(),
            data=self._data_input.text().strip(),
            format_type="hex" if self._format_combo.currentText() == "HEX" else "string",
            note=self._note_input.text().strip(),
            cycle_ms=self._cycle_spin.value() if self._cycle_cb.isChecked() else 0,
        )


class SendWidget(QGroupBox):
    """数据发送组件"""

    send_requested = pyqtSignal(str, str)  # data, format_type

    def __init__(self, parent=None):
        super().__init__("数据发送", parent)
        self._history: list = []
        self._quick_commands: list[QuickCommandItem] = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timer_tick)
        self._cycle_timers: dict[int, QTimer] = {}  # 每条指令的循环定时器
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 16, 8, 8)

        # 发送格式选择
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("发送格式:"))
        self._format_combo = QComboBox()
        self._format_combo.addItems(["HEX", "字符串"])
        format_layout.addWidget(self._format_combo)
        format_layout.addStretch()
        layout.addLayout(format_layout)

        # 发送输入区
        self._send_input = QLineEdit()
        self._send_input.setPlaceholderText("输入要发送的数据...")
        self._send_input.setFont(QFont("Consolas", 10))
        self._send_input.returnPressed.connect(self._send_data)
        layout.addWidget(self._send_input)

        # 发送按钮行
        send_btn_layout = QHBoxLayout()
        self._send_btn = QPushButton("发送")
        self._send_btn.clicked.connect(self._send_data)
        send_btn_layout.addWidget(self._send_btn)

        self._append_newline_cb = QCheckBox("追加换行")
        send_btn_layout.addWidget(self._append_newline_cb)

        self._newline_combo = QComboBox()
        self._newline_combo.addItems(["CR+LF", "CR", "LF"])
        send_btn_layout.addWidget(self._newline_combo)

        send_btn_layout.addStretch()
        layout.addLayout(send_btn_layout)

        # 定时发送
        timer_layout = QHBoxLayout()
        self._timer_cb = QCheckBox("定时发送")
        self._timer_cb.toggled.connect(self._on_timer_toggle)
        timer_layout.addWidget(self._timer_cb)

        timer_layout.addWidget(QLabel("周期(ms):"))
        self._timer_interval = QSpinBox()
        self._timer_interval.setRange(10, 60000)
        self._timer_interval.setValue(1000)
        self._timer_interval.setSuffix(" ms")
        timer_layout.addWidget(self._timer_interval)
        timer_layout.addStretch()
        layout.addLayout(timer_layout)

        # 快捷指令表格
        commands_label = QLabel("快捷指令列表:")
        layout.addWidget(commands_label)

        self._cmd_table = QTableWidget()
        self._cmd_table.setColumnCount(5)
        self._cmd_table.setHorizontalHeaderLabels(["名称", "数据", "格式", "备注", "循环(ms)"])
        self._cmd_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._cmd_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._cmd_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._cmd_table.setAlternatingRowColors(True)
        self._cmd_table.verticalHeader().setVisible(False)
        self._cmd_table.horizontalHeader().setStretchLastSection(True)
        self._cmd_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._cmd_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._cmd_table.customContextMenuRequested.connect(self._show_command_menu)
        self._cmd_table.cellDoubleClicked.connect(self._on_cmd_double_click)
        layout.addWidget(self._cmd_table)

        # 快捷指令按钮
        cmd_btn_layout = QHBoxLayout()
        add_cmd_btn = QPushButton("+ 添加")
        add_cmd_btn.clicked.connect(self._add_command)
        cmd_btn_layout.addWidget(add_cmd_btn)

        send_cmd_btn = QPushButton("[发送选中]")
        send_cmd_btn.clicked.connect(self._send_selected_cmd)
        cmd_btn_layout.addWidget(send_cmd_btn)

        edit_cmd_btn = QPushButton("[编辑]")
        edit_cmd_btn.clicked.connect(self._edit_selected_cmd)
        cmd_btn_layout.addWidget(edit_cmd_btn)

        del_cmd_btn = QPushButton("[删除]")
        del_cmd_btn.clicked.connect(self._delete_selected_cmd)
        cmd_btn_layout.addWidget(del_cmd_btn)

        cmd_btn_layout.addStretch()

        import_btn = QPushButton("导入")
        import_btn.clicked.connect(self._import_commands)
        cmd_btn_layout.addWidget(import_btn)

        export_btn = QPushButton("导出")
        export_btn.clicked.connect(self._export_commands)
        cmd_btn_layout.addWidget(export_btn)

        layout.addLayout(cmd_btn_layout)

    def _send_data(self):
        """发送数据"""
        text = self._send_input.text().strip()
        if not text:
            return

        fmt = self._format_combo.currentText()

        if self._append_newline_cb.isChecked():
            nl_type = self._newline_combo.currentText()
            if nl_type == "CR+LF":
                text += "\\r\\n"
            elif nl_type == "CR":
                text += "\\r"
            elif nl_type == "LF":
                text += "\\n"

        self._add_history(text)
        self.send_requested.emit(text, fmt)

    def _add_history(self, text: str):
        if text in self._history:
            self._history.remove(text)
        self._history.insert(0, text)
        if len(self._history) > 50:
            self._history = self._history[:50]

    def _on_timer_toggle(self, checked: bool):
        if checked:
            self._timer.setInterval(self._timer_interval.value())
            self._timer.start()
        else:
            self._timer.stop()

    def _on_timer_tick(self):
        text = self._send_input.text().strip()
        if text:
            fmt = self._format_combo.currentText()
            self.send_requested.emit(text, fmt)

    # ---- 快捷指令管理 ----

    def _add_command(self):
        dlg = CommandEditDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            cmd = dlg.get_command()
            if cmd.name and cmd.data:
                self._quick_commands.append(cmd)
                self._refresh_commands_list()
                self._update_cycle_timer(len(self._quick_commands) - 1, cmd)

    def _edit_selected_cmd(self):
        row = self._cmd_table.currentRow()
        if 0 <= row < len(self._quick_commands):
            cmd = self._quick_commands[row]
            dlg = CommandEditDialog(self, cmd)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                new_cmd = dlg.get_command()
                if new_cmd.name and new_cmd.data:
                    self._quick_commands[row] = new_cmd
                    self._refresh_commands_list()
                    self._update_cycle_timer(row, new_cmd)

    def _delete_selected_cmd(self):
        row = self._cmd_table.currentRow()
        if 0 <= row < len(self._quick_commands):
            self._stop_cycle_timer(row)
            self._quick_commands.pop(row)
            self._refresh_commands_list()

    def _show_command_menu(self, pos):
        row = self._cmd_table.rowAt(pos.y())
        if row < 0:
            return
        self._cmd_table.selectRow(row)

        menu = QMenu(self)
        send_action = menu.addAction("[发送]")
        send_action.triggered.connect(lambda: self._send_cmd(row))

        menu.addSeparator()
        edit_action = menu.addAction("[编辑]")
        edit_action.triggered.connect(self._edit_selected_cmd)

        delete_action = menu.addAction("[删除]")
        delete_action.triggered.connect(self._delete_selected_cmd)

        menu.exec(self._cmd_table.mapToGlobal(pos))

    def _on_cmd_double_click(self, row: int, col: int):
        """双击发送"""
        self._send_cmd(row)

    def _send_selected_cmd(self):
        row = self._cmd_table.currentRow()
        if 0 <= row < len(self._quick_commands):
            self._send_cmd(row)

    def _send_cmd(self, row: int):
        """发送指定行的指令"""
        if 0 <= row < len(self._quick_commands):
            cmd = self._quick_commands[row]
            self.send_requested.emit(cmd.data, cmd.format_type)

    def _update_cycle_timer(self, row: int, cmd: QuickCommandItem):
        """更新循环定时器"""
        self._stop_cycle_timer(row)
        if cmd.cycle_ms > 0:
            timer = QTimer(self)
            timer.timeout.connect(lambda r=row: self._send_cmd(r))
            timer.start(cmd.cycle_ms)
            self._cycle_timers[row] = timer

    def _stop_cycle_timer(self, row: int):
        if row in self._cycle_timers:
            self._cycle_timers[row].stop()
            del self._cycle_timers[row]

    def _refresh_commands_list(self):
        """刷新快捷指令表格"""
        self._cmd_table.setRowCount(len(self._quick_commands))
        for i, cmd in enumerate(self._quick_commands):
            self._cmd_table.setItem(i, 0, QTableWidgetItem(cmd.name))
            self._cmd_table.setItem(i, 1, QTableWidgetItem(cmd.data))
            fmt_text = "HEX" if cmd.format_type == "hex" else "字符串"
            self._cmd_table.setItem(i, 2, QTableWidgetItem(fmt_text))
            self._cmd_table.setItem(i, 3, QTableWidgetItem(cmd.note))
            cycle_text = str(cmd.cycle_ms) if cmd.cycle_ms > 0 else "—"
            self._cmd_table.setItem(i, 4, QTableWidgetItem(cycle_text))

    def _import_commands(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入快捷指令", "", "JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            return
        try:
            import json
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 停止所有循环定时器
            for row in list(self._cycle_timers.keys()):
                self._stop_cycle_timer(row)
            self._quick_commands = [QuickCommandItem.from_dict(d) for d in data]
            self._refresh_commands_list()
            # 恢复循环定时器
            for i, cmd in enumerate(self._quick_commands):
                self._update_cycle_timer(i, cmd)
        except Exception as e:
            QMessageBox.warning(self, "导入失败", f"导入快捷指令失败: {str(e)}")

    def _export_commands(self):
        if not self._quick_commands:
            QMessageBox.information(self, "导出", "没有快捷指令可导出")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出快捷指令", "quick_commands.json",
            "JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            return
        try:
            import json
            data = [cmd.to_dict() for cmd in self._quick_commands]
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "导出成功", f"已导出 {len(data)} 条快捷指令")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", f"导出快捷指令失败: {str(e)}")

    def get_quick_commands(self) -> list:
        return self._quick_commands

    def set_quick_commands(self, commands: list):
        for row in list(self._cycle_timers.keys()):
            self._stop_cycle_timer(row)
        self._quick_commands = [
            QuickCommandItem.from_dict(c) if isinstance(c, dict) else c
            for c in commands
        ]
        self._refresh_commands_list()
        for i, cmd in enumerate(self._quick_commands):
            self._update_cycle_timer(i, cmd)

    def get_send_text(self) -> str:
        return self._send_input.text()

    def set_send_text(self, text: str):
        self._send_input.setText(text)

    def stop_timer(self):
        self._timer_cb.setChecked(False)
        self._timer.stop()
        for row in list(self._cycle_timers.keys()):
            self._stop_cycle_timer(row)
