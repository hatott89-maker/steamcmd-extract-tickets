# SteamCMD Ticket Extractor (极简桌面版)

极简纯白现代 PyQt6 桌面客户端，直连本地 `steamcmd.exe` 与 `extract_tickets.exe`，专注 Denuvo 授权双票据提取。

## 项目结构

```
D:\py-project\steamcmd-extract-tickets\
├── core/
│   └── steamcmd_direct.py      # 单机直连驱动引擎 (Win32 Console API)
├── gui/
│   ├── styles.py               # 现代极简轻奢白 QSS 样式
│   ├── components.py           # 卡片、状态胶囊、代码块复制条、彩色日志框
│   └── main_window.py          # 单页主窗口 (账号/密码/2FA 令牌输入与产物展示)
├── main.py                     # 主入口
├── build_exe.py                # PyInstaller 打包脚本
├── config.py / config.json     # 配置文件
└── requirements.txt            # 依赖清单
```

## 运行与打包

```powershell
# 运行程序
.\.venv\Scripts\python.exe main.py

# 打包为单目录 EXE
.\.venv\Scripts\python.exe build_exe.py --onedir
```
