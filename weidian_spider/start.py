from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt, QTimer
import sys
import os
import logging
from datetime import datetime

def setup_logging():
    """设置日志系统"""
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    log_file = os.path.join(log_dir, f'spider_{datetime.now().strftime("%Y%m%d")}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    """程序入口函数"""
    try:
        # 设置日志
        setup_logging()
        logging.info("Starting application...")
        
        # 创建应用实例
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        # 设置应用图标
        icon_path = os.path.join(os.path.dirname(__file__), 'resources', 'icons', 'logo.png')
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
        
        # 导入主窗口
        from .gui import MainWindow
        
        # 创建并显示主窗口
        window = MainWindow()
        window.show()
        
        # 记录启动成功
        logging.info("Application started successfully")
        
        # 进入事件循环
        return app.exec()
        
    except Exception as e:
        logging.error(f"Error starting application: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 