"""
主窗口
管理多 Tab 串口会话、工具栏、状态栏、菜单栏
所有 Tab 共享同一个 SerialManager 串口连接
串口配置栏在顶部，过滤和发送面板在右侧全局共享
"""

from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QToolBar, QStatusBar, QMenuBar,
    QMenu, QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QFileDialog,
    QLabel, QPushButton, QApplication, QFrame, QSplitter
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup, QKeySequence, QIcon

from app.serial_manager import SerialManager
from app.serial_tab import SerialTabWidget
from app.config_widget import SerialConfigWidget
from app.filter_widget import FilterWidget
from app.send_widget import SendWidget
from app.config import AppConfig


class MainWindow(QMainWindow):
    """应用程序主窗口"""

    # 定义跨线程通信的信号
    sig_data_received = pyqtSignal(bytes)
    sig_error = pyqtSignal(str)
    sig_disconnected = pyqtSignal()

    def __init__(self, config: AppConfig):
        super().__init__()
        self._config = config
        self._tab_counter = 0

        # 全局共享的串口管理器
        self._serial_manager = SerialManager()
        
        # 绑定信号到槽函数 (自动处理跨线程)
        self.sig_data_received.connect(self._on_global_data_received)
        self.sig_error.connect(self._on_global_error)
        self.sig_disconnected.connect(self._on_global_disconnected)

        # 设置回调为信号的 emit 方法
        self._serial_manager.set_on_data_received(self.sig_data_received.emit)
        self._serial_manager.set_on_error(self.sig_error.emit)
        self._serial_manager.set_on_disconnected(self.sig_disconnected.emit)

        self._syncing_filter = False  # 过滤同步标志
        self._auto_save_enabled = False
        self._auto_save_file = None
        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.timeout.connect(self._do_auto_save)
        self._auto_save_timer.setInterval(1000)  # 每秒保存一次

        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_serial_bar()
        self._setup_statusbar()

        # 状态更新定时器
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._update_status_info)
        self._status_timer.start(500)

        # 添加第一个 Tab
        self._new_tab()

        # 恢复配置
        self._restore_config()

        # 手动初始化过滤面板 UI（首次加载时 _on_tab_changed 可能不会触发）
        if self._tab_widget.count() > 0:
            self._on_tab_changed(self._tab_widget.currentIndex())

    def _setup_ui(self):
        self.setWindowTitle("Serial Terminal - 串口调试工具")
        self.setMinimumSize(1024, 680)
        self.resize(1280, 800)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 左侧：Tab 区 + 串口配置栏
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # 串口配置栏（在 Tab 上方）
        self._serial_bar_container = QWidget()
        self._serial_bar_container.setObjectName("serialBarContainer")
        left_layout.addWidget(self._serial_bar_container)

        # Tab 控件
        self._tab_widget = QTabWidget()
        self._tab_widget.setTabsClosable(True)
        self._tab_widget.setMovable(True)
        self._tab_widget.setDocumentMode(True)
        self._tab_widget.tabCloseRequested.connect(self._close_tab)
        self._tab_widget.currentChanged.connect(self._on_tab_changed)
        left_layout.addWidget(self._tab_widget)

        # 右侧：过滤 + 发送（全局共享，同一列垂直分割）
        right_panel = QWidget()
        right_panel.setMinimumWidth(300)
        right_panel.setMaximumWidth(450)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        right_splitter = QSplitter(Qt.Orientation.Vertical)

        # 全局过滤面板
        self._filter_widget = FilterWidget()
        self._filter_widget.filter_changed.connect(self._on_filter_changed)
        right_splitter.addWidget(self._filter_widget)

        # 全局发送面板
        self._send_widget = SendWidget()
        self._send_widget.send_requested.connect(self._on_send_requested)
        right_splitter.addWidget(self._send_widget)

        right_splitter.setStretchFactor(0, 1)  # 过滤
        right_splitter.setStretchFactor(1, 3)  # 发送（大占比）
        right_splitter.setSizes([200, 500])

        right_layout.addWidget(right_splitter)

        # 主分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([850, 350])

        layout.addWidget(splitter)

    def _setup_serial_bar(self):
        """创建串口配置栏"""
        self._serial_bar_container.setFixedHeight(42)
        self._serial_bar_container.setStyleSheet(
            "#serialBarContainer { background-color: #2d2d2d; border-bottom: 1px solid #3c3c3c; }"
        )

        bar_layout = QHBoxLayout(self._serial_bar_container)
        bar_layout.setContentsMargins(8, 2, 8, 2)
        bar_layout.setSpacing(6)

        self._config_widget = SerialConfigWidget(self._serial_manager)
        self._config_widget.set_compact_mode(True)
        bar_layout.addWidget(self._config_widget)

    def _setup_menu(self):
        menubar = self.menuBar()
        self._actions = {}

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        self._actions["save"] = QAction("保存数据(&S)", self)
        self._actions["save"].setShortcut(QKeySequence("Ctrl+S"))
        self._actions["save"].triggered.connect(self._save_data)
        file_menu.addAction(self._actions["save"])

        save_as_action = QAction("另存为...", self)
        save_as_action.triggered.connect(self._save_data_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        self._auto_save_action = QAction("自动保存(&A)", self)
        self._auto_save_action.setCheckable(True)
        self._auto_save_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self._auto_save_action.triggered.connect(self._toggle_auto_save)
        self._actions["auto_save"] = self._auto_save_action
        file_menu.addAction(self._auto_save_action)

        file_menu.addSeparator()

        self._actions["exit"] = QAction("退出(&X)", self)
        self._actions["exit"].setShortcut(QKeySequence("Ctrl+Q"))
        self._actions["exit"].triggered.connect(self.close)
        file_menu.addAction(self._actions["exit"])

        # 串口菜单
        port_menu = menubar.addMenu("串口(&P)")
        self._actions["new_tab"] = QAction("新建窗口(&N)", self)
        self._actions["new_tab"].setShortcut(QKeySequence("Ctrl+N"))
        self._actions["new_tab"].triggered.connect(self._new_tab)
        port_menu.addAction(self._actions["new_tab"])

        self._actions["close_tab"] = QAction("关闭窗口(&W)", self)
        self._actions["close_tab"].setShortcut(QKeySequence("Ctrl+W"))
        self._actions["close_tab"].triggered.connect(lambda: self._close_tab(self._tab_widget.currentIndex()))
        port_menu.addAction(self._actions["close_tab"])

        port_menu.addSeparator()

        self._toggle_connect_action = QAction("连接/断开(F1)", self)
        self._toggle_connect_action.setShortcut(QKeySequence("F1"))
        self._toggle_connect_action.triggered.connect(self._toggle_connect)
        self._actions["toggle_connect"] = self._toggle_connect_action
        port_menu.addAction(self._toggle_connect_action)

        # 显示菜单
        display_menu = menubar.addMenu("显示(&D)")
        self._actions["clear_display"] = QAction("清空显示", self)
        self._actions["clear_display"].setShortcut(QKeySequence("F9"))
        self._actions["clear_display"].triggered.connect(self._clear_display)
        display_menu.addAction(self._actions["clear_display"])

        self._pause_action = QAction("暂停/继续(&P)", self)
        self._pause_action.setShortcut(QKeySequence("Ctrl+P"))
        self._pause_action.triggered.connect(self._toggle_pause)
        self._actions["toggle_pause"] = self._pause_action
        display_menu.addAction(self._pause_action)

        display_menu.addSeparator()

        self._ts_menu_action = QAction("时间戳(&T)", self)
        self._ts_menu_action.setCheckable(True)
        self._ts_menu_action.setChecked(True)
        self._ts_menu_action.setShortcut(QKeySequence("Ctrl+T"))
        self._ts_menu_action.triggered.connect(self._toggle_timestamp)
        self._actions["toggle_timestamp"] = self._ts_menu_action
        display_menu.addAction(self._ts_menu_action)

        # 模式切换（带勾选）
        mode_menu = display_menu.addMenu("显示模式(&M)")
        self._mode_action_group = QActionGroup(self)
        self._mode_action_group.setExclusive(True)
        self._current_mode = "ASCII"
        for mode in ["ASCII", "HEX", "HEX+ASCII"]:
            action = QAction(mode, self)
            action.setCheckable(True)
            action.setChecked(mode == self._current_mode)
            action.triggered.connect(lambda checked, m=mode: self._set_display_mode(m))
            self._mode_action_group.addAction(action)
            mode_menu.addAction(action)

        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")
        theme_menu = view_menu.addMenu("主题")
        dark_action = QAction("深色", self)
        dark_action.triggered.connect(lambda: self._set_theme("dark"))
        theme_menu.addAction(dark_action)
        light_action = QAction("浅色", self)
        light_action.triggered.connect(lambda: self._set_theme("light"))
        theme_menu.addAction(light_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        about_action = QAction("帮助/快捷键(&A)", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_toolbar(self):
        # 工具栏全部移除，功能通过菜单和按钮操作
        pass

    def _setup_statusbar(self):
        status = QStatusBar()
        self.setStatusBar(status)

        self._status_connection = QLabel("未连接")
        self._status_connection.setStyleSheet("padding: 0 8px; font-weight: bold;")
        status.addWidget(self._status_connection)

        status.addPermanentWidget(QLabel("|"))

        self._status_rx = QLabel("RX: 0 bytes")
        self._status_rx.setStyleSheet("padding: 0 8px;")
        status.addPermanentWidget(self._status_rx)

        self._status_tx = QLabel("TX: 0 bytes")
        self._status_tx.setStyleSheet("padding: 0 8px;")
        status.addPermanentWidget(self._status_tx)

        status.addPermanentWidget(QLabel("|"))

        self._status_info = QLabel("就绪")
        self._status_info.setStyleSheet("padding: 0 8px;")
        status.addPermanentWidget(self._status_info)

    def _get_toolbar_icon_size(self):
        """获取工具栏图标大小"""
        from PyQt6.QtCore import QSize
        return QSize(16, 16)

    def _new_tab(self):
        """新建串口会话 Tab"""
        self._tab_counter += 1
        tab = SerialTabWidget(self._tab_counter)

        # 设置字体大小变化回调，用于保存配置
        saved_font_size = self._config.get("fontSize", 10)
        tab.display_widget.set_font_size(saved_font_size)
        tab.display_widget.set_font_size_callback(
            lambda size: self._config.set("fontSize", size)
        )

        # 连接右键菜单信号
        dw = tab.display_widget
        dw.sig_toggle_connect.connect(self._toggle_connect)
        dw.sig_toggle_pause.connect(self._toggle_pause)
        dw.sig_save_file.connect(self._save_data)

        index = self._tab_widget.addTab(tab, tab.tab_title)
        self._tab_widget.setCurrentIndex(index)

        # 定时更新 Tab 标题
        if not hasattr(self, '_title_timer'):
            self._title_timer = QTimer(self)
            self._title_timer.timeout.connect(self._update_tab_titles)
            self._title_timer.start(1000)

        return tab

    def _close_tab(self, index: int):
        """关闭指定 Tab"""
        if self._tab_widget.count() <= 1:
            QMessageBox.information(self, "提示", "至少保留一个窗口")
            return

        widget = self._tab_widget.widget(index)
        if isinstance(widget, SerialTabWidget):
            widget.cleanup()
        self._tab_widget.removeTab(index)

    def _on_tab_changed(self, index: int):
        """Tab 切换：将当前 Tab 的过滤状态同步到全局过滤面板"""
        if index < 0:
            return
        widget = self._tab_widget.widget(index)
        if isinstance(widget, SerialTabWidget):
            # 恢复过滤面板 UI（不触发信号）
            self._syncing_filter = True
            self._filter_widget.set_filter_state(widget._filter_state)
            self._syncing_filter = False
            # 将当前 Tab 的过滤应用到显示
            fs = widget._filter_state
            widget.display_widget.set_filter(
                fs["enabled"], fs["pattern"], fs["mode"],
                fs["highlight"], fs["bg_color"], fs["fg_color"],
            )

    def _update_tab_titles(self):
        """更新所有 Tab 标题"""
        for i in range(self._tab_widget.count()):
            widget = self._tab_widget.widget(i)
            if isinstance(widget, SerialTabWidget):
                self._tab_widget.setTabText(i, widget.tab_title)

    def _toggle_connect(self):
        """切换连接状态"""
        self._config_widget._toggle_connection()

    def _update_connect_button(self, connected: bool):
        """更新连接按钮状态"""
        # 连接状态由顶部串口配置栏的按钮管理

    def _update_status_info(self):
        """更新状态栏信息"""
        connected = self._serial_manager.is_connected
        rx = self._serial_manager.rx_count
        tx = self._serial_manager.tx_count
        self._update_connect_button(connected)
        if connected:
            self._status_connection.setText("[已连接]")
            self._status_connection.setStyleSheet(
                "padding: 0 8px; font-weight: bold; color: #4ec94e;"
            )
        else:
            self._status_connection.setText("[未连接]")
            self._status_connection.setStyleSheet(
                "padding: 0 8px; font-weight: bold; color: #c44545;"
            )
        self._status_rx.setText(f"RX: {rx} bytes")
        self._status_tx.setText(f"TX: {tx} bytes")

    def _toggle_pause(self):
        """切换暂停状态"""
        widget = self.current_tab
        if widget and hasattr(widget, 'display_widget'):
            paused = not widget.display_widget.is_paused
            # 将暂停/继续状态应用到所有窗口
            for i in range(self._tab_widget.count()):
                w = self._tab_widget.widget(i)
                if isinstance(w, SerialTabWidget) and hasattr(w, 'display_widget'):
                    w.display_widget.set_paused(paused)
            self._pause_action.setText("继续" if paused else "暂停")

    def _clear_display(self):
        """清空所有窗口显示"""
        for i in range(self._tab_widget.count()):
            widget = self._tab_widget.widget(i)
            if isinstance(widget, SerialTabWidget) and hasattr(widget, 'display_widget'):
                widget.display_widget.clear_display()

    def _toggle_timestamp(self):
        """切换时间戳（应用到所有 Tab）"""
        visible = self._ts_menu_action.isChecked()
        for i in range(self._tab_widget.count()):
            widget = self._tab_widget.widget(i)
            if isinstance(widget, SerialTabWidget):
                widget.display_widget.set_timestamp_visible(visible)

    def _set_display_mode(self, mode: str):
        """设置显示模式（应用到所有 Tab）"""
        self._current_mode = mode
        # 更新菜单勾选
        for action in self._mode_action_group.actions():
            if action.text() == mode:
                action.setChecked(True)
                break
        for i in range(self._tab_widget.count()):
            widget = self._tab_widget.widget(i)
            if isinstance(widget, SerialTabWidget):
                widget.display_widget.set_display_mode(mode)

    def _set_theme(self, theme: str):
        """切换主题"""
        self._config.set("theme", theme)
        QMessageBox.information(self, "主题", "主题将在下次启动时生效")

    def _refresh_ports(self):
        """刷新端口"""
        self._config_widget.refresh_ports()

    def _save_data(self):
        """保存数据"""
        widget = self.current_tab
        if not widget or not hasattr(widget, 'display_widget'):
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存数据", "serial_data.log",
            "Log Files (*.log);;Text Files (*.txt);;CSV Files (*.csv);;HEX Files (*.hex);;All Files (*)"
        )
        if not file_path:
            return

        try:
            text = widget.display_widget.get_all_text()
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text)
            self._status_info.setText(f"已保存到: {file_path}")
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"保存文件失败: {str(e)}")

    def _save_data_as(self):
        """另存为"""
        self._save_data()

    def _toggle_auto_save(self):
        """切换自动保存"""
        if self._auto_save_enabled:
            # 停止自动保存
            self._auto_save_enabled = False
            self._auto_save_timer.stop()
            self._auto_save_file = None
            self._auto_save_action.setChecked(False)
            self._status_info.setText("自动保存已停止")
        else:
            # 选择保存文件
            file_path, _ = QFileDialog.getSaveFileName(
                self, "自动保存到...", "serial_auto.log",
                "Log Files (*.log);;Text Files (*.txt);;All Files (*)"
            )
            if not file_path:
                return
            self._auto_save_enabled = True
            self._auto_save_file = file_path
            self._auto_save_timer.start()
            self._auto_save_action.setChecked(True)
            self._status_info.setText(f"自动保存中: {file_path}")

    def _do_auto_save(self):
        """执行自动保存（由定时器触发）"""
        if not self._auto_save_enabled or not self._auto_save_file:
            return
        try:
            widget = self.current_tab
            if widget and hasattr(widget, 'display_widget'):
                text = widget.display_widget.get_all_text()
                if text:
                    with open(self._auto_save_file, "w", encoding="utf-8") as f:
                        f.write(text)
        except Exception:
            pass  # 自动保存静默失败，不弹框打扰用户

    def _show_about(self):
        """关于/帮助对话框"""
        QMessageBox.about(
            self,
            "Serial Terminal - 帮助",
            """<h2>Serial Terminal v1.0.0</h2>
<p><b>Windows 串口调试工具</b></p>

<h3>📋 快捷键</h3>
<table>
<tr><td><b>F1</b></td><td>连接 / 断开串口</td></tr>
<tr><td><b>Ctrl + C</b></td><td>复制选中数据</td></tr>
<tr><td><b>Ctrl + S</b></td><td>保存当前窗口数据</td></tr>
<tr><td><b>F9</b></td><td>清空所有窗口显示</td></tr>
<tr><td><b>Ctrl + P</b></td><td>暂停 / 继续所有窗口数据显示</td></tr>
<tr><td><b>Ctrl + T</b></td><td>切换时间戳显示</td></tr>
<tr><td><b>Ctrl + N</b></td><td>新建串口窗口</td></tr>
<tr><td><b>Ctrl + W</b></td><td>关闭当前窗口</td></tr>
<tr><td><b>Ctrl + Tab</b></td><td>切换窗口</td></tr>
<tr><td><b>Ctrl + F</b></td><td>打开搜索栏</td></tr>
<tr><td><b>Enter / F4</b></td><td>搜索：查找下一个</td></tr>
<tr><td><b>Shift+Enter / F3</b></td><td>搜索：查找上一个</td></tr>
<tr><td><b>Esc</b></td><td>关闭搜索栏</td></tr>
</table>

<h3>🔍 搜索功能</h3>
<p>按 <b>Ctrl+F</b> 在数据显示区右上角打开搜索栏，输入关键词后：</p>
<ul>
<li>所有匹配项自动高亮显示</li>
<li>右上角显示匹配计数（如 3/12）</li>
<li><b>Enter</b> 或 <b>F4</b> 跳转到下一个匹配</li>
<li><b>Shift+Enter</b> 或 <b>F3</b> 跳转到上一个匹配</li>
<li>点击 <b>▲▼</b> 按钮手动切换</li>
</ul>

<h3>📂 多窗口管理</h3>
<ul>
<li>点击工具栏 <b>+ 新建窗口</b> 或按 <b>Ctrl+N</b> 创建新窗口</li>
<li>所有窗口<b>共享同一串口连接</b>，同时接收数据</li>
<li>“暂停/继续”与“清除”为<b>所有窗口通用</b>的功能，操作时将同步影响所有窗口</li>
<li>每个窗口可设置<b>独立的过滤条件</b></li>
<li>切换窗口时，右侧过滤面板自动切换为对应窗口的过滤条件</li>
</ul>

<h3>快捷指令</h3>
<ul>
<li>点击 <b>+ 添加</b> 添加新指令，支持 HEX/字符串格式</li>
<li>可设置<b>备注</b>和<b>循环发送周期</b></li>
<li><b>双击</b>指令行或选中后点击 <b>[发送选中]</b> 发送</li>
<li>支持导入/导出为 JSON 文件</li>
</ul>

<h3>数据过滤</h3>
<ul>
<li>勾选<b>启用过滤</b>，输入关键字或正则表达式</li>
<li>支持<b>白名单</b>（仅显示匹配）和<b>黑名单</b>（隐藏匹配）</li>
<li>勾选<b>高亮匹配</b>可自定义高亮颜色</li>
</ul>

<h3>数据显示</h3>
<ul>
<li>支持 <b>ASCII / HEX / HEX+ASCII</b> 三种显示模式</li>
<li>勾选<b>时间戳</b>显示每条数据的时间</li>
<li>滚动到历史位置时<b>自动停止滚动</b>，滚回底部恢复</li>
</ul>
"""
        )

    # ---- 全局串口回调 ----

    def _on_global_data_received(self, data: bytes):
        """全局串口数据接收，分发给所有 Tab"""
        for i in range(self._tab_widget.count()):
            widget = self._tab_widget.widget(i)
            if isinstance(widget, SerialTabWidget):
                widget.on_data_received(data)

    def _on_global_error(self, error_msg: str):
        print(f"串口错误: {error_msg}")

    def _on_global_disconnected(self):
        """串口异常断开"""
        self._config_widget.update_connection_state(False)
        self._send_widget.stop_timer()

    def _on_filter_changed(self, enabled: bool, pattern: str, mode: str,
                            highlight: bool, bg_color: str = "#ffff00",
                            fg_color: str = "#000000"):
        """全局过滤变更，仅更新当前 Tab"""
        if getattr(self, '_syncing_filter', False):
            return  # 正在同步 Tab 切换，不重复处理

        widget = self.current_tab
        if widget:
            widget._filter_state = {
                "enabled": enabled,
                "pattern": pattern,
                "mode": mode,
                "highlight": highlight,
                "bg_color": bg_color,
                "fg_color": fg_color,
            }
            widget.display_widget.set_filter(enabled, pattern, mode, highlight,
                                              bg_color, fg_color)

    def _on_send_requested(self, data: str, fmt: str):
        """发送数据（全局发送面板）"""
        if fmt == "HEX":
            success, msg = self._serial_manager.send_hex(data)
        else:
            # 同时支持字面量 \r\n 和真正的控制字符
            actual_data = data.replace("\\r\\n", "\r\n").replace("\\r", "\r").replace("\\n", "\n")
            success, msg = self._serial_manager.send_data(actual_data.encode("utf-8"))

        # 发送成功后，在所有 Tab 中显示发送的数据
        if success:
            for i in range(self._tab_widget.count()):
                widget = self._tab_widget.widget(i)
                if isinstance(widget, SerialTabWidget):
                    widget.on_data_sent(data, fmt)

    # ---- 属性与方法 ----

    @property
    def current_tab(self):
        widget = self._tab_widget.currentWidget()
        if isinstance(widget, SerialTabWidget):
            return widget
        return None

    def _restore_config(self):
        """恢复配置"""
        # 窗口位置
        geometry = self._config.get("windowGeometry")
        if geometry:
            try:
                from PyQt6.QtCore import QByteArray
                self.restoreGeometry(QByteArray(bytes(geometry)))
            except Exception:
                pass

        # 快捷指令
        quick_commands = self._config.get("quickCommands", [])
        if quick_commands:
            self._send_widget.set_quick_commands(quick_commands)

        # 串口配置
        last_config = self._config.get("lastSerialConfig", {})
        self._config_widget.set_config_from_dict(last_config)

        # 恢复各窗口配置（过滤 + 显示模式 + 时间戳）
        tab_configs = self._config.get("tabConfigs", [])
        # 如果保存的窗口数多于当前，先创建
        while self._tab_widget.count() < len(tab_configs):
            self._new_tab()
        for i, cfg in enumerate(tab_configs):
            if i < self._tab_widget.count():
                widget = self._tab_widget.widget(i)
                if isinstance(widget, SerialTabWidget):
                    widget.set_tab_config(cfg)

        # 恢复上次打开的 Tab（会触发 _on_tab_changed 同步过滤面板）
        last_tab = self._config.get("lastOpenedTab", 0)
        if last_tab < self._tab_widget.count():
            self._tab_widget.setCurrentIndex(last_tab)
        else:
            # 确保过滤面板初始化
            self._on_tab_changed(0)

    def _collect_config(self):
        """收集当前所有配置"""
        # 串口配置
        config = self._config_widget.get_config()
        self._config.data["lastSerialConfig"] = config.to_dict()

        # 快捷指令
        commands = self._send_widget.get_quick_commands()
        self._config.data["quickCommands"] = [c.to_dict() for c in commands]

        # 各窗口配置
        tab_configs = []
        for i in range(self._tab_widget.count()):
            widget = self._tab_widget.widget(i)
            if isinstance(widget, SerialTabWidget):
                tab_configs.append(widget.get_tab_config())
        self._config.data["tabConfigs"] = tab_configs

        self._config.data["lastOpenedTab"] = self._tab_widget.currentIndex()

    def closeEvent(self, event):
        """关闭事件"""
        geometry = self.saveGeometry()
        if geometry:
            self._config.data["windowGeometry"] = [int.from_bytes(b, 'big') for b in geometry]
        else:
            self._config.data["windowGeometry"] = None

        self._collect_config()
        self._config.save()

        if self._serial_manager.is_connected:
            self._serial_manager.disconnect()

        self._send_widget.stop_timer()
        if self._auto_save_enabled:
            self._auto_save_timer.stop()
        for i in range(self._tab_widget.count()):
            widget = self._tab_widget.widget(i)
            if isinstance(widget, SerialTabWidget):
                widget.cleanup()

        event.accept()
