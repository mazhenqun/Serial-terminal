# Serial Terminal - Windows 串口调试工具

一个现代化的 Windows 桌面串口调试工具，基于 **Python + PyQt6 + pyserial** 构建。

## ✨ 功能特性

- **串口连接管理** — 端口扫描、波特率(自定义)、数据位、停止位、校验位、流控制、RTS/DTR
- **多窗口会话** — 支持创建多个窗口，共享同一串口连接，各窗口独立过滤
- **数据显示** — ASCII / HEX / HEX+ASCII 三种模式，时间戳、行号、智能滚动
- **数据过滤** — 关键字/正则过滤，白名单/黑名单，自定义高亮颜色
- **快捷指令** — 支持 HEX/字符串格式，备注、循环发送周期，导入/导出 JSON
- **数据搜索** — Ctrl+F 搜索，高亮匹配，支持上/下一个跳转
- **配置持久化** — 自动保存串口配置、窗口布局、过滤条件、快捷指令
- **深色主题** — 现代化 VS Code 风格深色 UI

## ⌨️ 快捷键

| 快捷键 | 功能 |
|--------|------|
| `F1` | 连接 / 断开串口 |
| `Ctrl + C` | 复制 |
| `Ctrl + A` | 全选 |
| `Ctrl + F` | 搜索 |
| `Ctrl + S` | 保存数据 |
| `Ctrl + N` | 新建窗口 |
| `Ctrl + W` | 关闭窗口 |
| `Ctrl + P` | 暂停 / 继续 |
| `Ctrl + T` | 切换时间戳 |
| `Esc` | 关闭搜索栏 |
| `Enter / F4` | 查找下一个 |
| `Shift+Enter / F3` | 查找上一个 |

## 📦 项目结构

```
serial-terminal/
├── main.py              # 程序入口
├── requirements.txt     # Python 依赖
├── app/
│   ├── config.py        # 配置管理
│   ├── serial_manager.py # 串口通信核心
│   ├── config_widget.py  # 串口配置面板
│   ├── display_widget.py # 数据显示组件
│   ├── filter_widget.py  # 数据过滤组件
│   ├── send_widget.py    # 数据发送组件
│   ├── serial_tab.py     # 串口会话 Tab
│   └── main_window.py    # 主窗口
└── dist/
    └── SerialTerminal.exe  # 打包好的可执行文件
```

## 🚀 运行方式

### 直接运行 exe
双击 `serial-terminal/dist/SerialTerminal.exe`

### 开发环境
```bash
cd serial-terminal
pip install -r requirements.txt
python main.py
```

## 🛠 技术栈

- **UI 框架**: PyQt6
- **串口通信**: pyserial
- **打包工具**: PyInstaller

## 📄 License

MIT
