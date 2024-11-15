from PyQt6.QtGui import QIcon
import os

class Icons:
    def __init__(self):
        self._cache = {}
        self.icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icons')
        
    def get_icon(self, name):
        """获取图标"""
        if name not in self._cache:
            icon_file = os.path.join(self.icon_path, f'{name}.png')
            if os.path.exists(icon_file):
                self._cache[name] = QIcon(icon_file)
            else:
                print(f"Warning: Icon {name}.png not found at {icon_file}")
                self._cache[name] = QIcon()
        return self._cache[name] 