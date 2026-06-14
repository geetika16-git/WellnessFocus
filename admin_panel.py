import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QPushButton, QWidget,
    QListWidget, QListWidgetItem, QSpinBox,
    QTimeEdit, QGroupBox, QFormLayout, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QTextEdit, QComboBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from config_manager import ConfigManager
from database import DatabaseManager
from datetime import datetime

class AdminPanel(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wellness Focus — Admin Settings")
        self.setMinimumSize(700, 500)
        self.config = ConfigManager.load_config()
        self.user_id = ConfigManager.get_active_user_id()

        self._setup_ui()
        self._load_config()
        self._load_reports()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        self.tabs.addTab(self._build_general_tab(), "General")
        self.tabs.addTab(self._build_limits_tab(), "Limits")
        self.tabs.addTab(self._build_blocks_tab(), "Blocks")
        self.tabs.addTab(self._build_reports_tab(), "Reports")
        self.tabs.addTab(self._build_password_tab(), "Password")

        layout.addWidget(self.tabs)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _build_general_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("user@example.com (optional, for cloud sync)")
        layout.addRow("User Email:", self.email_input)

        self.work_min_input = QSpinBox()
        self.work_min_input.setRange(1, 120)
        self.work_min_input.setSuffix(" min")
        layout.addRow("Work interval:", self.work_min_input)

        self.break_sec_input = QSpinBox()
        self.break_sec_input.setRange(5, 300)
        self.break_sec_input.setSuffix(" sec")
        layout.addRow("Eye break duration:", self.break_sec_input)

        self.long_break_min_input = QSpinBox()
        self.long_break_min_input.setRange(1, 30)
        self.long_break_min_input.setSuffix(" min")
        layout.addRow("Long break duration:", self.long_break_min_input)

        self.long_interval_input = QSpinBox()
        self.long_interval_input.setRange(1, 8)
        self.long_interval_input.setSuffix(" hour(s)")
        layout.addRow("Long break interval:", self.long_interval_input)

        self.eye_enabled = QComboBox()
        self.eye_enabled.addItems(["Enabled", "Disabled"])
        layout.addRow("Eye breaks:", self.eye_enabled)

        self.long_enabled = QComboBox()
        self.long_enabled.addItems(["Enabled", "Disabled"])
        layout.addRow("Long breaks:", self.long_enabled)

        save_btn = QPushButton("Save General Settings")
        save_btn.clicked.connect(self._save_general)
        layout.addRow(save_btn)

        return tab

    def _build_limits_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        limits_group = QGroupBox("Daily Limits (minutes)")
        limits_layout = QFormLayout(limits_group)
        self.day_inputs = {}
        for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            inp = QSpinBox()
            inp.setRange(0, 1440)
            inp.setSuffix(" min")
            self.day_inputs[day] = inp
            limits_layout.addRow(f"{day}:", inp)
        layout.addWidget(limits_group)

        app_group = QGroupBox("App Schedule (process_name: max_min,allowed_days)")
        app_layout = QVBoxLayout(app_group)
        self.app_schedule_input = QTextEdit()
        self.app_schedule_input.setPlaceholderText(
            "Minecraft.exe: 60,Sat,Sun\nRobloxPlayerBeta.exe: 30,Mon,Tue,Wed,Thu,Fri,Sat,Sun"
        )
        app_layout.addWidget(self.app_schedule_input)
        layout.addWidget(app_group)

        save_btn = QPushButton("Save Limits")
        save_btn.clicked.connect(self._save_limits)
        layout.addWidget(save_btn)
        layout.addStretch()

        return tab

    def _build_blocks_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        web_group = QGroupBox("Blocked Websites")
        web_layout = QVBoxLayout(web_group)
        self.blocked_websites_input = QTextEdit()
        self.blocked_websites_input.setPlaceholderText("youtube.com\ntiktok.com\ninstagram.com")
        web_layout.addWidget(self.blocked_websites_input)
        layout.addWidget(web_group)

        save_btn = QPushButton("Save Blocks")
        save_btn.clicked.connect(self._save_blocks)
        layout.addWidget(save_btn)
        layout.addStretch()

        return tab

    def _build_reports_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.report_label = QLabel("Loading...")
        self.report_label.setFont(QFont("Courier", 10))
        layout.addWidget(self.report_label)

        refresh_btn = QPushButton("Refresh Reports")
        refresh_btn.clicked.connect(self._load_reports)
        layout.addWidget(refresh_btn)
        layout.addStretch()

        return tab

    def _build_password_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)

        self.current_pw = QLineEdit()
        self.current_pw.setEchoMode(QLineEdit.Password)
        layout.addRow("Current password:", self.current_pw)

        self.new_pw = QLineEdit()
        self.new_pw.setEchoMode(QLineEdit.Password)
        layout.addRow("New password:", self.new_pw)

        self.confirm_pw = QLineEdit()
        self.confirm_pw.setEchoMode(QLineEdit.Password)
        layout.addRow("Confirm password:", self.confirm_pw)

        save_btn = QPushButton("Change Password")
        save_btn.clicked.connect(self._save_password)
        layout.addRow(save_btn)

        return tab

    def _load_config(self):
        c = self.config

        self.email_input.setText(c.get("user_email", ""))
        self.work_min_input.setValue(c.get("work_duration_minutes", 20))
        self.break_sec_input.setValue(c.get("break_duration_seconds", 30))
        self.long_break_min_input.setValue(c.get("long_break_duration_minutes", 5))
        self.long_interval_input.setValue(c.get("long_break_interval_hours", 1))
        self.eye_enabled.setCurrentIndex(0 if c.get("eye_break_enabled", True) else 1)
        self.long_enabled.setCurrentIndex(0 if c.get("long_break_enabled", True) else 1)

        daily_limits = c.get("daily_limits", {})
        for day, inp in self.day_inputs.items():
            inp.setValue(daily_limits.get(day, 120))

        app_schedule = c.get("app_schedule", {})
        lines = []
        for app, info in app_schedule.items():
            max_min = info.get("max_minutes", 0)
            days = ",".join(info.get("allowed_days", []))
            lines.append(f"{app}: {max_min},{days}")
        self.app_schedule_input.setText("\n".join(lines))

        blocked = c.get("blocked_websites", [])
        self.blocked_websites_input.setText("\n".join(blocked))

    def _save_general(self):
        self.config["user_email"] = self.email_input.text().strip()
        self.config["work_duration_minutes"] = self.work_min_input.value()
        self.config["break_duration_seconds"] = self.break_sec_input.value()
        self.config["long_break_duration_minutes"] = self.long_break_min_input.value()
        self.config["long_break_interval_hours"] = self.long_interval_input.value()
        self.config["eye_break_enabled"] = self.eye_enabled.currentIndex() == 0
        self.config["long_break_enabled"] = self.long_enabled.currentIndex() == 0

        if ConfigManager.save_config(self.config):
            QMessageBox.information(self, "Saved", "General settings saved.")
        else:
            QMessageBox.warning(self, "Error", "Failed to save settings.")

    def _save_limits(self):
        for day, inp in self.day_inputs.items():
            if "daily_limits" not in self.config:
                self.config["daily_limits"] = {}
            self.config["daily_limits"][day] = inp.value()

        app_schedule = {}
        for line in self.app_schedule_input.toPlainText().strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                parts = line.split(":", 1)
                app_name = parts[0].strip()
                rest = parts[1].strip()
                segments = [s.strip() for s in rest.split(",")]
                if segments and segments[0].isdigit():
                    max_min = int(segments[0])
                    days = segments[1:] if len(segments) > 1 else []
                    app_schedule[app_name] = {
                        "max_minutes": max_min,
                        "allowed_days": days
                    }
        self.config["app_schedule"] = app_schedule

        if ConfigManager.save_config(self.config):
            QMessageBox.information(self, "Saved", "Limits saved.")
        else:
            QMessageBox.warning(self, "Error", "Failed to save limits.")

    def _save_blocks(self):
        websites = [
            line.strip()
            for line in self.blocked_websites_input.toPlainText().strip().split("\n")
            if line.strip()
        ]
        self.config["blocked_websites"] = websites

        if ConfigManager.save_config(self.config):
            QMessageBox.information(self, "Saved", "Block list saved.")
        else:
            QMessageBox.warning(self, "Error", "Failed to save block list.")

    def _save_password(self):
        current = self.current_pw.text()
        new = self.new_pw.text()
        confirm = self.confirm_pw.text()

        if not ConfigManager.verify_password(current):
            QMessageBox.warning(self, "Error", "Current password is incorrect.")
            return

        if not new:
            QMessageBox.warning(self, "Error", "New password cannot be empty.")
            return

        if new != confirm:
            QMessageBox.warning(self, "Error", "Passwords do not match.")
            return

        if ConfigManager.update_password(new):
            QMessageBox.information(self, "Saved", "Password changed.")
            self.current_pw.clear()
            self.new_pw.clear()
            self.confirm_pw.clear()
        else:
            QMessageBox.warning(self, "Error", "Failed to change password.")

    def _load_reports(self):
        if not self.user_id:
            self.report_label.setText("No user configured.")
            return

        total = DatabaseManager.get_today_total_screen_time(self.user_id)
        apps = DatabaseManager.get_today_app_usage(self.user_id)
        web = DatabaseManager.get_recent_web_history(self.user_id, limit=10)

        lines = [f"Date: {datetime.now().strftime('%A, %Y-%m-%d')}"]
        lines.append(f"User: {self.user_id}")
        lines.append("")
        lines.append(f"Screen Time Today: {total:.0f} min")
        lines.append("")
        lines.append("--- App Usage ---")
        for name, mins in sorted(apps.items(), key=lambda x: -x[1]):
            lines.append(f"  {name}: {mins:.0f} min")

        lines.append("")
        lines.append("--- Recent Web History ---")
        for entry in web[:10]:
            lines.append(f"  {entry['timestamp'][:16]} | {entry['domain']}")

        self.report_label.setText("\n".join(lines))
