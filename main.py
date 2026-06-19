import sys
import platform
import threading
from datetime import datetime
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QWidget, QMessageBox
from PySide6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import QTimer, Qt

from config_manager import ConfigManager
from database import DatabaseManager
from notifications import BreakNotification
from overlay import BreakOverlay
from window_monitor import WindowMonitor
from web_tracker import WebTracker
from admin_panel import AdminPanel

class WellnessApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wellness Focus")
        self.setGeometry(0, 0, 0, 0)

        DatabaseManager.initialize_db()

        self.config = ConfigManager.load_config()
        self.user_id = ConfigManager.get_active_user_id()

        self.eye_elapsed_minutes = 0
        self.long_elapsed_minutes = 0
        self.is_break_active = False

        self._setup_tray()
        self._setup_timers()
        self._start_monitoring()

        QTimer.singleShot(2000, self._first_run_check)

    def _setup_tray(self):
        icon = self._create_tray_icon()
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip("Wellness Focus")

        menu = QMenu()
        show_action = QAction("Show Status", self)
        show_action.triggered.connect(self.show_status)
        menu.addAction(show_action)

        admin_action = QAction("Admin Settings", self)
        admin_action.triggered.connect(self.open_admin)
        menu.addAction(admin_action)

        menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.show()

    def _create_tray_icon(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QColor("#ff9800"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, 4, 24, 24)
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "W")
        painter.end()
        return QIcon(pixmap)

    def _setup_timers(self):
        self.minute_timer = QTimer(self)
        self.minute_timer.timeout.connect(self._tick)
        self.minute_timer.start(60000)

        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self._check_limits)
        self.check_timer.start(30000)

    def _start_monitoring(self):
        if not self.user_id:
            return
        self.window_monitor = WindowMonitor(self.user_id)
        self.web_tracker = WebTracker(self.user_id)
        threading.Thread(target=self.window_monitor.start, daemon=True).start()
        threading.Thread(target=self.web_tracker.start, daemon=True).start()

    def _tick(self):
        if self.is_break_active:
            return

        self.eye_elapsed_minutes += 1
        self.long_elapsed_minutes += 1

        work_minutes = self.config.get("work_duration_minutes", 20)
        long_interval_minutes = self.config.get("long_break_interval_hours", 1) * 60

        remaining_eye = work_minutes - self.eye_elapsed_minutes
        remaining_long = long_interval_minutes - self.long_elapsed_minutes

        if remaining_eye == 2:
            self._show_notification("Eye Break Soon", "Eye break in 2 minutes. Look away from the screen soon!")
        elif remaining_eye == 1:
            self._show_notification("Eye Break in 1 Minute", "Time to rest your eyes in less than a minute!")

        if remaining_long == 2:
            self._show_notification("Long Break Soon", "Long break in 2 minutes. Time to stretch!")
        elif remaining_long == 1:
            self._show_notification("Long Break in 1 Minute", "Long break in less than a minute! Get ready to move.")

        if remaining_eye <= 0:
            self._trigger_break("eye")
        elif remaining_long <= 0:
            self._trigger_break("long")

    def _trigger_break(self, break_type):
        self.is_break_active = True
        was_bypassed = False

        if break_type == "eye":
            duration = self.config.get("break_duration_seconds", 30)
            message = self.config.get("break_message", "Time to rest your eyes!")
            self.eye_elapsed_minutes = 0
        else:
            duration = self.config.get("long_break_duration_minutes", 5) * 60
            message = self.config.get("long_break_message", "Time for a movement break!")
            self.long_elapsed_minutes = 0

        self.overlay = BreakOverlay(break_type, duration, message)
        self.overlay.showFullScreen()
        self.overlay.show()

        self.overlay_timer = QTimer(self)
        self.overlay_timer.setSingleShot(True)
        self.overlay_timer.timeout.connect(lambda: self._on_break_end(break_type))
        self.overlay_timer.start((duration + 5) * 1000)

        self.overlay.destroyed.connect(lambda: self._on_break_end(break_type))

    def _on_break_end(self, break_type):
        self.is_break_active = False
        if self.user_id and hasattr(self, 'overlay'):
            was_bypassed = getattr(self.overlay, 'bypassed', False)
            was_completed = getattr(self.overlay, 'completed', False)
            DatabaseManager.log_break(self.user_id, break_type, was_completed, was_bypassed)
        self.overlay = None

    def _show_notification(self, title, message):
        notif = BreakNotification(title, message)
        notif.show_notification()

    def _check_limits(self):
        if not self.user_id:
            return

        config = ConfigManager.load_config()
        day_name = datetime.now().strftime("%a")
        daily_limits = config.get("daily_limits", {})
        daily_limit = daily_limits.get(day_name, 120)
        total_today = DatabaseManager.get_today_total_screen_time(self.user_id)

        if total_today >= daily_limit:
            self._show_notification(
                "Daily Limit Reached",
                f"Screen time today: {total_today:.0f} min. Daily limit is {daily_limit} min for {day_name}."
            )
            return

        app_schedule = config.get("app_schedule", {})
        today_apps = DatabaseManager.get_today_app_usage(self.user_id)
        if hasattr(self, 'window_monitor'):
            current_app, _ = self.window_monitor.get_current_process()
            if current_app in app_schedule:
                schedule = app_schedule[current_app]
                allowed_days = schedule.get("allowed_days", [])
                max_minutes = schedule.get("max_minutes", 0)
                if max_minutes > 0 and today_apps.get(current_app, 0) >= max_minutes:
                    self._show_notification(
                        "App Limit Reached",
                        f"{current_app} limit reached: {max_minutes} min on {day_name}."
                    )
                elif allowed_days and day_name not in allowed_days:
                    self._show_notification(
                        "App Not Allowed Today",
                        f"{current_app} is not allowed on {day_name}."
                    )

    def show_status(self):
        if not self.user_id:
            self.tray.showMessage("Not Configured", "Configure an email in Admin Settings.", QSystemTrayIcon.Information, 3000)
            return

        total = DatabaseManager.get_today_total_screen_time(self.user_id)
        apps = DatabaseManager.get_today_app_usage(self.user_id)
        app_list = "\n".join([f"{name}: {mins:.0f}m" for name, mins in sorted(apps.items(), key=lambda x: -x[1])[:5]])

        msg = f"Screen time today: {total:.0f} min\n"
        if app_list:
            msg += f"\nTop apps:\n{app_list}"

        self.tray.showMessage("Wellness Focus - Today's Status", msg, QSystemTrayIcon.Information, 5000)

    def _first_run_check(self):
        email = ConfigManager.get_user_email()
        if not email:
            self.tray.showMessage(
                "Wellness Focus is running",
                "Click Admin Settings to configure limits and user email.",
                QSystemTrayIcon.Information,
                5000
            )

    def open_admin(self):
        dialog = AdminPanel(self)
        dialog.exec()

    def quit_app(self):
        reply = QMessageBox.question(
            self, "Quit Wellness App?",
            "Enter admin password to quit.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            QApplication.quit()

    def closeEvent(self, event):
        event.ignore()

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    wellness = WellnessApp()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
