import sys
from cx_Freeze import setup, Executable

build_exe_options = {
    "packages": ["os", "sys", "PyQt6", "requests", "bs4", "pandas"],
    "includes": ["queue", "sqlite3", "json", "threading", "logging"],
    "include_files": []
}

base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(
    name="商品数据爬取工具",
    version="1.0",
    description="微店/拼多多商品数据爬取工具",
    options={"build_exe": build_exe_options},
    executables=[Executable("weidian_spider/gui.py", base=base)]
) 