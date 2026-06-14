import os
import sys
import platform
import sqlite3
import shutil
import time
from datetime import datetime
from database import DatabaseManager

CHROME_HISTORY_PATH = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "Google", "Chrome", "User Data", "Default", "History"
)

EDGE_HISTORY_PATH = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "Microsoft", "Edge", "User Data", "Default", "History"
)

class WebTracker:
    def __init__(self, user_id, poll_interval=10):
        self.user_id = user_id
        self.poll_interval = poll_interval
        self.running = False
        self.last_urls = set()

    def start(self):
        self.running = True
        if platform.system() == "Windows":
            self._poll_loop_windows()
        else:
            self._poll_loop_stub()

    def stop(self):
        self.running = False

    def _poll_loop_windows(self):
        while self.running:
            self._check_browser_history("chrome", CHROME_HISTORY_PATH)
            self._check_browser_history("edge", EDGE_HISTORY_PATH)
            time.sleep(self.poll_interval)

    def _poll_loop_stub(self):
        while self.running:
            time.sleep(1)

    def _check_browser_history(self, browser_name, history_path):
        if not os.path.exists(history_path):
            return

        temp_path = history_path + ".temp"
        try:
            shutil.copy2(history_path, temp_path)
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT url, title, visit_count, last_visit_time
                FROM urls
                ORDER BY last_visit_time DESC
                LIMIT 20
            """)
            rows = cursor.fetchall()
            conn.close()
            os.remove(temp_path)

            from urllib.parse import urlparse
            for url, title, visit_count, last_visit_time in rows:
                if url in self.last_urls:
                    continue
                self.last_urls.add(url)

                try:
                    parsed = urlparse(url)
                    domain = parsed.netloc or parsed.hostname or url
                except Exception:
                    domain = url

                DatabaseManager.log_web_usage(
                    self.user_id,
                    browser_name,
                    url,
                    domain
                )

                if len(self.last_urls) > 500:
                    self.last_urls = set(list(self.last_urls)[-300:])

        except Exception:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
