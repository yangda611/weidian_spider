import sys
from PyQt6.QtWidgets import QApplication
from weidian_spider.gui import MainWindow

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main()) 