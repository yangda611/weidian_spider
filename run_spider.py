import sys
import traceback
import logging
from PyQt6.QtWidgets import QApplication, QMessageBox
from weidian_spider.gui import MainWindow

def setup_logging():
    """设置日志系统"""
    import os
    from datetime import datetime
    
    # 创建logs目录
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # 设置日志文件
    log_file = os.path.join('logs', f'error_{datetime.now().strftime("%Y%m%d")}.log')
    
    # 配置日志
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def exception_hook(exc_type, exc_value, exc_traceback):
    """全局异常处理"""
    # 记录错误日志
    logging.error("Uncaught exception:", exc_info=(exc_type, exc_value, exc_traceback))
    
    # 显示错误对话框
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    QMessageBox.critical(None, "错误",
        f"程序发生错误:\n{str(exc_value)}\n\n详细信息已记录到日志文件。")

def main():
    """程序入口"""
    try:
        # 设置日志
        setup_logging()
        
        # 设置异常处理
        sys._excepthook = sys.excepthook
        sys.excepthook = exception_hook
        
        # 创建应用
        app = QApplication(sys.argv)
        
        # 设置应用样式
        app.setStyle('Fusion')
        
        # 创建主窗口
        window = MainWindow()
        window.show()
        
        # 进入事件循环
        return app.exec()
        
    except Exception as e:
        logging.error("Program startup failed", exc_info=True)
        QMessageBox.critical(None, "错误", 
            f"程序启动失败:\n{str(e)}\n\n详细信息已记录到日志文件。")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 