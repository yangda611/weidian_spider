__version__ = '1.0.0' 

# 包初始化文件
import os

# 设置资源目录
RESOURCE_DIR = os.path.join(os.path.dirname(__file__), 'resources')
if not os.path.exists(RESOURCE_DIR):
    os.makedirs(RESOURCE_DIR)

# 设置图标目录
ICONS_DIR = os.path.join(RESOURCE_DIR, 'icons')
if not os.path.exists(ICONS_DIR):
    os.makedirs(ICONS_DIR) 