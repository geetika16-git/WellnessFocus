import sys
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QScreen

class BreakNotification(QWidget):
    def __init__(self, title, message, duration_ms=5000, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.FramelessWindowHint
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._opacity = 0.95
        self._notification_height = 0

        self.setStyleSheet("""
            QWidget#notification {
                background-color: #2d2d2d;
                border: 2px solid #ff9800;
                border-radius: 12px;
            }
            QLabel#title {
                color: #ff9800;
                font-size: 16px;
                font-weight: bold;
                padding: 8px 12px 0px 12px;
            }
            QLabel#message {
                color: #ffffff;
                font-size: 14px;
                padding: 4px 12px 12px 12px;
            }
        """)

        container = QWidget(self)
        container.setObjectName("notification")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignLeft)

        msg_label = QLabel(message)
        msg_label.setObjectName("message")
        msg_label.setWordWrap(True)
        msg_label.setAlignment(Qt.AlignLeft)

        layout.addWidget(title_label)
        layout.addWidget(msg_label)

        self.setFixedWidth(380)
        self.adjustSize()

        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        self.start_x = screen.width() - self.width() - 20
        self.start_y = 20
        self.setGeometry(self.start_x, self.start_y, self.width(), self.height())

        self.fade_in_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in_animation.setDuration(300)
        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)

        self.close_timer = QTimer(self)
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self.fade_out)

        self.fade_out_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_out_animation.setDuration(500)
        self.fade_out_animation.setStartValue(1.0)
        self.fade_out_animation.setEndValue(0.0)
        self.fade_out_animation.finished.connect(self.close)

    def show_notification(self):
        self.show()
        self.raise_()
        self.fade_in_animation.start()
        self.close_timer.start(5000)

    def fade_out(self):
        self.fade_out_animation.start()

    def keyPressEvent(self, event):
        event.ignore()

    def closeEvent(self, event):
        self.close_timer.stop()
        super().closeEvent(event)
