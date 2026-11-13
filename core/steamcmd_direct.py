# -*- coding: utf-8 -*-
"""
SteamCMD 本地直连提取引擎 (无沙箱/无HTTP池/纯直连)
直接驱动指定目录下的 steamcmd.exe 与 extract_tickets.exe 完成登录与双票据提取。
"""
import ctypes
from ctypes import wintypes
import logging
from pathlib import Path
import re
import subprocess
import time
from typing import Optional, List, Dict, Any, Tuple, Callable
from config import cfg

logger = logging.getLogger("SteamCMDDirect")

kernel32 = ctypes.windll.kernel32

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
OPEN_EXISTING = 3


class COORD(ctypes.Structure):
    _fields_ = [('X', wintypes.SHORT), ('Y', wintypes.SHORT)]


class SMALL_RECT(ctypes.Structure):
    _fields_ = [
        ('Left', wintypes.SHORT),
        ('Top', wintypes.SHORT),
        ('Right', wintypes.SHORT),
        ('Bottom', wintypes.SHORT)
    ]


class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
    _fields_ = [
        ('dwSize', COORD),
        ('dwCursorPosition', COORD),
        ('wAttributes', wintypes.WORD),
        ('srWindow', SMALL_RECT),
        ('dwMaximumWindowSize', COORD)
    ]


class KEY_EVENT_RECORD(ctypes.Structure):
    _fields_ = [
        ('bKeyDown', wintypes.BOOL),
        ('wRepeatCount', wintypes.WORD),
        ('wVirtualKeyCode', wintypes.WORD),
        ('wVirtualScanCode', wintypes.WORD),
        ('uChar', wintypes.WCHAR),
        ('dwControlKeyState', wintypes.DWORD)
    ]


class _Event(ctypes.Union):
    _fields_ = [('KeyEvent', KEY_EVENT_RECORD)]


class INPUT_RECORD(ctypes.Structure):
    _fields_ = [
        ('EventType', wintypes.WORD),
        ('Event', _Event)
    ]


class SteamCMDDirectExtractor:
    """单机直连提取器"""

    def __init__(
        self,
        steamcmd_dir: Path,
        show_steamcmd_console: bool = False,
        show_extract_console: bool = False,
        on_log: Optional[Callable[[str, str], None]] = None,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_need_guard_code: Optional[Callable[[str], Optional[str]]] = None,
    ):
        self.work_dir = Path(steamcmd_dir)
        self.show_steamcmd_console = show_steamcmd_console
        self.show_extract_console = show_extract_console
        self.on_log = on_log or (lambda lvl, msg: None)
        self.on_progress = on_progress or (lambda pct, desc: None)
        self.on_need_guard_code = on_need_guard_code

        self.steamcmd_exe = self.work_dir / "steamcmd.exe"
        self.extract_exe = self.work_dir / "extract_tickets.exe"

        self.process: Optional[subprocess.Popen] = None
        self.h_in = None
        self.h_out = None
        self.is_attached = False
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True
        self.terminate()

    def _log(self, msg: str, level: str = "INFO"):
        self.on_log(level, msg)

    def _progress(self, pct: int, desc: str):
        self.on_progress(pct, desc)

    def _start_steamcmd(self):
        if not self.steamcmd_exe.exists():
            raise FileNotFoundError(f"未找到 steamcmd.exe，请检查路径: {self.steamcmd_exe}")
        if not self.extract_exe.exists():
            raise FileNotFoundError(f"未找到 extract_tickets.exe，请检查路径: {self.extract_exe}")

        creationflags = (
            subprocess.CREATE_NEW_CONSOLE
            if self.show_steamcmd_console
            else getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        )

        self._log(f"正在启动 steamcmd.exe ({'显示窗口' if self.show_steamcmd_console else '静默运行'})...")
        self.process = subprocess.Popen(
            [str(self.steamcmd_exe)],
            cwd=str(self.work_dir),
            creationflags=creationflags
        )

        time.sleep(1.5)
        kernel32.FreeConsole()
        if kernel32.AttachConsole(self.process.pid):
            self.is_attached = True
        else:
            self._log(f"AttachConsole 提示 (err={kernel32.GetLastError()})", "WARNING")

        self.h_in = kernel32.CreateFileW(
            "CONIN$", GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE,
            None, OPEN_EXISTING, 0, None
        )
        self.h_out = kernel32.CreateFileW(
            "CONOUT$", GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE,
            None, OPEN_EXISTING, 0, None
        )

        for _ in range(30):
            if self._is_cancelled:
                return
            if any("Steam>" in line for line in self._read_screen_rows()[-8:]):
                break
            time.sleep(0.5)

    def _get_cursor_row(self) -> int:
        if not self.h_out or self.h_out == -1:
            return 0
        csbi = CONSOLE_SCREEN_BUFFER_INFO()
        if kernel32.GetConsoleScreenBufferInfo(self.h_out, ctypes.byref(csbi)):
            return csbi.dwCursorPosition.Y
        return 0

    def _read_screen_rows(self, start_row: int = 0, end_row: Optional[int] = None) -> List[str]:
        if not self.h_out or self.h_out == -1:
            return []
        csbi = CONSOLE_SCREEN_BUFFER_INFO()
        if not kernel32.GetConsoleScreenBufferInfo(self.h_out, ctypes.byref(csbi)):
            return []

        width = csbi.dwSize.X
        total_rows = csbi.dwSize.Y
        if end_row is None:
            end_row = csbi.dwCursorPosition.Y

        start_row = max(0, min(start_row, total_rows - 1))
        end_row = max(start_row, min(end_row, total_rows - 1))
        num_rows = end_row - start_row + 1
        if num_rows <= 0:
            return []

        buf_size = width * num_rows
        buf = ctypes.create_unicode_buffer(buf_size)
        chars_read = wintypes.DWORD()
        coord = COORD(0, start_row)

        if not kernel32.ReadConsoleOutputCharacterW(
            self.h_out, buf, buf_size, coord, ctypes.byref(chars_read)
        ):
            return []

        lines = []
        for i in range(num_rows):
            line = buf.value[i * width:(i + 1) * width].rstrip()
            if line:
                lines.append(line)
        return lines

    def _send_keys(self, text: str):
        if not self.h_in or self.h_in == -1:
            return

        def make_key_event(char: str, is_down: bool):
            rec = INPUT_RECORD()
            rec.EventType = 0x0001
            rec.Event.KeyEvent.bKeyDown = is_down
            rec.Event.KeyEvent.wRepeatCount = 1
            rec.Event.KeyEvent.uChar = char
            rec.Event.KeyEvent.wVirtualKeyCode = 0x0D if char in ('\r', '\n') else 0
            rec.Event.KeyEvent.wVirtualScanCode = 0
            rec.Event.KeyEvent.dwControlKeyState = 0
            return rec

        records = []
        for c in text:
            ch = '\r' if c == '\n' else c
            records.append(make_key_event(ch, True))
            records.append(make_key_event(ch, False))

        arr_type = INPUT_RECORD * len(records)
        arr = arr_type(*records)
        written = wintypes.DWORD()
        kernel32.WriteConsoleInputW(self.h_in, arr, len(records), ctypes.byref(written))

    def _set_depot_filter(self, filter_val: str = "none", timeout: float = 6.0) -> bool:
        """
        设置 sDepotDownloadFileFilter 参数（绝不能带 @ 前缀）
        验证控制台回显: "sDepotDownloadFileFilter" = "none"
        """
        start_row = self._get_cursor_row()
        self._send_keys(f"sDepotDownloadFileFilter {filter_val}\n")
        filter_regex = re.compile(
            rf'["\']?sDepotDownloadFileFilter["\']?\s*=\s*["\']?{filter_val}["\']?',
            re.IGNORECASE
        )
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self._is_cancelled:
                return False
            lines = self._read_screen_rows(start_row)
            text = "\n".join(lines)
            if filter_regex.search(text):
                return True
            time.sleep(0.15)
        return False

    def _clean_old_tickets(self, appid: int):
        app_dir = self.work_dir / str(appid)
        if app_dir.exists():
            for p in list(app_dir.glob("*.txt")) + list(app_dir.glob("*.bin")):
                try:
                    p.unlink(missing_ok=True)
                except Exception:
                    pass

    def _parse_tickets(self, app_dir: Path) -> Tuple[str, str]:
        appticket = ""
        eticket = ""

        # 1. 优先读取标准 tickets.txt (支持 appticket(190bytes):<hex> 格式)
        t_f = app_dir / "tickets.txt"
        if t_f.exists():
            content = t_f.read_text(encoding="utf-8", errors="ignore")
            if not appticket:
                m = re.search(r"appticket[^\n:=]*[:=]\s*([a-zA-Z0-9+/=]{20,})", content, re.IGNORECASE)
                if m:
                    appticket = m.group(1).strip()
            if not eticket:
                m = re.search(r"eticket[^\n:=]*[:=]\s*([a-zA-Z0-9+/=]{20,})", content, re.IGNORECASE)
                if m:
                    eticket = m.group(1).strip()

        # 2. 从二进制文件 (.bin) 提取并转为 16 进制字符串
        app_bin = app_dir / "appticket.bin"
        if not appticket and app_bin.exists():
            raw = app_bin.read_bytes()
            if raw:
                appticket = raw.hex()

        e_bin = app_dir / "eticket.bin"
        if not eticket and e_bin.exists():
            raw = e_bin.read_bytes()
            if raw:
                eticket = raw.hex()

        # 3. 兜底读取单独的 txt 文件
        app_f = app_dir / "appticket.txt"
        if not appticket and app_f.exists():
            appticket = app_f.read_text(encoding="utf-8", errors="ignore").strip()

        e_f = app_dir / "eticket.txt"
        if not eticket and e_f.exists():
            eticket = e_f.read_text(encoding="utf-8", errors="ignore").strip()

        return appticket, eticket

    def run(self, appid: int, username: str, password: str, two_factor_code: str = "") -> Dict[str, Any]:
        """执行完整提取"""
        try:
            self._progress(10, "初始化环境")
            self._clean_old_tickets(appid)
            self._start_steamcmd()

            if self._is_cancelled:
                return {"success": False, "msg": "已取消"}

            # ----------------- 1. 登录阶段 -----------------
            self._progress(30, f"正在登录 Steam 账号 ({username})")
            self._log(f"提示：正在执行 Steam 登录 ({username})...")
            start_row = self._get_cursor_row()
            self._send_keys(f"login {username} {password}\n")

            login_ok = False
            t0 = time.time()
            guard_submitted = False
            guard_row = start_row
            timeout_sec = cfg.get("login_timeout_seconds", 90)

            guard_pattern = re.compile(
                r"(steam guard code|two-factor code|enter the current code|enter code from)",
                re.IGNORECASE
            )
            guard_error_pattern = re.compile(
                r"(invalid login auth code|two-factor code mismatch|incorrect code|invalid code)",
                re.IGNORECASE
            )
            login_success_pattern = re.compile(
                r"(logged in ok|waiting for user info\.\.\.ok|waiting for client config\.\.\.ok)",
                re.IGNORECASE
            )

            while time.time() - t0 < timeout_sec:
                if self._is_cancelled:
                    return {"success": False, "msg": "已取消"}

                lines = self._read_screen_rows(guard_row)
                block = "\n".join(lines)

                # 登录成功判定
                if login_success_pattern.search(block):
                    login_ok = True
                    self._log("🎉 Steam 账号登录成功！", "SUCCESS")
                    break

                # 账号或密码错误判定
                if "Login Failure" in block or "Invalid Password" in block:
                    return {"success": False, "msg": "Steam 登录失败：账号或密码错误"}
                if "Rate Limit Exceeded" in block:
                    return {"success": False, "msg": "Steam 登录失败：请求频次受限 (Rate Limit Exceeded)"}

                # 验证码提交后若检测到错误回显，立即弹出重试窗口并重新触发登录验证
                if guard_submitted and guard_error_pattern.search(block):
                    self._log("❌ Steam Guard 验证码错误（令牌错误或已过期），等待重新输入...", "WARNING")
                    self._progress(35, "验证码错误，等待重新输入")
                    guard_submitted = False

                    prompt_msg = "Steam Guard 验证码错误或已过期，请重新输入："
                    if self.on_need_guard_code:
                        input_code = self.on_need_guard_code(prompt_msg)
                        if input_code and str(input_code).strip():
                            final_code = str(input_code).strip()
                            self._log(f"已提交重试验证码: {final_code}，正在重新发起登录验证...")

                            # 重新触发登录流程
                            guard_row = self._get_cursor_row()
                            self._send_keys(f"login {username} {password}\n")

                            # 等待控制台输出 Steam Guard code 提示
                            t_wait = time.time()
                            while time.time() - t_wait < 12.0:
                                if self._is_cancelled:
                                    return {"success": False, "msg": "已取消"}
                                cur_lines = self._read_screen_rows(guard_row)
                                cur_txt = "\n".join(cur_lines)
                                if guard_pattern.search(cur_txt):
                                    break
                                time.sleep(0.3)

                            # 输入新的验证码
                            guard_row = self._get_cursor_row()
                            self._send_keys(f"{final_code}\n")
                            guard_submitted = True
                            t0 = time.time()
                            time.sleep(0.5)
                            continue
                        else:
                            return {"success": False, "msg": "用户取消了验证码输入"}
                    else:
                        return {"success": False, "msg": "Steam Guard 验证码错误，未配置重试交互"}

                # 出现验证码要求判定 (仅在尚未提交或已被判为错误时触发)
                if not guard_submitted and guard_pattern.search(block):
                    prompt_msg = "Steam 正在请求安全验证码（手机令牌或邮箱验证码）"
                    self._log(f"⚠️ {prompt_msg}，等待用户输入...", "WARNING")
                    self._progress(35, "等待输入验证码")

                    if self.on_need_guard_code:
                        input_code = self.on_need_guard_code(prompt_msg)
                        if input_code and str(input_code).strip():
                            final_code = str(input_code).strip()
                            self._log(f"已提交验证码: {final_code}，正在验证...")
                            
                            guard_row = self._get_cursor_row()
                            self._send_keys(f"{final_code}\n")
                            guard_submitted = True
                            t0 = time.time()
                            time.sleep(0.5)
                            continue
                        else:
                            return {"success": False, "msg": "用户取消了验证码输入"}
                    else:
                        return {"success": False, "msg": "检测到验证码要求，但未配置输入交互"}

                # 兜底：如果已提交过验证码，且控制台末尾出现新的 Steam> 提示符
                if guard_submitted and len(lines) >= 1:
                    last_three = "\n".join(lines[-3:])
                    if "Steam>" in last_three and "Steam Guard code:" not in last_three:
                        login_ok = True
                        self._log("🎉 检测到 Steam 控制台就绪，登录成功！", "SUCCESS")
                        break

                time.sleep(0.5)

            if not login_ok:
                return {"success": False, "msg": "Steam 登录超时，请检查网络或验证码"}

            # ----------------- 2. 触发更新阶段 (严格设置 none 参数并等待 app_update) -----------------
            self._progress(60, f"设置下载过滤并触发 AppID={appid} 更新")
            self._log("正在设置过滤参数: sDepotDownloadFileFilter none (禁止下载游戏内容)...")

            filter_ok = self._set_depot_filter("none", timeout=5.0)
            if not filter_ok:
                self._log("未捕获到 filter 回显确认，重试发送 sDepotDownloadFileFilter none...", "WARNING")
                self._send_keys("\n")
                time.sleep(0.3)
                filter_ok = self._set_depot_filter("none", timeout=5.0)

            if filter_ok:
                self._log("已确认生效: \"sDepotDownloadFileFilter\" = \"none\"", "SUCCESS")
            else:
                self._log("sDepotDownloadFileFilter 命令已发送，继续下一步", "INFO")

            # 执行 app_update
            self._log(f"执行 app_update {appid} 获取票据授权凭证...")
            time.sleep(0.5)
            upd_row = self._get_cursor_row()
            self._send_keys(f"app_update {appid}\n")
            time.sleep(1.0)  # 留足 1 秒让命令回显，避免读到旧屏幕内容

            t_upd = time.time()
            upd_success = False
            last_status_report = t_upd

            success_regex = re.compile(rf"Success!\s+App\s+['\"]?{appid}['\"]?.*", re.IGNORECASE)
            fallback_success_regex = re.compile(r"Success!\s+App.*", re.IGNORECASE)

            while time.time() - t_upd < 60:
                if self._is_cancelled:
                    return {"success": False, "msg": "已取消"}

                lines = self._read_screen_rows(upd_row)
                txt = "\n".join(lines)

                # 1. 严格检查无订阅错误
                if "No subscription" in txt:
                    self._log(f"❌ 错误：当前账号未拥有 AppID {appid} 授权 (No subscription)！", "ERROR")
                    return {"success": False, "msg": f"当前账号未拥有 AppID {appid} 授权 (No subscription)，请检查账号权限"}

                # 2. 检查权限不足错误
                if "Access Denied" in txt:
                    self._log(f"❌ app_update 权限受限 (Access Denied)", "ERROR")
                    return {"success": False, "msg": f"app_update 权限受限 (Access Denied)"}

                # 3. 严格匹配成功关键字 (绝不使用泛化 already up to date)
                succ_match = success_regex.search(txt) or fallback_success_regex.search(txt)
                if succ_match:
                    upd_success = True
                    self._log(f"app_update {appid} 执行完成: {succ_match.group().strip()}", "SUCCESS")
                    time.sleep(1.0)
                    break

                # 4. 定期在日志中同步控制台当前状态，防止用户误以为卡死
                if time.time() - last_status_report > 6.0:
                    latest = lines[-1].strip() if lines else "等待响应中"
                    self._log(f"正在等待 app_update {appid} 完成... 状态: {latest[:75]}")
                    last_status_report = time.time()

                time.sleep(0.5)

            if not upd_success:
                self._log(f"app_update {appid} 等待超时(60s)，继续尝试进行票据提取...", "WARNING")

            # ----------------- 3. 提取票据阶段 (带完整实时日志透传) -----------------
            self._progress(80, "调用 extract_tickets.exe 提取票据")
            app_dir = self.work_dir / str(appid)
            max_attempts = cfg.get("extract_max_attempts", 8)
            retry_interval = cfg.get("extract_retry_interval", 6.0)

            appticket, eticket = "", ""
            for attempt in range(1, max_attempts + 1):
                if self._is_cancelled:
                    return {"success": False, "msg": "已取消"}

                cmd_args = [str(self.extract_exe), str(appid)]
                self._log(f"正在执行提取命令: extract_tickets.exe {appid} ({attempt}/{max_attempts})...")

                try:
                    extract_flags = (
                        subprocess.CREATE_NEW_CONSOLE
                        if self.show_extract_console
                        else getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
                    )

                    res = subprocess.run(
                        cmd_args,
                        cwd=str(self.work_dir),
                        input="\n",
                        capture_output=True,
                        text=True,
                        timeout=30,
                        creationflags=extract_flags
                    )

                    out_text = (res.stdout or "").strip()
                    err_text = (res.stderr or "").strip()

                    # 将 extract_tickets.exe 的真实输出实时打印在 GUI 日志中
                    if out_text:
                        for line in out_text.splitlines():
                            ls = line.strip()
                            if ls:
                                self._log(f"[提取] {ls}")
                    if err_text:
                        self._log(f"[提取警告] {err_text}", "WARNING")

                except Exception as ex:
                    self._log(f"调用 extract_tickets 提示: {ex}", "WARNING")

                appticket, eticket = self._parse_tickets(app_dir)
                if appticket and eticket:
                    break
                if attempt < max_attempts:
                    time.sleep(retry_interval)

            if not appticket or not eticket:
                missing = []
                if not appticket: missing.append("appticket")
                if not eticket: missing.append("eticket")
                return {"success": False, "msg": f"票据提取不完整 (缺少: {', '.join(missing)})"}

            self._progress(100, "提取完成")
            self._log("🎉 成功提取到 appticket 与 eticket！", "SUCCESS")

            return {
                "success": True,
                "data": {
                    "appid": str(appid),
                    "account": username,
                    "appticket": appticket,
                    "eticket": eticket,
                    "ticket_file": str(app_dir / "tickets.txt"),
                    "ticket_dir": str(app_dir)
                }
            }

        except Exception as e:
            self._log(f"运行异常: {e}", "ERROR")
            return {"success": False, "msg": str(e)}
        finally:
            self.terminate()

    def terminate(self):
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

        if self.h_in and self.h_in != -1:
            try:
                kernel32.CloseHandle(self.h_in)
            except Exception:
                pass
            self.h_in = None

        if self.h_out and self.h_out != -1:
            try:
                kernel32.CloseHandle(self.h_out)
            except Exception:
                pass
            self.h_out = None

        if self.is_attached:
            try:
                kernel32.FreeConsole()
            except Exception:
                pass
            self.is_attached = False
