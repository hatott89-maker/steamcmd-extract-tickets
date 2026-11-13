# -*- coding: utf-8 -*-
"""
SteamCMD Ticket Extractor 现代桌面主界面 (双栏响应式自适应版)
支持登录提示、按需动态弹窗输入验证码、验证成功自动关闭与错误复弹。
"""
import os
import threading
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QLineEdit, QPushButton, QProgressBar,
    QMessageBox, QApplication, QCheckBox, QFileDialog,
    QSizePolicy, QScrollArea, QFrame, QDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from gui.styles import STUDIO_LIGHT_QSS
from gui.components import CardWidget, StatusBadge, LogViewer, CodeSnippetBox
from core.steamcmd_direct import SteamCMDDirectExtractor
from config import cfg

VERSION = "v1.0.0"


class GuardCodeDialog(QDialog):
    """Steam Guard 验证码交互输入对话框"""

    def __init__(self, prompt: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Steam Guard 安全验证")
        self.setFixedSize(390, 220)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setStyleSheet(STUDIO_LIGHT_QSS)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        lbl_title = QLabel("请输入 Steam 安全验证码")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #0f172a;")

        lbl_desc = QLabel(prompt or "检测到 Steam 正在请求安全验证码（手机令牌或邮箱验证码），请输入后继续：")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("font-size: 12px; color: #64748b; line-height: 1.4;")

        self.input_code = QLineEdit()
        self.input_code.setFixedHeight(40)
        self.input_code.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.input_code.setPlaceholderText("例如: X4F2K 或 12345")
        self.input_code.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 16px; font-weight: 700; letter-spacing: 2px;"
        )
        self.input_code.textChanged.connect(self._auto_upper)
        self.input_code.returnPressed.connect(self.on_confirm)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_confirm = QPushButton("确认并继续")
        self.btn_confirm.setObjectName("primaryBtn")
        self.btn_confirm.setFixedHeight(38)
        self.btn_confirm.clicked.connect(self.on_confirm)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setObjectName("dangerBtn")
        self.btn_cancel.setFixedHeight(38)
        self.btn_cancel.setFixedWidth(80)
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_confirm, stretch=1)
        btn_layout.addWidget(self.btn_cancel)

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_desc)
        layout.addWidget(self.input_code)
        layout.addLayout(btn_layout)

        self.input_code.setFocus()
        self.code_value = ""

    def _auto_upper(self, text: str):
        pos = self.input_code.cursorPosition()
        self.input_code.blockSignals(True)
        self.input_code.setText(text.upper())
        self.input_code.setCursorPosition(pos)
        self.input_code.blockSignals(False)

    def on_confirm(self):
        val = self.input_code.text().strip()
        if not val:
            self.input_code.setFocus()
            return
        self.code_value = val
        self.accept()


class DirectExtractThread(QThread):
    """后台单机直连提取工作线程，支持线程安全的验证码交互等待"""
    sig_log = pyqtSignal(str, str)
    sig_progress = pyqtSignal(int, str)
    sig_finished = pyqtSignal(bool, dict)
    sig_need_guard_code = pyqtSignal(str)

    def __init__(
        self,
        steamcmd_dir: Path,
        show_steamcmd_console: bool,
        show_extract_console: bool,
        appid: int,
        username: str,
        password: str
    ):
        super().__init__()
        self.appid = appid
        self.username = username
        self.password = password

        self._guard_event = threading.Event()
        self._received_guard_code: Optional[str] = None

        self.extractor = SteamCMDDirectExtractor(
            steamcmd_dir=steamcmd_dir,
            show_steamcmd_console=show_steamcmd_console,
            show_extract_console=show_extract_console,
            on_log=self.sig_log.emit,
            on_progress=self.sig_progress.emit,
            on_need_guard_code=self._wait_for_guard_code
        )

    def _wait_for_guard_code(self, prompt: str) -> Optional[str]:
        """供提取器调用的同步回调：挂起当前工作线程，通知 UI 弹窗等待用户输入"""
        self._received_guard_code = None
        self._guard_event.clear()
        self.sig_need_guard_code.emit(prompt)
        # 等待用户输入验证码 (最长 180 秒)
        self._guard_event.wait(timeout=180.0)
        return self._received_guard_code

    def provide_guard_code(self, code: Optional[str]):
        """主线程调用此槽，唤醒工作线程继续执行"""
        self._received_guard_code = code
        self._guard_event.set()

    def run(self):
        try:
            res = self.extractor.run(
                appid=self.appid,
                username=self.username,
                password=self.password
            )
            self.sig_finished.emit(res.get("success", False), res)
        except Exception as e:
            self.sig_log.emit("ERROR", f"执行异常: {e}")
            self.sig_finished.emit(False, {"success": False, "msg": str(e)})

    def cancel(self):
        self._received_guard_code = None
        self._guard_event.set()
        self.extractor.cancel()


class MainWindow(QMainWindow):
    """现代纯白桌面主窗口，采用高空间利用率的左右双栏布局架构"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"SteamCMD 票据提取工具 {VERSION}")
        self.resize(1000, 640)
        self.setMinimumSize(860, 520)
        self.setStyleSheet(STUDIO_LIGHT_QSS)

        self.worker_thread: DirectExtractThread = None
        self.last_ticket_dir = ""
        self.init_ui()

    def init_ui(self):
        # 外层防裁切滚动容器
        scroll_area = QScrollArea()
        scroll_area.setObjectName("mainScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.setCentralWidget(scroll_area)

        content_widget = QWidget()
        content_widget.setObjectName("centralWidget")
        scroll_area.setWidget(content_widget)

        # 根布局：左右双主栏结构
        root_h = QHBoxLayout(content_widget)
        root_h.setContentsMargins(18, 16, 18, 16)
        root_h.setSpacing(16)

        # ========================================================
        # 1. 左栏：配置与凭据输入卡片 (极简一站式，无需预填令牌)
        # ========================================================
        left_card = CardWidget("配置与账号凭据")
        left_card.setFixedWidth(410)
        left_card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.MinimumExpanding)

        # 1.1 SteamCMD 目录
        lbl_dir = QLabel("SteamCMD 目录")
        lbl_dir.setObjectName("fieldLabel")
        dir_row = QHBoxLayout()
        dir_row.setSpacing(6)
        dir_row.setContentsMargins(0, 0, 0, 0)

        self.input_dir = QLineEdit(str(cfg.steamcmd_dir))
        self.input_dir.setFixedHeight(34)
        self.input_dir.setPlaceholderText("选择包含 steamcmd.exe 的目录")

        self.btn_browse = QPushButton("浏览")
        self.btn_browse.setProperty("class", "small-btn")
        self.btn_browse.setFixedWidth(60)
        self.btn_browse.setFixedHeight(34)
        self.btn_browse.clicked.connect(self.browse_dir)

        dir_row.addWidget(self.input_dir, stretch=1)
        dir_row.addWidget(self.btn_browse)

        left_card.add_widget(lbl_dir)
        left_card.add_layout(dir_row)

        # 1.2 控制台显示勾选项
        chk_row = QHBoxLayout()
        chk_row.setSpacing(14)
        chk_row.setContentsMargins(0, 2, 0, 4)

        self.chk_show_steam = QCheckBox("显示 SteamCMD 窗口")
        self.chk_show_steam.setFixedHeight(24)
        self.chk_show_steam.setChecked(cfg.show_steamcmd_console)
        self.chk_show_steam.stateChanged.connect(self.save_env_config)

        self.chk_show_extract = QCheckBox("显示提取窗口")
        self.chk_show_extract.setFixedHeight(24)
        self.chk_show_extract.setChecked(cfg.show_extract_console)
        self.chk_show_extract.stateChanged.connect(self.save_env_config)

        chk_row.addWidget(self.chk_show_steam)
        chk_row.addWidget(self.chk_show_extract)
        chk_row.addStretch()
        left_card.add_layout(chk_row)

        # 1.3 AppID 与常用游戏快捷填充
        lbl_appid = QLabel("AppID (游戏编号)")
        lbl_appid.setObjectName("fieldLabel")
        self.input_appid = QLineEdit(str(cfg.get("default_appid", 1091500)))
        self.input_appid.setFixedHeight(34)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)
        preset_row.setContentsMargins(0, 0, 0, 2)
        for name, aid in [("赛博朋克2077", 1091500), ("黑神话:悟空", 2358720), ("生化危机4", 2050650)]:
            btn_p = QPushButton(name)
            btn_p.setProperty("class", "tag-btn")
            btn_p.setFixedHeight(24)
            btn_p.clicked.connect(lambda _, a=aid: self.input_appid.setText(str(a)))
            preset_row.addWidget(btn_p)
        preset_row.addStretch()

        left_card.add_widget(lbl_appid)
        left_card.add_widget(self.input_appid)
        left_card.add_layout(preset_row)

        # 1.4 Steam 账号
        lbl_user = QLabel("Steam 账号")
        lbl_user.setObjectName("fieldLabel")
        self.input_user = QLineEdit(cfg.get("last_username", ""))
        self.input_user.setFixedHeight(34)
        self.input_user.setPlaceholderText("请输入 Steam 登录账号")
        left_card.add_widget(lbl_user)
        left_card.add_widget(self.input_user)

        # 1.5 Steam 密码
        lbl_pwd = QLabel("Steam 密码")
        lbl_pwd.setObjectName("fieldLabel")
        self.input_pwd = QLineEdit(cfg.get("last_password", ""))
        self.input_pwd.setFixedHeight(34)
        self.input_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_pwd.setPlaceholderText("请输入 Steam 登录密码")

        pwd_row = QHBoxLayout()
        pwd_row.setSpacing(6)
        pwd_row.setContentsMargins(0, 0, 0, 0)
        self.btn_toggle_pwd = QPushButton("显示")
        self.btn_toggle_pwd.setProperty("class", "small-btn")
        self.btn_toggle_pwd.setFixedWidth(55)
        self.btn_toggle_pwd.setFixedHeight(34)
        self.btn_toggle_pwd.clicked.connect(self.toggle_password_visibility)
        pwd_row.addWidget(self.input_pwd, stretch=1)
        pwd_row.addWidget(self.btn_toggle_pwd)

        left_card.add_widget(lbl_pwd)
        left_card.add_layout(pwd_row)

        # 1.6 记住账号密码
        self.chk_remember = QCheckBox("记住账号密码")
        self.chk_remember.setFixedHeight(24)
        self.chk_remember.setChecked(cfg.get("remember_credentials", True))
        left_card.add_widget(self.chk_remember)

        # 1.7 操作按钮 (固定 40px，绝对包裹于卡片内部底端)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.setContentsMargins(0, 10, 0, 2)

        self.btn_start = QPushButton("开始提取")
        self.btn_start.setObjectName("primaryBtn")
        self.btn_start.setFixedHeight(40)
        self.btn_start.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_start.clicked.connect(self.start_extraction)

        self.btn_stop = QPushButton("取消")
        self.btn_stop.setObjectName("dangerBtn")
        self.btn_stop.setFixedHeight(40)
        self.btn_stop.setFixedWidth(85)
        self.btn_stop.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.cancel_extraction)

        btn_row.addWidget(self.btn_start, stretch=1)
        btn_row.addWidget(self.btn_stop)
        left_card.add_layout(btn_row)

        left_card.main_layout.addStretch()
        root_h.addWidget(left_card, stretch=0)

        # ========================================================
        # 2. 右栏：提取结果与实时控制台日志
        # ========================================================
        right_v = QVBoxLayout()
        right_v.setSpacing(12)
        right_v.setContentsMargins(0, 0, 0, 0)

        # 2.1 提取结果卡片
        self.badge_status = StatusBadge("就绪待命", "offline")
        res_card = CardWidget("提取结果", extra_header_widget=self.badge_status)

        status_box = QVBoxLayout()
        status_box.setSpacing(6)
        status_box.setContentsMargins(0, 0, 0, 4)

        self.lbl_step_desc = QLabel("等待启动任务...")
        self.lbl_step_desc.setStyleSheet("color: #475569; font-weight: 500; font-size: 13px;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setValue(0)

        status_box.addWidget(self.lbl_step_desc)
        status_box.addWidget(self.progress_bar)
        res_card.add_layout(status_box)

        # 票据展示框
        self.snippet_app = CodeSnippetBox("appticket")
        self.snippet_e = CodeSnippetBox("eticket")
        res_card.add_widget(self.snippet_app)
        res_card.add_widget(self.snippet_e)

        # 产物路径展示
        path_box = QWidget()
        path_box.setFixedHeight(34)
        path_layout = QHBoxLayout(path_box)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.setSpacing(8)

        lbl_path_title = QLabel("产物路径")
        lbl_path_title.setObjectName("fieldLabel")
        lbl_path_title.setFixedWidth(70)

        self.input_filepath = QLineEdit()
        self.input_filepath.setReadOnly(True)
        self.input_filepath.setFixedHeight(34)
        self.input_filepath.setPlaceholderText("尚未生成")

        self.btn_open_folder = QPushButton("打开所在目录")
        self.btn_open_folder.setProperty("class", "small-btn")
        self.btn_open_folder.setFixedWidth(95)
        self.btn_open_folder.setFixedHeight(34)
        self.btn_open_folder.clicked.connect(self.open_result_dir)

        path_layout.addWidget(lbl_path_title)
        path_layout.addWidget(self.input_filepath, stretch=1)
        path_layout.addWidget(self.btn_open_folder)
        res_card.add_widget(path_box)

        right_v.addWidget(res_card, stretch=0)

        # 2.2 运行日志卡片
        self.log_viewer = LogViewer()
        self.log_viewer.setMinimumHeight(200)
        self.log_viewer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.log_viewer.append_log("INFO", "系统已就绪，请输入凭据后点击开始提取")
        right_v.addWidget(self.log_viewer, stretch=1)

        root_h.addLayout(right_v, stretch=1)

    def browse_dir(self):
        p = QFileDialog.getExistingDirectory(self, "选择 SteamCMD 目录", self.input_dir.text())
        if p:
            self.input_dir.setText(p)
            self.save_env_config()

    def save_env_config(self):
        cfg.steamcmd_dir = self.input_dir.text().strip()
        cfg.show_steamcmd_console = self.chk_show_steam.isChecked()
        cfg.show_extract_console = self.chk_show_extract.isChecked()
        cfg.save()

    def toggle_password_visibility(self):
        if self.input_pwd.echoMode() == QLineEdit.EchoMode.Password:
            self.input_pwd.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_pwd.setText("隐藏")
        else:
            self.input_pwd.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_pwd.setText("显示")

    def start_extraction(self):
        work_dir = Path(self.input_dir.text().strip())
        if not (work_dir / "steamcmd.exe").exists():
            QMessageBox.warning(self, "提示", f"指定目录下未找到 steamcmd.exe:\n{work_dir}")
            return

        try:
            appid = int(self.input_appid.text().strip())
        except ValueError:
            QMessageBox.warning(self, "提示", "请输入正确的数字 AppID")
            return

        user = self.input_user.text().strip()
        pwd = self.input_pwd.text().strip()

        if not user or not pwd:
            QMessageBox.warning(self, "提示", "Steam 账号与密码不能为空")
            return

        self.save_env_config()
        if self.chk_remember.isChecked():
            cfg.set("remember_credentials", True, auto_save=False)
            cfg.set("last_username", user, auto_save=False)
            cfg.set("last_password", pwd, auto_save=True)
        else:
            cfg.set("remember_credentials", False, auto_save=False)
            cfg.set("last_username", "", auto_save=False)
            cfg.set("last_password", "", auto_save=True)

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress_bar.setValue(15)
        self.badge_status.set_status("running", "提取中")
        self.lbl_step_desc.setText(f"提示：正在执行 Steam 登录 ({user})...")
        self.snippet_app.set_value("")
        self.snippet_e.set_value("")
        self.input_filepath.setText("")
        self.log_viewer.clear_logs()

        self.worker_thread = DirectExtractThread(
            steamcmd_dir=work_dir,
            show_steamcmd_console=self.chk_show_steam.isChecked(),
            show_extract_console=self.chk_show_extract.isChecked(),
            appid=appid,
            username=user,
            password=pwd
        )
        self.worker_thread.sig_log.connect(self.log_viewer.append_log)
        self.worker_thread.sig_progress.connect(self.on_worker_progress)
        self.worker_thread.sig_finished.connect(self.on_worker_finished)
        self.worker_thread.sig_need_guard_code.connect(self.on_need_guard_code)
        self.worker_thread.start()

    def on_need_guard_code(self, prompt: str):
        """当 SteamCMD 要求安全验证码时，弹出验证码输入框；输入正确并提交后立即关闭弹窗"""
        self.badge_status.set_status("warning", "等待验证码")
        self.lbl_step_desc.setText(prompt or "等待输入 Steam Guard 验证码...")

        dlg = GuardCodeDialog(prompt, self)
        dlg.raise_()
        dlg.activateWindow()
        if dlg.exec() == QDialog.DialogCode.Accepted:
            code = dlg.code_value
            self.lbl_step_desc.setText("已提交验证码，正在验证登录...")
            self.badge_status.set_status("running", "正在验证")
            self.worker_thread.provide_guard_code(code)
        else:
            self.lbl_step_desc.setText("用户取消了验证码输入")
            self.worker_thread.provide_guard_code(None)

    def cancel_extraction(self):
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.cancel()
            self.lbl_step_desc.setText("正在取消任务...")
            self.log_viewer.append_log("WARNING", "用户触发手动终止操作")

    def on_worker_progress(self, pct: int, desc: str):
        self.progress_bar.setValue(pct)
        self.lbl_step_desc.setText(desc)

    def on_worker_finished(self, success: bool, res_data: dict):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

        if success:
            self.badge_status.set_status("success", "提取成功")
            self.progress_bar.setValue(100)
            self.lbl_step_desc.setText("已成功提取双票据！")

            info = res_data.get("data", {})
            self.snippet_app.set_value(info.get("appticket", ""))
            self.snippet_e.set_value(info.get("eticket", ""))
            self.last_ticket_dir = info.get("ticket_dir", "")
            self.input_filepath.setText(info.get("ticket_file", self.last_ticket_dir))
            QMessageBox.information(self, "成功", "Denuvo 双票据提取成功！")
        else:
            self.badge_status.set_status("danger", "提取失败")
            msg = res_data.get("msg", "未知错误")
            self.lbl_step_desc.setText(f"失败: {msg}")
            QMessageBox.critical(self, "失败", f"提取未能完成:\n{msg}")

    def open_result_dir(self):
        if self.last_ticket_dir and os.path.exists(self.last_ticket_dir):
            os.startfile(self.last_ticket_dir)
        else:
            QMessageBox.warning(self, "提示", "尚未生成产物目录。")


def run_app():
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
