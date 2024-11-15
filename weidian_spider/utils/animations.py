from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QPoint, QSize
from PyQt6.QtWidgets import QWidget

class AnimationHelper:
    @staticmethod
    def fade_in(widget: QWidget, duration=300):
        """淡入动画"""
        animation = QPropertyAnimation(widget, b"windowOpacity")
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        animation.start()
        
    @staticmethod
    def button_click(button: QWidget):
        """按钮点击动画"""
        animation = QPropertyAnimation(button, b"size")
        animation.setDuration(100)
        original_size = button.size()
        animation.setStartValue(original_size)
        animation.setEndValue(QSize(original_size.width() * 0.9, original_size.height() * 0.9))
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        animation.finished.connect(lambda: AnimationHelper.button_restore(button, original_size))
        animation.start()
        
    @staticmethod
    def button_restore(button: QWidget, original_size):
        """按钮恢复动画"""
        animation = QPropertyAnimation(button, b"size")
        animation.setDuration(100)
        animation.setStartValue(button.size())
        animation.setEndValue(original_size)
        animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        animation.start() 