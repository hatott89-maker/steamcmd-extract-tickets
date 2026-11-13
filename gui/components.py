# -*- coding: utf-8 -*-
"""
PyQt6 现代极简纯白桌面组件库 (Clean Modern Light Components)
"""
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPlainTextEdit, QPushButton, QFrame, QFileDialog, QMessageBox,
    QApplication, QLineEdit, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QTextCursor, QColor, QTextCharFormat, QFont


class CardWidget(QFrame):
    """纯白轻量卡片容器，带标题与自适应内容约束"""

    def __init__(self, title: str = "", extra_header_widget: QWidget = None, parent=None):
        super().__init__(parent)
        self.setObjectName("cardWidget")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)
        self.main_layout.setContentsMargins(16, 14, 16, 14)
        self.main_layout.setSpacing(8)

        if title or extra_header_widget:
            header_layout = QHBoxLayout()
            header_layout.setContentsMargins(0, 0, 0, 4)

            if title:
                self.title_lbl = QLabel(title)
                self.title_lbl.setObjectName("cardTitle")
                header_layout.addWidget(self.title_lbl)

            header_layout.addStretch()

            if extra_header_widget:
                header_layout.addWidget(extra_header_widget)

            self.main_layout.addLayout(header_layout)

    def add_widget(self, widget: QWidget):
        self.main_layout.addWidget(widget)

    def add_layout(self, layout):
        self.main_layout.addLayout(layout)


class StatusBadge(QWidget):
    """胶囊状态指示徽章 (指示灯 + 状态文字)"""

    def __init__(self, text: str = "就绪", status: str = "offline", parent=None):
        super().__init__(parent)
        self.setFixedHeight(26)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(6)

        self.dot = QLabel()
        self.dot.setFixedSize(8, 8)

        self.lbl_text = QLabel(text)
        self.lbl_text.setStyleSheet("font-size: 12px; font-weight: 600; background: transparent;")

        layout.addWidget(self.dot)
        layout.addWidget(self.lbl_text)

        self.set_status(status, text)

    def set_status(self, status: str, text: str = ""):
        if text:
            self.lbl_text.setText(text)

        configs = {
            "success": ("#ecfdf5", "#059669", "#10b981", "#a7f3d0"),  # bg, text, dot, border
            "running": ("#eff6ff", "#2563eb", "#3b82f6", "#bfdbfe"),
            "warning": ("#fffbeb", "#d97706", "#f59e0b", "#fde68a"),
            "danger":  ("#fef2f2", "#dc2626", "#ef4444", "#fecaca"),
            "offline": ("#f1f5f9", "#64748b", "#94a3b8", "#e2e8f0"),
        }
        bg, fg, dot_c, border_c = configs.get(status, configs["offline"])

        self.setStyleSheet(f"""
            StatusBadge {{
                background-color: {bg};
                border: 1px solid {border_c};
                border-radius: 13px;
            }}
        """)
        self.lbl_text.setStyleSheet(f"color: {fg}; font-size: 12px; font-weight: 600; background: transparent;")
        self.dot.setStyleSheet(f"background-color: {dot_c}; border-radius: 4px;")


class CodeSnippetBox(QWidget):
    """现代化单行票据展示条 (只读文本框 + 一键复制按钮，高度锁死 36px)"""

    def __init__(self, label_text: str, default_val: str = "", parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        lbl = QLabel(label_text)
        lbl.setObjectName("fieldLabel")
        lbl.setFixedWidth(70)

        self.line_edit = QLineEdit()
        self.line_edit.setReadOnly(True)
        self.line_edit.setFixedHeight(36)
        self.line_edit.setPlaceholderText("尚未生成")
        self.line_edit.setStyleSheet("font-family: Consolas, monospace; font-size: 12px; color: #2563eb; font-weight: 500;")

        self.btn_copy = QPushButton("复制")
        self.btn_copy.setProperty("class", "small-btn")
        self.btn_copy.setFixedWidth(60)
        self.btn_copy.setFixedHeight(36)
        self.btn_copy.clicked.connect(self.on_copy)

        layout.addWidget(lbl)
        layout.addWidget(self.line_edit, stretch=1)
        layout.addWidget(self.btn_copy)

        self.raw_value = ""
        if default_val:
            self.set_value(default_val)

    def set_value(self, val: str):
        self.raw_value = str(val or "").strip()
        self.line_edit.setText(self.raw_value)
        if not self.raw_value:
            self.line_edit.setStyleSheet("font-family: Consolas, monospace; font-size: 12px; color: #94a3b8;")
        else:
            self.line_edit.setStyleSheet("font-family: Consolas, monospace; font-size: 12px; color: #2563eb; font-weight: 600;")

    def on_copy(self):
        val = self.raw_value or self.line_edit.text().strip()
        if not val:
            return
        QApplication.clipboard().setText(val)
        self.btn_copy.setText("已复制")
        self.btn_copy.setStyleSheet("color: #16a34a; font-weight: 600;")
        QTimer.singleShot(1500, self._restore_copy_btn)

    def _restore_copy_btn(self):
        self.btn_copy.setText("复制")
        self.btn_copy.setStyleSheet("")


class LogViewer(QFrame):
    """现代嵌入式控制台日志查看器"""

    def __init__(self, max_lines: int = 2000, parent=None):
        super().__init__(parent)
        self.setObjectName("cardWidget")
        self.max_lines = max_lines

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(8)

        # 头部工具栏
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel("运行日志")
        lbl.setObjectName("cardTitle")
        top_bar.addWidget(lbl)
        top_bar.addStretch()

        self.btn_clear = QPushButton("清空")
        self.btn_clear.setProperty("class", "small-btn")
        self.btn_clear.setFixedWidth(55)
        self.btn_clear.setFixedHeight(28)
        self.btn_clear.clicked.connect(self.clear_logs)

        self.btn_export = QPushButton("导出")
        self.btn_export.setProperty("class", "small-btn")
        self.btn_export.setFixedWidth(55)
        self.btn_export.setFixedHeight(28)
        self.btn_export.clicked.connect(self.export_logs)

        top_bar.addWidget(self.btn_clear)
        top_bar.addWidget(self.btn_export)
        layout.addLayout(top_bar)

        # 日志文本框
        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setMaximumBlockCount(self.max_lines)
        self.text_edit.setMinimumHeight(120)
        layout.addWidget(self.text_edit, stretch=1)

    def append_log(self, level: str, message: str):
        timestamp = time.strftime("%H:%M:%S")
        lvl = level.upper()

        colors = {
            "INFO": "#2563eb",
            "SUCCESS": "#16a34a",
            "WARNING": "#d97706",
            "ERROR": "#dc2626",
            "DEBUG": "#64748b",
        }
        color_hex = colors.get(lvl, "#0f172a")

        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        fmt_time = QTextCharFormat()
        fmt_time.setForeground(QColor("#94a3b8"))
        cursor.insertText(f"[{timestamp}] ", fmt_time)

        fmt_lvl = QTextCharFormat()
        fmt_lvl.setForeground(QColor(color_hex))
        fmt_lvl.setFontWeight(QFont.Weight.Bold)
        cursor.insertText(f"[{lvl:^7}] ", fmt_lvl)

        fmt_msg = QTextCharFormat()
        fmt_msg.setForeground(QColor("#1e293b"))
        cursor.insertText(f"{message}\n", fmt_msg)

        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible()

    def clear_logs(self):
        self.text_edit.clear()

    def export_logs(self):
        content = self.text_edit.toPlainText()
        if not content:
            QMessageBox.information(self, "提示", "日志为空。")
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出日志", "logs.txt", "Text (*.txt);;All (*)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                QMessageBox.information(self, "成功", "导出成功。")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {e}")
