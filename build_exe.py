# -*- coding: utf-8 -*-
"""
PyInstaller 打包脚本 (build_exe.py)
"""
import sys
import os
import shutil
import argparse
import PyInstaller.__main__

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def build():
    parser = argparse.ArgumentParser(description="Build SteamCMD Ticket Extractor EXE")
    parser.add_argument("--onefile", action="store_true", default=True, help="打包为单个 EXE (默认)")
    parser.add_argument("--onedir", action="store_true", help="打包为单目录")
    parser.add_argument("--console", action="store_true", help="保留控制台窗口")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    dist_dir = os.path.join(script_dir, "dist")
    build_dir = os.path.join(script_dir, "build")

    for d in [build_dir, dist_dir]:
        if os.path.exists(d):
            try:
                shutil.rmtree(d)
            except Exception:
                pass

    pyinstaller_args = [
        "main.py",
        "--name=SteamCMD-Ticket-Extractor",
        "--clean",
        f"--paths={script_dir}",
        f"--add-data={os.path.join(script_dir, 'gui', 'assets')};gui/assets",
        "--distpath", dist_dir,
        "--workpath", build_dir,
        "--specpath", build_dir,

        "--hidden-import=PyQt6",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=PyQt6.sip",
        "--hidden-import=json",
        "--hidden-import=ctypes",
        "--hidden-import=ctypes.wintypes",
        "--hidden-import=config",
        "--hidden-import=core",
        "--hidden-import=core.steamcmd_direct",
        "--hidden-import=gui",
        "--hidden-import=gui.styles",
        "--hidden-import=gui.components",
        "--hidden-import=gui.main_window",
    ]

    if args.onedir:
        pyinstaller_args.append("--onedir")
    else:
        pyinstaller_args.append("--onefile")

    if args.console:
        pyinstaller_args.append("--console")
    else:
        pyinstaller_args.append("--noconsole")

    PyInstaller.__main__.run(pyinstaller_args)

    src_config = os.path.join(script_dir, "config.json")
    if os.path.exists(src_config):
        shutil.copy2(src_config, os.path.join(dist_dir, "config.json"))

    print("打包完成，输出目录:", dist_dir)

if __name__ == "__main__":
    build()
