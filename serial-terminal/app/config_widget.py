"""
串口配置面板组件
提供端口选择、波特率、数据位、停止位、校验位、流控制等参数配置
"""

from typing import Callable, List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QGroupBox, QSpinBox, QCheckBox, QFrame,
    QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from app.serial_manager import SerialManager, SerialConfig, SerialPortInfo


class SerialConfigWidget(QGroupBox):
    """串口配置面板"""

    connect_requested = pyqtSignal(SerialConfig)
    disconnect_requested = pyqtSignal()

    def __init__(self, serial_manager: SerialManager, parent=None):
        super().__init__("串口配置", parent)
        self._serial_manager = serial_manager
        self._baud_rates = [
            9600, 19200, 38400, 57600, 115200,
            256000, 1000000, 2000000, 3000000
        ]
        self._compact = False
        self._setup_ui()

    def set_compact_mode(self, compact: bool):
        """设置紧凑模式（水平布局，用于顶部工具栏）"""
        self._compact = compact
        # 清空并重建布局
        old_layout = self.layout()
        if old_layout:
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
            QWidget().setLayout(old_layout)
        self._setup_ui()

    def _setup_ui(self):
        if self._compact:
            self._setup_compact_ui()
        else:
            self._setup_normal_ui()

    def _setup_compact_ui(self):
        """紧凑水平布局（用于顶部工具栏）"""
        self.setTitle("")
        self.setFlat(True)
        self.setStyleSheet(
            "QGroupBox { border: none; margin-top: 0; padding-top: 0; }"
        )
        layout = QHBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(2, 2, 2, 2)

        # 端口
        layout.addWidget(QLabel("端口:"))
        self._port_combo = QComboBox()
        self._port_combo.setMinimumWidth(100)
        self._port_combo.setMaximumWidth(150)
        layout.addWidget(self._port_combo)

        self._refresh_btn = QPushButton("刷新")
        self._refresh_btn.setFixedWidth(55)
        self._refresh_btn.clicked.connect(self.refresh_ports)
        layout.addWidget(self._refresh_btn)

        layout.addWidget(self._vsep())

        # 波特率
        layout.addWidget(QLabel("波特率:"))
        self._baud_combo = QComboBox()
        self._baud_combo.setEditable(True)
        self._baud_combo.setMaximumWidth(100)
        for rate in self._baud_rates:
            self._baud_combo.addItem(str(rate))
        self._baud_combo.setCurrentText("115200")
        layout.addWidget(self._baud_combo)

        layout.addWidget(self._vsep())

        # 数据位
        layout.addWidget(QLabel("数据位:"))
        self._data_bits_combo = QComboBox()
        self._data_bits_combo.setMaximumWidth(55)
        for b in [5, 6, 7, 8]:
            self._data_bits_combo.addItem(str(b))
        self._data_bits_combo.setCurrentText("8")
        layout.addWidget(self._data_bits_combo)

        # 停止位
        layout.addWidget(QLabel("停止位:"))
        self._stop_bits_combo = QComboBox()
        self._stop_bits_combo.setMaximumWidth(55)
        for s in [1, 1.5, 2]:
            self._stop_bits_combo.addItem(str(s))
        self._stop_bits_combo.setCurrentText("1")
        layout.addWidget(self._stop_bits_combo)

        # 校验位
        layout.addWidget(QLabel("校验:"))
        self._parity_combo = QComboBox()
        self._parity_combo.setMaximumWidth(70)
        self._parity_combo.addItems(["None", "Odd", "Even", "Mark", "Space"])
        layout.addWidget(self._parity_combo)

        # 流控制
        layout.addWidget(QLabel("流控:"))
        self._flow_combo = QComboBox()
        self._flow_combo.setMaximumWidth(120)
        self._flow_combo.addItems(["None", "Hardware(RTS/CTS)", "Software(XON/XOFF)"])
        layout.addWidget(self._flow_combo)

        layout.addWidget(self._vsep())

        # 连接按钮
        self._connect_btn = QPushButton("连接")
        self._connect_btn.setFixedWidth(55)
        self._connect_btn.clicked.connect(self._toggle_connection)
        layout.addWidget(self._connect_btn)

        # RTS/DTR
        self._rts_cb = QCheckBox("RTS")
        self._rts_cb.toggled.connect(self._on_rts_toggled)
        layout.addWidget(self._rts_cb)
        self._dtr_cb = QCheckBox("DTR")
        self._dtr_cb.toggled.connect(self._on_dtr_toggled)
        layout.addWidget(self._dtr_cb)

        layout.addStretch()
        self.refresh_ports()

    def _vsep(self):
        """垂直分隔线"""
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet("color: #555;")
        return sep

    def _setup_normal_ui(self):
        """常规垂直布局"""
        self.setTitle("串口配置")
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(8, 16, 8, 8)

        # 端口选择
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("端口:"))
        self._port_combo = QComboBox()
        self._port_combo.setMinimumWidth(120)
        port_layout.addWidget(self._port_combo, 1)
        self._refresh_btn = QPushButton("刷新")
        self._refresh_btn.setFixedWidth(60)
        self._refresh_btn.clicked.connect(self.refresh_ports)
        port_layout.addWidget(self._refresh_btn)
        layout.addLayout(port_layout)

        # 波特率
        baud_layout = QHBoxLayout()
        baud_layout.addWidget(QLabel("波特率:"))
        self._baud_combo = QComboBox()
        self._baud_combo.setEditable(True)
        for rate in self._baud_rates:
            self._baud_combo.addItem(str(rate))
        self._baud_combo.setCurrentText("115200")
        baud_layout.addWidget(self._baud_combo, 1)
        layout.addLayout(baud_layout)

        # 数据位
        bits_layout = QHBoxLayout()
        bits_layout.addWidget(QLabel("数据位:"))
        self._data_bits_combo = QComboBox()
        for b in [5, 6, 7, 8]:
            self._data_bits_combo.addItem(str(b))
        self._data_bits_combo.setCurrentText("8")
        bits_layout.addWidget(self._data_bits_combo)
        bits_layout.addStretch()
        layout.addLayout(bits_layout)

        # 停止位
        stop_layout = QHBoxLayout()
        stop_layout.addWidget(QLabel("停止位:"))
        self._stop_bits_combo = QComboBox()
        for s in [1, 1.5, 2]:
            self._stop_bits_combo.addItem(str(s))
        self._stop_bits_combo.setCurrentText("1")
        stop_layout.addWidget(self._stop_bits_combo)
        stop_layout.addStretch()
        layout.addLayout(stop_layout)

        # 校验位
        parity_layout = QHBoxLayout()
        parity_layout.addWidget(QLabel("校验位:"))
        self._parity_combo = QComboBox()
        self._parity_combo.addItems(["None", "Odd", "Even", "Mark", "Space"])
        parity_layout.addWidget(self._parity_combo)
        parity_layout.addStretch()
        layout.addLayout(parity_layout)

        # 流控制
        flow_layout = QHBoxLayout()
        flow_layout.addWidget(QLabel("流控制:"))
        self._flow_combo = QComboBox()
        self._flow_combo.addItems(["None", "Hardware(RTS/CTS)", "Software(XON/XOFF)"])
        flow_layout.addWidget(self._flow_combo)
        flow_layout.addStretch()
        layout.addLayout(flow_layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        self._connect_btn = QPushButton("连接")
        self._connect_btn.clicked.connect(self._toggle_connection)
        layout.addWidget(self._connect_btn)

        rts_layout = QHBoxLayout()
        self._rts_cb = QCheckBox("RTS")
        self._rts_cb.toggled.connect(self._on_rts_toggled)
        rts_layout.addWidget(self._rts_cb)
        self._dtr_cb = QCheckBox("DTR")
        self._dtr_cb.toggled.connect(self._on_dtr_toggled)
        rts_layout.addWidget(self._dtr_cb)
        rts_layout.addStretch()
        layout.addLayout(rts_layout)

        layout.addStretch()
        self.refresh_ports()

    def refresh_ports(self):
        """刷新端口列表"""
        current_port = self._port_combo.currentText()
        self._port_combo.clear()

        ports = SerialManager.scan_ports()
        for p in ports:
            self._port_combo.addItem(p.display_name, p.device)

        # 恢复之前选中的端口
        for i in range(self._port_combo.count()):
            if self._port_combo.itemData(i) == current_port or \
               self._port_combo.itemText(i).startswith(current_port):
                self._port_combo.setCurrentIndex(i)
                break

    def get_config(self) -> SerialConfig:
        """获取当前配置"""
        port = self._port_combo.currentData()
        if not port and self._port_combo.currentText():
            port = self._port_combo.currentText().split(" - ")[0]

        return SerialConfig(
            port=port or "",
            baudrate=int(self._baud_combo.currentText()),
            bytesize=int(self._data_bits_combo.currentText()),
            parity=self._parity_combo.currentText(),
            stopbits=float(self._stop_bits_combo.currentText()),
            flowcontrol=self._flow_combo.currentText(),
        )

    def _toggle_connection(self):
        """切换连接状态"""
        if self._serial_manager.is_connected:
            self._serial_manager.disconnect()
            self._update_connection_state(False)
        else:
            config = self.get_config()
            if not config.port:
                QMessageBox.warning(self, "警告", "请选择串口端口")
                return
            success, msg = self._serial_manager.connect(config)
            if success:
                self._update_connection_state(True)
            else:
                QMessageBox.critical(self, "连接失败", msg)

    def _update_connection_state(self, connected: bool):
        """更新连接状态显示"""
        if connected:
            self._connect_btn.setText("断开")
            self._connect_btn.setStyleSheet("background-color: #c44545;")
            self._set_config_enabled(False)
        else:
            self._connect_btn.setText("连接")
            self._connect_btn.setStyleSheet("")
            self._set_config_enabled(True)
            self._rts_cb.setChecked(False)
            self._dtr_cb.setChecked(False)

    def _set_config_enabled(self, enabled: bool):
        """设置配置区域是否可用"""
        self._port_combo.setEnabled(enabled)
        self._refresh_btn.setEnabled(enabled)
        self._baud_combo.setEnabled(enabled)
        self._data_bits_combo.setEnabled(enabled)
        self._stop_bits_combo.setEnabled(enabled)
        self._parity_combo.setEnabled(enabled)
        self._flow_combo.setEnabled(enabled)

    def _on_rts_toggled(self, checked: bool):
        self._serial_manager.set_rts(checked)

    def _on_dtr_toggled(self, checked: bool):
        self._serial_manager.set_dtr(checked)

    def update_connection_state(self, connected: bool):
        """外部更新连接状态（如异常断开时）"""
        self._update_connection_state(connected)

    def set_config_from_dict(self, config: dict):
        """从字典恢复串口配置"""
        if not config:
            return
        port = config.get("port", "")
        if port:
            for i in range(self._port_combo.count()):
                if self._port_combo.itemData(i) == port or \
                   self._port_combo.itemText(i).startswith(port):
                    self._port_combo.setCurrentIndex(i)
                    break
        baud = str(config.get("baudrate", 115200))
        self._baud_combo.setCurrentText(baud)
        self._data_bits_combo.setCurrentText(str(config.get("bytesize", 8)))
        self._stop_bits_combo.setCurrentText(str(config.get("stopbits", 1)))
        self._parity_combo.setCurrentText(config.get("parity", "None"))
        self._flow_combo.setCurrentText(config.get("flowcontrol", "None"))
