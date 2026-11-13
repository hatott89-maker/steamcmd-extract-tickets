# -*- coding: utf-8 -*-
"""
SteamCMD Ticket Extractor 现代极简纯白设计系统 (Modern Clean Light Design System)
严格遵循 Qt 盒子模型，固定标准控件高度与内边距，根除任何挤压与走样变形。
"""
import os
import sys

if hasattr(sys, "_MEIPASS"):
    ASSETS_DIR = os.path.join(sys._MEIPASS, "gui", "assets")
else:
    ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

CHECK_ICON_PATH = os.path.join(ASSETS_DIR, "check_white.png").replace("\\", "/")


def ensure_assets():
    """若资源图标不存在则自动绘制兜底，确保免依赖运行"""
    if not os.path.exists(ASSETS_DIR):
        try:
            os.makedirs(ASSETS_DIR, exist_ok=True)
        except Exception:
            pass
    icon_file = os.path.join(ASSETS_DIR, "check_white.png")
    if not os.path.exists(icon_file):
        try:
            from PyQt6.QtGui import QImage, QPainter, QColor, QPen
            from PyQt6.QtCore import Qt, QPoint
            img = QImage(32, 32, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            painter = QPainter(img)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(QColor("#ffffff"), 3.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(QPoint(7, 16), QPoint(13, 22))
            painter.drawLine(QPoint(13, 22), QPoint(25, 9))
            painter.end()
            img.save(icon_file, "PNG")
        except Exception:
            pass


ensure_assets()


def get_stylesheet() -> str:
    return f"""
/* 全局基础设置 */
QWidget {{
    background-color: #f8fafc;
    color: #0f172a;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    font-size: 13px;
    outline: none;
}}

/* 主内容容器与外层滚动区 */
#centralWidget, #mainScrollArea {{
    background-color: #f8fafc;
    border: none;
}}

QScrollArea#mainScrollArea > QWidget > QWidget {{
    background-color: #f8fafc;
}}

/* 纯白轻量卡片容器 */
#cardWidget {{
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
}}

/* 卡片标题 */
#cardTitle {{
    font-size: 14px;
    font-weight: 700;
    color: #0f172a;
    background: transparent;
}}

/* 表单字段标签 */
QLabel#fieldLabel {{
    font-size: 12px;
    font-weight: 600;
    color: #475569;
    background: transparent;
}}

/* 单行输入框标准规范 (高度严控 36px) */
QLineEdit {{
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    color: #0f172a;
    padding: 0 10px;
    min-height: 34px;
    max-height: 34px;
    font-size: 13px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}}

QLineEdit:hover {{
    border-color: #94a3b8;
}}

QLineEdit:focus {{
    border: 1.5px solid #2563eb;
    background-color: #ffffff;
}}

QLineEdit:disabled, QLineEdit:read-only {{
    background-color: #f8fafc;
    color: #475569;
    border-color: #e2e8f0;
}}

/* 主操作按钮 (开始提取 - 现代蓝 40px) */
QPushButton#primaryBtn {{
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #1d4ed8;
    font-weight: 600;
    font-size: 14px;
    border-radius: 6px;
    min-height: 38px;
    max-height: 38px;
    padding: 0 20px;
}}

QPushButton#primaryBtn:hover {{
    background-color: #1d4ed8;
    border-color: #1e40af;
}}

QPushButton#primaryBtn:pressed {{
    background-color: #1e40af;
}}

QPushButton#primaryBtn:disabled {{
    background-color: #93c5fd;
    border-color: #93c5fd;
    color: #ffffff;
}}

/* 终止/取消按钮 (40px) */
QPushButton#dangerBtn {{
    background-color: #ffffff;
    color: #dc2626;
    border: 1px solid #fca5a5;
    font-weight: 600;
    font-size: 14px;
    border-radius: 6px;
    min-height: 38px;
    max-height: 38px;
    padding: 0 18px;
}}

QPushButton#dangerBtn:hover {{
    background-color: #fef2f2;
    border-color: #ef4444;
}}

QPushButton#dangerBtn:pressed {{
    background-color: #fee2e2;
}}

QPushButton#dangerBtn:disabled {{
    background-color: #f8fafc;
    color: #94a3b8;
    border-color: #e2e8f0;
}}

/* 常用小按钮 (浏览、清空、导出、复制、显示密码) */
QPushButton.small-btn {{
    background-color: #ffffff;
    color: #334155;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 0 10px;
    min-height: 32px;
    max-height: 34px;
    font-size: 12px;
    font-weight: 500;
}}

QPushButton.small-btn:hover {{
    background-color: #f1f5f9;
    border-color: #94a3b8;
    color: #0f172a;
}}

QPushButton.small-btn:pressed {{
    background-color: #e2e8f0;
}}

QPushButton.small-btn:disabled {{
    background-color: #f8fafc;
    color: #94a3b8;
    border-color: #e2e8f0;
}}

/* 快捷 AppID 药丸标签 */
QPushButton.tag-btn {{
    background-color: #f1f5f9;
    color: #475569;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 0 10px;
    min-height: 24px;
    max-height: 24px;
    font-size: 11px;
    font-weight: 500;
}}

QPushButton.tag-btn:hover {{
    background-color: #e2e8f0;
    color: #0f172a;
    border-color: #cbd5e1;
}}

/* 复选框 - 高清指示器与独立对勾图标，彻底杜绝走样与方括号 */
QCheckBox {{
    color: #334155;
    font-size: 13px;
    spacing: 8px;
    background: transparent;
}}

QCheckBox::indicator {{
    width: 17px;
    height: 17px;
    border: 1.5px solid #cbd5e1;
    border-radius: 4px;
    background-color: #ffffff;
}}

QCheckBox::indicator:hover {{
    border-color: #2563eb;
}}

QCheckBox::indicator:checked {{
    background-color: #2563eb;
    border-color: #2563eb;
    image: url({CHECK_ICON_PATH});
}}

/* 进度条 */
QProgressBar {{
    background-color: #e2e8f0;
    border: none;
    border-radius: 3px;
    text-align: center;
    color: transparent;
    min-height: 6px;
    max-height: 6px;
}}

QProgressBar::chunk {{
    background-color: #2563eb;
    border-radius: 3px;
}}

/* 日志文本框 */
QPlainTextEdit {{
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    color: #1e293b;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    line-height: 1.4;
    padding: 8px 10px;
    selection-background-color: #dbeafe;
    selection-color: #1e3a8a;
}}

/* 纤细现代滚动条 */
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 6px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: #cbd5e1;
    min-height: 24px;
    border-radius: 3px;
}}

QScrollBar::handle:vertical:hover {{
    background: #94a3b8;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    border: none;
    background: transparent;
    height: 6px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background: #cbd5e1;
    min-width: 24px;
    border-radius: 3px;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
"""

STUDIO_LIGHT_QSS = get_stylesheet()
MODERN_PRO_QSS = STUDIO_LIGHT_QSS
