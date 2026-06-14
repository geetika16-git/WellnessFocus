import sys
import platform
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QApplication
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QScreen, QKeySequence, QShortcut, QAction

if platform.system() == "Windows":
    import ctypes
    import ctypes.wintypes

class BreakOverlay(QWidget):
    def __init__(self, break_type, duration_seconds, message, parent=None):
        super().__init__(parent)
        self.break_type = break_type
        self.remaining_seconds = duration_seconds
        self.message = message
        self.is_locked = True
        self.bypassed = False
        self.completed = False
        self.password_verified = False

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        screen = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(screen)

        self.setStyleSheet("""
            QWidget#overlay {
                background-color: rgba(0, 0, 0, 230);
            }
            QLabel#title {
                color: #ffffff;
                font-size: 36px;
                font-weight: bold;
            }
            QLabel#message {
                color: #e0e0e0;
                font-size: 20px;
            }
            QLabel#countdown {
                color: #ff9800;
                font-size: 72px;
                font-weight: bold;
            }
            QLabel#status {
                color: #aaaaaa;
                font-size: 16px;
            }
            QLabel#header_countdown {
                color: #ff9800;
                font-size: 28px;
                font-weight: bold;
            }
        """)

        container = QWidget(self)
        container.setObjectName("overlay")
        container.setGeometry(self.rect())

        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)

        self.header_countdown_label = QLabel("Break starts in 5...")
        self.header_countdown_label.setObjectName("header_countdown")
        self.header_countdown_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.header_countdown_label)

        title_text = "Eye Break" if break_type == "eye" else "Long Break"
        title_label = QLabel(title_text)
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        self.message_label = QLabel(message)
        self.message_label.setObjectName("message")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)

        self.countdown_label = QLabel(self.format_time(duration_seconds))
        self.countdown_label.setObjectName("countdown")
        self.countdown_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.countdown_label)

        self.status_label = QLabel("")
        self.status_label.setObjectName("status")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.countdown_label.hide()

        self.bypass_container = QWidget()
        self.bypass_container.setVisible(False)
        bypass_layout = QHBoxLayout(self.bypass_container)
        bypass_layout.setAlignment(Qt.AlignCenter)
        bypass_layout.setSpacing(8)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Admin password to skip")
        self.password_input.setMaximumWidth(250)
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                font-size: 16px;
                border: 2px solid #555;
                border-radius: 8px;
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
        self.password_input.returnPressed.connect(self.try_bypass)

        self.bypass_button = QPushButton("Skip Break")
        self.bypass_button.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                font-size: 16px;
                background-color: #ff9800;
                color: #000000;
                border: none;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ffb74d;
            }
        """)
        self.bypass_button.clicked.connect(self.try_bypass)

        bypass_layout.addWidget(self.password_input)
        bypass_layout.addWidget(self.bypass_button)
        layout.addWidget(self.bypass_container)

        self.header_countdown = 5
        self.header_timer = QTimer(self)
        self.header_timer.timeout.connect(self.update_header_countdown)
        self.header_timer.start(1000)

        self.break_timer = QTimer(self)
        self.break_timer.timeout.connect(self.update_break_timer)

        self._install_keyboard_block()

    def _install_keyboard_block(self):
        if platform.system() == "Windows":
            try:
                user32 = ctypes.windll.user32
                self._block_keys = True
            except Exception:
                self._block_keys = False
        else:
            self._block_keys = False

    def keyPressEvent(self, event):
        if self.password_verified:
            super().keyPressEvent(event)
            return
        event.accept()

    def showEvent(self, event):
        super().showEvent(event)
        self.activateWindow()
        self.raise_()

    def update_header_countdown(self):
        self.header_countdown -= 1
        if self.header_countdown > 0:
            self.header_countdown_label.setText(f"Break starts in {self.header_countdown}...")
        else:
            self.header_timer.stop()
            self.header_countdown_label.setText("Break time!")
            self.countdown_label.show()
            self.bypass_container.setVisible(True)
            self.break_timer.start(1000)

    def update_break_timer(self):
        self.remaining_seconds -= 1
        self.countdown_label.setText(self.format_time(self.remaining_seconds))
        if self.remaining_seconds <= 0:
            self.break_timer.stop()
            self.completed = True
            self.close()

    def try_bypass(self):
        from config_manager import ConfigManager
        password = self.password_input.text()
        if ConfigManager.verify_password(password):
            self.password_verified = True
            self.bypassed = True
            self.break_timer.stop()
            self.status_label.setText("Break skipped by admin")
            QTimer.singleShot(1000, self.close)
        else:
            self.status_label.setText("Incorrect password")
            self.password_input.clear()
            QTimer.singleShot(2000, lambda: self.status_label.setText(""))

    def format_time(self, seconds):
        if seconds >= 60:
            mins = seconds // 60
            secs = seconds % 60
            return f"{mins}:{secs:02d}"
        return f"0:{seconds:02d}"

    def mousePressEvent(self, event):
        if not self.password_verified:
            event.accept()
        else:
            super().mousePressEvent(event)
