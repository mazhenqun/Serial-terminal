"""
串口通信管理模块
封装 pyserial，提供端口扫描、连接管理、数据收发等功能
"""

import threading
import time
from typing import Callable, Dict, List, Optional, Tuple

import serial
import serial.tools.list_ports


class SerialPortInfo:
    """串口端口信息"""

    def __init__(self, device: str, description: str = "", hwid: str = ""):
        self.device = device
        self.description = description
        self.hwid = hwid

    @property
    def display_name(self) -> str:
        """显示名称"""
        if self.description:
            return f"{self.device} - {self.description}"
        return self.device

    def __str__(self):
        return self.display_name


class SerialConfig:
    """串口配置参数"""

    def __init__(
        self,
        port: str = "",
        baudrate: int = 2000000,
        bytesize: int = 8,
        parity: str = "None",
        stopbits: float = 1.0,
        flowcontrol: str = "None",
        timeout: float = 0.05,
    ):
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.flowcontrol = flowcontrol
        self.timeout = timeout

    def to_dict(self) -> dict:
        return {
            "port": self.port,
            "baudrate": self.baudrate,
            "bytesize": self.bytesize,
            "parity": self.parity,
            "stopbits": self.stopbits,
            "flowcontrol": self.flowcontrol,
        }

    @staticmethod
    def parity_to_serial(parity: str) -> str:
        mapping = {"None": "N", "Odd": "O", "Even": "E", "Mark": "M", "Space": "S"}
        return mapping.get(parity, "N")

    @staticmethod
    def flowcontrol_to_serial(flowcontrol: str) -> Tuple[bool, bool]:
        if flowcontrol == "Hardware(RTS/CTS)":
            return True, False  # rtscts, xonxoff
        elif flowcontrol == "Software(XON/XOFF)":
            return False, True
        return False, False

    def to_serial_kwargs(self) -> dict:
        rtscts, xonxoff = self.flowcontrol_to_serial(self.flowcontrol)
        return {
            "port": self.port,
            "baudrate": self.baudrate,
            "bytesize": self.bytesize,
            "parity": self.parity_to_serial(self.parity),
            "stopbits": self.stopbits,
            "timeout": self.timeout,
            "rtscts": rtscts,
            "xonxoff": xonxoff,
        }


class SerialManager:
    """串口管理器 - 管理单个串口的连接与通信"""

    def __init__(self):
        self._serial: Optional[serial.Serial] = None
        self._read_thread: Optional[threading.Thread] = None
        self._running = False
        self._config = SerialConfig()
        self._rx_count = 0
        self._tx_count = 0
        self._on_data_received: Optional[Callable[[bytes], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
        self._on_disconnected: Optional[Callable[[], None]] = None
        self._lock = threading.Lock()

    @property
    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    @property
    def config(self) -> SerialConfig:
        return self._config

    @property
    def rx_count(self) -> int:
        return self._rx_count

    @property
    def tx_count(self) -> int:
        return self._tx_count

    def set_on_data_received(self, callback: Callable[[bytes], None]):
        self._on_data_received = callback

    def set_on_error(self, callback: Callable[[str], None]):
        self._on_error = callback

    def set_on_disconnected(self, callback: Callable[[], None]):
        self._on_disconnected = callback

    @staticmethod
    def scan_ports() -> List[SerialPortInfo]:
        """扫描可用串口"""
        ports = []
        try:
            for p in serial.tools.list_ports.comports():
                ports.append(SerialPortInfo(p.device, p.description, p.hwid))
        except Exception:
            pass
        return ports

    def connect(self, config: SerialConfig) -> Tuple[bool, str]:
        """连接串口"""
        if self.is_connected:
            return False, "已经连接"

        try:
            kwargs = config.to_serial_kwargs()
            self._serial = serial.Serial(**kwargs)
            self._config = config
            self._rx_count = 0
            self._tx_count = 0
            self._running = True

            # 启动接收线程
            self._read_thread = threading.Thread(
                target=self._read_loop, daemon=True, name=f"SerialRead-{config.port}"
            )
            self._read_thread.start()

            return True, "连接成功"
        except serial.SerialException as e:
            return False, f"连接失败: {str(e)}"

    def disconnect(self):
        """断开串口连接"""
        self._running = False
        if self._read_thread and self._read_thread.is_alive():
            self._read_thread.join(timeout=1.0)

        with self._lock:
            if self._serial and self._serial.is_open:
                try:
                    self._serial.close()
                except Exception:
                    pass
            self._serial = None

    def send_data(self, data: bytes) -> Tuple[bool, str]:
        """发送数据"""
        if not self.is_connected:
            return False, "串口未连接"

        try:
            with self._lock:
                written = self._serial.write(data)
                self._tx_count += written
            return True, f"已发送 {written} 字节"
        except serial.SerialException as e:
            return False, f"发送失败: {str(e)}"

    def send_hex(self, hex_str: str) -> Tuple[bool, str]:
        """发送十六进制字符串 (如 "7E 01 00 00")"""
        try:
            # 移除空格并转换
            hex_str = hex_str.strip().replace(" ", "")
            if not hex_str:
                return False, "数据为空"
            if len(hex_str) % 2 != 0:
                return False, "十六进制字符串长度无效"
            data = bytes.fromhex(hex_str)
            return self.send_data(data)
        except ValueError as e:
            return False, f"十六进制格式错误: {str(e)}"

    def set_rts(self, level: bool) -> bool:
        """设置 RTS 信号"""
        if self.is_connected:
            try:
                self._serial.rts = level
                return True
            except Exception:
                pass
        return False

    def set_dtr(self, level: bool) -> bool:
        """设置 DTR 信号"""
        if self.is_connected:
            try:
                self._serial.dtr = level
                return True
            except Exception:
                pass
        return False

    def _read_loop(self):
        """串口数据读取循环（后台线程）"""
        import traceback
        log_path = None
        try:
            import os
            log_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "crash.log"
            )
        except Exception:
            pass

        while self._running:
            try:
                if self._serial and self._serial.is_open and self._serial.in_waiting > 0:
                    data = self._serial.read(self._serial.in_waiting)
                    if data:
                        self._rx_count += len(data)
                        if self._on_data_received:
                            self._on_data_received(data)
                else:
                    time.sleep(0.001)
            except serial.SerialException as e:
                if log_path:
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(f"[SerialException] {e}\n")
                    except Exception:
                        pass
                if self._on_disconnected:
                    self._on_disconnected()
                break
            except Exception as e:
                if log_path:
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(f"[ReadThread Error] {e}\n")
                            traceback.print_exc(file=f)
                    except Exception:
                        pass
                if self._on_error:
                    self._on_error(f"接收错误: {str(e)}")
                break

        # 线程结束时确保清理
        if self._running:  # 非主动断开
            self._running = False
            if self._on_disconnected:
                self._on_disconnected()

    def reset_counts(self):
        """重置计数"""
        self._rx_count = 0
        self._tx_count = 0
