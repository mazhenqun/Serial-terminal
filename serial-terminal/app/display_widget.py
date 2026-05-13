"""
数据显示组件
支持 HEX/ASCII/混合模式、时间戳、暂停、搜索、高亮等功能
"""

import re
from typing import List, Optional, Tuple
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit,
    QComboBox, QLabel, QCheckBox, QLineEdit, QPushButton,
    QTextEdit, QMenu, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRect
from PyQt6.QtGui import (
    QTextCursor, QColor, QTextCharFormat, QFont,
    QSyntaxHighlighter, QPainter, QTextFormat, QAction,
    QKeySequence, QBrush
)


class DisplayHighlighter(QSyntaxHighlighter):
    """数据显示高亮器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._search_pattern: Optional[re.Pattern] = None
        self._search_format = QTextCharFormat()
        self.set_colors("#ffff00", "#000000")

    def set_colors(self, bg_color: str, fg_color: str):
        """设置高亮颜色"""
        self._search_format.setBackground(QColor(bg_color))
        self._search_format.setForeground(QColor(fg_color))
        self._search_format.setFontWeight(QFont.Weight.Bold)

    def set_search_pattern(self, pattern: Optional[str]):
        if pattern:
            try:
                self._search_pattern = re.compile(re.escape(pattern), re.IGNORECASE)
            except re.error:
                self._search_pattern = None
        else:
            self._search_pattern = None
        self.rehighlight()

    def highlightBlock(self, text: str):
        if self._search_pattern:
            for match in self._search_pattern.finditer(text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, self._search_format)


class LineNumberArea(QWidget):
    """行号区域"""

    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor

    def paintEvent(self, event):
        self._editor.line_number_area_paint_event(event)

    def sizeHint(self):
        return self._editor.get_line_number_area_width()


class SerialDisplayWidget(QPlainTextEdit):
    """串口数据显示组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._display_mode = "ASCII"  # ASCII / HEX / Mixed
        self._show_timestamp = True
        self._timestamp_mode = "absolute"  # absolute / relative / none
        self._paused = False
        self._max_lines = 10000
        self._start_time = datetime.now()
        self._buffer: List[str] = []
        self._buffer_size = 0
        self._max_buffer_size = 1000  # 最大缓冲行数

        # 过滤相关
        self._filter_enabled = False
        self._filter_pattern: Optional[re.Pattern] = None
        self._filter_mode = "whitelist"  # whitelist / blacklist
        self._filter_highlight = False

        # 智能滚动标志
        self._auto_scroll = True

        # 设置字体
        self._font = QFont("Consolas", 10)
        self._font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(self._font)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setReadOnly(True)
        self.setCursorWidth(0)

        # 行号
        self._line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)

        # 高亮器
        self._highlighter = DisplayHighlighter(self.document())

        # 搜索相关
        self._search_text = ""
        self._last_search_pos = 0

        # 右键菜单
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # 定时刷新 buffer（确保数据即使不满 50 条也能及时显示）
        self._flush_timer = QTimer(self)
        self._flush_timer.timeout.connect(self._flush_buffer)
        self._flush_timer.start(100)  # 每 100ms 刷新一次

        self._update_line_number_area_width()

    def append_data(self, data: bytes, is_tx: bool = False):
        """追加接收到的数据"""
        if self._paused:
            return

        # 按行分割数据（支持 \r\n, \r, \n）
        text = data.decode("utf-8", errors="replace")
        # 统一换行符
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        raw_lines = text.split("\n")
        for i, line in enumerate(raw_lines):
            # 最后一个空行跳过（split 末尾产生）
            if i == len(raw_lines) - 1 and line == "":
                continue

            formatted = self._format_line(line, is_tx)

            # 过滤检查
            if self._filter_enabled and self._filter_pattern:
                if self._filter_mode == "whitelist":
                    if not self._filter_pattern.search(formatted):
                        continue
                else:  # blacklist
                    if self._filter_pattern.search(formatted):
                        continue

            self._buffer.append(formatted)
            self._buffer_size += 1

        # 批量刷新到界面
        if self._buffer_size >= 50:
            self._flush_buffer()

    def _flush_buffer(self):
        """刷新缓冲到界面"""
        if not self._buffer:
            return

        scrollbar = self.verticalScrollBar()

        # 控制最大行数：如果总行数超过限制，删除前面的行
        current_lines = self.blockCount()
        new_lines = len(self._buffer)
        if current_lines + new_lines > self._max_lines:
            excess = current_lines + new_lines - self._max_lines
            if excess >= current_lines:
                self.clear()
            else:
                cursor = self.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                for _ in range(excess):
                    cursor.movePosition(
                        QTextCursor.MoveOperation.Down,
                        QTextCursor.MoveMode.KeepAnchor
                    )
                cursor.removeSelectedText()

        text = "\n".join(self._buffer)
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.insertPlainText(text + "\n")
        self._buffer.clear()
        self._buffer_size = 0

        # 智能滚动：仅当 _auto_scroll 为 True 时才滚动到底部
        if self._auto_scroll:
            scrollbar.setValue(scrollbar.maximum())

    def wheelEvent(self, event):
        """鼠标滚轮事件：检测用户是否手动滚动"""
        super().wheelEvent(event)
        # 滚轮操作后检查是否在底部
        scrollbar = self.verticalScrollBar()
        self._auto_scroll = (scrollbar.value() >= scrollbar.maximum() - 10)

    def mousePressEvent(self, event):
        """鼠标点击事件：用户选中文本时停止自动滚动"""
        super().mousePressEvent(event)
        # 点击后延迟检查（等选中操作完成）
        QTimer.singleShot(50, self._check_auto_scroll)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        super().mouseReleaseEvent(event)
        QTimer.singleShot(50, self._check_auto_scroll)

    def keyPressEvent(self, event):
        """键盘事件：用户可能用键盘选中文本"""
        super().keyPressEvent(event)
        QTimer.singleShot(50, self._check_auto_scroll)

    def _check_auto_scroll(self):
        """检查是否应该恢复自动滚动"""
        scrollbar = self.verticalScrollBar()
        # 如果用户在底部，恢复自动滚动
        if scrollbar.maximum() == 0:
            self._auto_scroll = True
        else:
            self._auto_scroll = (scrollbar.value() >= scrollbar.maximum() - 10)

    def _format_line(self, text: str, is_tx: bool) -> str:
        """格式化单行文本为显示行"""
        ts = self._get_timestamp() if self._show_timestamp else ""

        if self._display_mode == "HEX":
            hex_str = text.encode("utf-8", errors="replace").hex(" ").upper()
            if ts:
                return f"[{ts}] {hex_str}"
            return hex_str

        elif self._display_mode == "ASCII":
            ascii_str = self._str_to_ascii(text)
            if ts:
                return f"[{ts}] {ascii_str}"
            return ascii_str

        else:  # Mixed
            data = text.encode("utf-8", errors="replace")
            hex_str = data.hex(" ").upper()
            ascii_str = self._str_to_ascii(text)
            if ts:
                return f"[{ts}] {hex_str}  |  {ascii_str}"
            return f"{hex_str}  |  {ascii_str}"

    def _str_to_ascii(self, text: str) -> str:
        """将字符串中的不可打印字符转为转义表示，保留 UTF-8 可显示字符"""
        result = []
        for ch in text:
            code = ord(ch)
            if 0x20 <= code <= 0x7E:
                result.append(ch)
            elif code == 0x0D:
                result.append("\\r")
            elif code == 0x0A:
                result.append("\\n")
            elif code == 0x09:
                result.append("\\t")
            elif code < 0x20:
                # 控制字符，转义
                result.append(f"\\x{code:02x}")
            else:
                # >= 0x7F 的字符（包括中文等多字节 UTF-8），直接保留
                result.append(ch)
        return "".join(result)

    def _get_timestamp(self) -> str:
        """获取时间戳字符串"""
        if self._timestamp_mode == "absolute":
            return datetime.now().strftime("%H:%M:%S.%f")[:-3]
        elif self._timestamp_mode == "relative":
            delta = datetime.now() - self._start_time
            total_ms = int(delta.total_seconds() * 1000)
            return f"+{total_ms}ms"
        return ""

    def clear_display(self):
        """清空显示"""
        self.clear()
        self._buffer.clear()
        self._buffer_size = 0

    def set_display_mode(self, mode: str):
        """设置显示模式"""
        self._display_mode = mode

    def set_timestamp_visible(self, visible: bool):
        """设置时间戳显示"""
        self._show_timestamp = visible

    def set_paused(self, paused: bool):
        """设置暂停状态"""
        self._paused = paused
        if not paused:
            self._flush_buffer()

    @property
    def is_paused(self) -> bool:
        return self._paused

    def set_max_lines(self, max_lines: int):
        """设置最大显示行数"""
        self._max_lines = max_lines

    def set_filter(self, enabled: bool, pattern: str = "", mode: str = "whitelist",
                   highlight: bool = False, bg_color: str = "#ffff00",
                   fg_color: str = "#000000"):
        """设置过滤规则"""
        self._filter_enabled = enabled
        self._filter_mode = mode
        self._filter_highlight = highlight

        if enabled and pattern:
            try:
                self._filter_pattern = re.compile(pattern, re.IGNORECASE)
            except re.error:
                self._filter_pattern = None
        else:
            self._filter_pattern = None

        # 设置高亮颜色
        self._highlighter.set_colors(bg_color, fg_color)

        # 设置高亮：如果启用了高亮且有 pattern，则设置高亮器
        if highlight and enabled and pattern:
            self._highlighter.set_search_pattern(pattern)
        else:
            self._highlighter.set_search_pattern(None)

    def set_search_text(self, text: str):
        """设置搜索文本"""
        self._highlighter.set_search_pattern(text if text else None)

    def get_all_text(self) -> str:
        """获取所有文本"""
        self._flush_buffer()
        return self.toPlainText()

    def get_filtered_text(self) -> str:
        """获取过滤后的文本"""
        self._flush_buffer()
        return self.toPlainText()

    # ---- 行号支持 ----
    def get_line_number_area_width(self) -> int:
        """计算行号区域宽度"""
        digits = len(str(max(1, self.blockCount())))
        return 10 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_line_number_area_width(self):
        self.setViewportMargins(self.get_line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy):
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(),
                                          self._line_number_area.width(), rect.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.get_line_number_area_width(), cr.height())
        )

    def line_number_area_paint_event(self, event):
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QColor("#252526"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#858585"))
                painter.drawText(
                    0, top, self._line_number_area.width() - 4,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight, number
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        copy_action = menu.addAction("复制 Ctrl+C")
        copy_action.triggered.connect(self._safe_copy)
        select_all_action = menu.addAction("全选 Ctrl+A")
        select_all_action.triggered.connect(self._safe_select_all)
        menu.addSeparator()
        find_action = menu.addAction("查找 Ctrl+F")
        find_action.triggered.connect(self._show_search_bar)
        menu.addSeparator()
        clear_action = menu.addAction("清空")
        clear_action.triggered.connect(self.clear_display)
        try:
            menu.exec(self.mapToGlobal(pos))
        except Exception:
            pass

    def _safe_copy(self):
        """安全复制"""
        try:
            self.copy()
        except Exception:
            pass

    def _safe_select_all(self):
        """安全全选"""
        try:
            self.selectAll()
        except Exception:
            pass

    # ---- 搜索功能 ----

    def keyPressEvent(self, event):
        """键盘事件"""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_F:
                self._show_search_bar()
            elif event.key() == Qt.Key.Key_C:
                self._safe_copy()
            elif event.key() == Qt.Key.Key_A:
                self._safe_select_all()
            else:
                super().keyPressEvent(event)
        elif event.key() == Qt.Key.Key_F4 or \
             (event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and
              not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier)):
            self._find_next()
        elif event.key() == Qt.Key.Key_F3 or \
             (event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and
              event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self._find_previous()
        elif event.key() == Qt.Key.Key_Escape:
            self._hide_search_bar()
        else:
            super().keyPressEvent(event)

    def _show_search_bar(self):
        """显示搜索栏"""
        if hasattr(self, '_search_bar') and self._search_bar.isVisible():
            self._search_input.setFocus()
            self._search_input.selectAll()
            return

        # 创建搜索栏
        self._search_bar = QWidget(self)
        self._search_bar.setStyleSheet(
            "background-color: #2d2d2d; border: 1px solid #1a8ad4; border-radius: 4px;"
        )
        bar_layout = QHBoxLayout(self._search_bar)
        bar_layout.setContentsMargins(4, 2, 4, 2)
        bar_layout.setSpacing(4)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("搜索...")
        self._search_input.setStyleSheet("border: none; background: transparent;")
        self._search_input.textChanged.connect(self._on_search_text_changed)
        bar_layout.addWidget(self._search_input)

        # 匹配计数
        self._search_count_label = QLabel("")
        self._search_count_label.setStyleSheet("color: #888; border: none;")
        bar_layout.addWidget(self._search_count_label)

        prev_btn = QPushButton("▲")
        prev_btn.setFixedSize(24, 24)
        prev_btn.setStyleSheet("border: none; background: transparent; color: #d4d4d4;")
        prev_btn.clicked.connect(self._find_previous)
        bar_layout.addWidget(prev_btn)

        next_btn = QPushButton("▼")
        next_btn.setFixedSize(24, 24)
        next_btn.setStyleSheet("border: none; background: transparent; color: #d4d4d4;")
        next_btn.clicked.connect(self._find_next)
        bar_layout.addWidget(next_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("border: none; background: transparent; color: #d4d4d4;")
        close_btn.clicked.connect(self._hide_search_bar)
        bar_layout.addWidget(close_btn)

        # 定位到右上角
        self._search_bar.setGeometry(
            self.width() - 320, 4, 310, 30
        )
        self._search_bar.show()
        self._search_input.setFocus()

    def _hide_search_bar(self):
        """隐藏搜索栏"""
        if hasattr(self, '_search_bar'):
            self._search_bar.hide()
            self._search_count_label.setText("")
            self._highlighter.set_search_pattern(None)
            self._search_text = ""

    def _on_search_text_changed(self, text: str):
        """搜索文本变化"""
        self._search_text = text
        self._last_search_pos = 0
        if text:
            self._highlighter.set_search_pattern(text)
            self._find_next()
        else:
            self._highlighter.set_search_pattern(None)
            self._search_count_label.setText("")

    def _find_next(self):
        """查找下一个"""
        if not self._search_text:
            return
        text = self.toPlainText()
        pos = text.find(self._search_text, self._last_search_pos)
        if pos == -1:
            # 从头开始
            pos = text.find(self._search_text, 0)
            if pos == -1:
                self._search_count_label.setText("无匹配")
                return

        self._last_search_pos = pos + len(self._search_text)
        self._select_and_scroll_to(pos, len(self._search_text))
        self._update_search_count(text)

    def _find_previous(self):
        """查找上一个"""
        if not self._search_text:
            return
        text = self.toPlainText()
        # 从当前匹配位置之前开始搜索
        start = self._last_search_pos - len(self._search_text)
        if start <= 0:
            start = len(text)
        pos = text.rfind(self._search_text, 0, start)
        if pos == -1:
            # 从末尾开始
            pos = text.rfind(self._search_text)
            if pos == -1:
                self._search_count_label.setText("无匹配")
                return

        self._last_search_pos = pos + len(self._search_text)
        self._select_and_scroll_to(pos, len(self._search_text))
        self._update_search_count(text)

    def _select_and_scroll_to(self, pos: int, length: int):
        """选中并滚动到指定位置"""
        cursor = self.textCursor()
        cursor.setPosition(pos)
        cursor.movePosition(
            QTextCursor.MoveOperation.Right,
            QTextCursor.MoveMode.KeepAnchor,
            length
        )
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def _update_search_count(self, text: str):
        """更新匹配计数"""
        count = text.count(self._search_text)
        current = text[:self._last_search_pos].count(self._search_text)
        if count > 0:
            self._search_count_label.setText(f"{current}/{count}")
        else:
            self._search_count_label.setText("无匹配")
