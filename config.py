# -*- coding: utf-8 -*-
"""
SteamCMD Ticket Extractor 全局配置中心 (极简纯净版)
"""
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

CONFIG_FILE = BASE_DIR / "config.json"


class AppConfig:
    """应用程序统一配置"""

    DEFAULT_CONFIG = {
        "steamcmd_dir": r"D:\steamcmd\steamcmd",
        "show_steamcmd_console": False,
        "show_extract_console": False,
        "default_appid": 1091500,
        "login_timeout_seconds": 60,
        "extract_max_attempts": 8,
        "extract_retry_interval": 8.0,
        "remember_credentials": True,
        "last_username": "",
        "last_password": "",
    }

    _instance: Optional["AppConfig"] = None

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or CONFIG_FILE
        self._data: Dict[str, Any] = self.DEFAULT_CONFIG.copy()
        self.load()

    @classmethod
    def get_instance(cls) -> "AppConfig":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load(self):
        if not self.config_path.exists():
            self.save()
            return
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                self._data.update(loaded)
        except Exception as e:
            logging.getLogger("Config").warning("加载配置失败: %s", e)

    def save(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.getLogger("Config").error("保存配置失败: %s", e)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any, auto_save: bool = True):
        self._data[key] = value
        if auto_save:
            self.save()

    @property
    def steamcmd_dir(self) -> Path:
        return Path(self._data.get("steamcmd_dir", r"D:\steamcmd\steamcmd"))

    @steamcmd_dir.setter
    def steamcmd_dir(self, val: str):
        self._data["steamcmd_dir"] = str(val)

    @property
    def show_steamcmd_console(self) -> bool:
        return bool(self._data.get("show_steamcmd_console", False))

    @show_steamcmd_console.setter
    def show_steamcmd_console(self, val: bool):
        self._data["show_steamcmd_console"] = bool(val)

    @property
    def show_extract_console(self) -> bool:
        return bool(self._data.get("show_extract_console", False))

    @show_extract_console.setter
    def show_extract_console(self, val: bool):
        self._data["show_extract_console"] = bool(val)


cfg = AppConfig.get_instance()
