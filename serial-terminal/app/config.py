"""
配置管理模块
负责配置文件的读写、默认配置管理
"""

import json
import os
import sys
from typing import Any, Dict, Optional


def _get_config_dir() -> str:
    """获取配置目录（exe 打包后也能正常写入）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，使用 exe 所在目录
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return base


DEFAULT_CONFIG_PATH = os.path.join(_get_config_dir(), "config.json")

DEFAULT_CONFIG = {
    "theme": "dark",
    "language": "zh-CN",
    "maxDisplayLines": 10000,
    "autoReconnect": False,
    "logDir": "./logs",
    "autoLog": False,
    "logFileSplitSize": 10,
    "recentPorts": [],
    "quickCommands": [],
    "windowGeometry": None,
    "lastOpenedTab": 0,
    # 串口配置
    "lastSerialConfig": {
        "port": "",
        "baudrate": 115200,
        "bytesize": 8,
        "parity": "None",
        "stopbits": 1,
        "flowcontrol": "None",
    },
    # 各窗口配置列表（过滤条件 + 显示模式 + 时间戳）
    "tabConfigs": [],
    "baudRates": [9600, 19200, 38400, 57600, 115200, 256000, 1000000, 2000000, 3000000],
    "dataBits": [5, 6, 7, 8],
    "stopBits": [1, 1.5, 2],
    "parities": ["None", "Odd", "Even", "Mark", "Space"],
    "flowControls": ["None", "Hardware(RTS/CTS)", "Software(XON/XOFF)"],
}


class AppConfig:
    """应用程序配置管理器"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.data: Dict[str, Any] = {}

    def load(self):
        """加载配置文件，如果不存在则使用默认配置"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.data = {**DEFAULT_CONFIG, **loaded}
            except (json.JSONDecodeError, IOError):
                self.data = dict(DEFAULT_CONFIG)
        else:
            self.data = dict(DEFAULT_CONFIG)
            self.save()

    def save(self):
        """保存配置到文件"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"保存配置文件失败: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self.data.get(key, default)

    def set(self, key: str, value: Any):
        """设置配置项并保存"""
        self.data[key] = value
        self.save()
