# SteamCMD 票据提取工具

简单易用的 Steam Denuvo 双票据（appticket / eticket）提取工具。

---

## 📦 快速下载（免安装版）

直接下载解包即可开箱即用：
- **下载地址**：[v1.zip (GitHub Releases)](https://www.github.com/hatott89-maker/steamcmd-extract-tickets/releases/download/v1.0.0/v1.zip)

解压后包含内容：
- `SteamCMD-Ticket-Extractor.exe`：图形界面主程序
- `steamcmd/`：已配置好劫持依赖与提取工具的运行环境
- `config.json`：默认配置文件

> **相关开源项目**：
> 核心劫持与提取插件源码：[BetterSteamTools-ddev2z (version.dll 源码)](https://github.com/hatott89-maker/BetterSteamTools-ddev2z)

---

## 🚀 使用说明

打开客户端后，按图示依次操作即可：

1. **SteamCMD 目录**：选择解压后的 `steamcmd` 目录路径。
2. **AppID (游戏编号)**：输入要提取票据的游戏编号（如 `1091500`、`2358720` 等）。
3. **Steam 账号**：输入拥有该游戏授权的 Steam 账号。
4. **Steam 密码**：输入对应的登录密码。
5. **开始提取**：点击蓝色“开始提取”按钮。
   - 若账号触发了安全验证，程序会自动弹出窗口，输入手机令牌或邮箱验证码后确认即可。
   - 提取完成后，右侧会自动填充 `appticket` 与 `eticket`，并在对应的 `<AppID>/tickets.txt` 中生成结果。

---

## 💻 Python 源码启动方式

如需通过源码直接运行：

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 启动运行
```bash
python main.py
```

### 3. 打包生成 EXE（可选）
```bash
python build_exe.py --onedir
```
