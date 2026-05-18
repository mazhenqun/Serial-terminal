#!/usr/bin/env python3
"""
Serial Terminal - Windows 串口调试工具
主入口文件
"""

import sys
import os
import traceback
from datetime import datetime


def _get_exe_dir() -> str:
    """获取 exe 所在目录（打包后也能正确获取）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# 确保 resources 目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CRASH_LOG_PATH = os.path.join(_get_exe_dir(), "crash.log")


def _write_crash_log(exc_type, exc_value, exc_tb):
    """将崩溃信息写入日志文件"""
    try:
        with open(CRASH_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n===== {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====\n")
            f.write(f"异常类型: {exc_type.__name__}\n")
            f.write(f"异常信息: {exc_value}\n")
            f.write("堆栈跟踪:\n")
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
            f.write("\n")
    except Exception:
        pass


def global_excepthook(exc_type, exc_value, exc_tb):
    """全局未捕获异常处理"""
    _write_crash_log(exc_type, exc_value, exc_tb)
    sys.__excepthook__(exc_type, exc_value, exc_tb)


sys.excepthook = global_excepthook


def main():
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt

    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName("Serial Terminal")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("SerialTerminal")

    # 加载配置
    from app.config import AppConfig
    config = AppConfig()
    config.load()

    # 设置样式
    _apply_theme(app, config.data.get("theme", "dark"))

    from app.main_window import MainWindow
    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())


def _apply_theme(app, theme: str):
    """应用主题"""
    if theme == "dark":
        app.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
            QMenuBar {
                background-color: #2d2d2d;
                color: #d4d4d4;
            }
            QMenuBar::item:selected {
                background-color: #094771;
            }
            QMenu {
                background-color: #2d2d2d;
                color: #d4d4d4;
            }
            QMenu::item:selected {
                background-color: #094771;
            }
            QToolBar {
                background-color: #2d2d2d;
                border-bottom: 1px solid #3c3c3c;
                spacing: 4px;
                padding: 2px;
            }
            QToolButton {
                background-color: #2d2d2d;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 4px 10px;
                min-height: 24px;
            }
            QToolButton:hover {
                background-color: #094771;
                border-color: #1a8ad4;
            }
            QToolButton:checked {
                background-color: #094771;
                border-color: #1a8ad4;
            }
            QTabWidget::pane {
                border: 1px solid #3c3c3c;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #9d9d9d;
                border: 1px solid #3c3c3c;
                border-bottom: none;
                padding: 6px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                color: #ffffff;
                border-bottom: 1px solid #1e1e1e;
            }
            QTabBar::tab:hover:!selected {
                color: #d4d4d4;
            }
            QGroupBox {
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 16px;
                font-weight: bold;
                color: #d4d4d4;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QLabel {
                color: #d4d4d4;
            }
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
            QPushButton:pressed {
                background-color: #094771;
            }
            QPushButton:disabled {
                background-color: #3c3c3c;
                color: #6e6e6e;
            }
            QComboBox {
                background-color: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px 8px;
                min-height: 24px;
            }
            QComboBox:hover {
                border-color: #1a8ad4;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #d4d4d4;
                selection-background-color: #094771;
                border: 1px solid #3c3c3c;
            }
            QSpinBox, QLineEdit {
                background-color: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px 8px;
                min-height: 24px;
            }
            QSpinBox:focus, QLineEdit:focus {
                border-color: #1a8ad4;
            }
            QCheckBox {
                color: #d4d4d4;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QRadioButton {
                color: #d4d4d4;
                spacing: 6px;
            }
            QTextEdit, QPlainTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                selection-background-color: #264f78;
            }
            QListWidget {
                background-color: #252526;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
            }
            QListWidget::item:selected {
                background-color: #094771;
            }
            QListWidget::item:hover {
                background-color: #2a2d2e;
            }
            QStatusBar {
                background-color: #007acc;
                color: white;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 10px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #424242;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #555555;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                background-color: #1e1e1e;
                height: 10px;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background-color: #424242;
                border-radius: 5px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #555555;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QSplitter::handle {
                background-color: #3c3c3c;
            }
            QSplitter::handle:horizontal {
                width: 2px;
            }
            QSplitter::handle:vertical {
                height: 2px;
            }
        """)


if __name__ == "__main__":
    main()
