import os
import sqlite3
import sys
from datetime import datetime, date
from config_manager import ConfigManager

class DatabaseManager:
    @classmethod
    def get_db_path(cls):
        return os.path.join(ConfigManager.get_app_dir(), "activity.db")

    @classmethod
    def get_connection(cls):
        db_path = cls.get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def initialize_db(cls):
        """Initializes the SQLite database with tracking tables."""
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            
            # Table to track active windows / app usage
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_usage_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_email TEXT NOT NULL,
                    process_name TEXT NOT NULL,
                    window_title TEXT,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    duration_seconds INTEGER NOT NULL
                )
            """)
            
            # Table to track web history / visits
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS web_usage_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_email TEXT NOT NULL,
                    browser_name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Table to track breaks taken
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS break_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_email TEXT NOT NULL,
                    break_type TEXT NOT NULL, -- 'eye' or 'long'
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed INTEGER NOT NULL, -- 1 for True, 0 for False (bypassed/skipped)
                    bypassed INTEGER NOT NULL
                )
            """)
            
            conn.commit()

    @classmethod
    def log_app_usage(cls, user_email, process_name, window_title, duration_seconds):
        """Logs active app duration in seconds."""
        if duration_seconds <= 0:
            return
        try:
            with cls.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO app_usage_log (user_email, process_name, window_title, duration_seconds)
                    VALUES (?, ?, ?, ?)
                """, (user_email, process_name, window_title, duration_seconds))
                conn.commit()
        except Exception as e:
            print(f"Database error logging app usage: {e}", file=sys.stderr)

    @classmethod
    def log_web_usage(cls, user_email, browser_name, url, domain):
        """Logs web URL activity."""
        # Avoid logging empty/redundant URLs too rapidly (e.g. check duplicate)
        try:
            with cls.get_connection() as conn:
                cursor = conn.cursor()
                # Don't log the same domain within 5 seconds to prevent spamming
                cursor.execute("""
                    SELECT timestamp FROM web_usage_log 
                    WHERE user_email = ? AND url = ? ORDER BY timestamp DESC LIMIT 1
                """, (user_email, url))
                row = cursor.fetchone()
                if row:
                    last_time = datetime.strptime(row['timestamp'], "%Y-%m-%d %H:%M:%S")
                    if (datetime.now() - last_time).total_seconds() < 5:
                        return # Skip duplicate spam
                
                cursor.execute("""
                    INSERT INTO web_usage_log (user_email, browser_name, url, domain)
                    VALUES (?, ?, ?, ?)
                """, (user_email, browser_name, url, domain))
                conn.commit()
        except Exception as e:
            print(f"Database error logging web usage: {e}", file=sys.stderr)

    @classmethod
    def log_break(cls, user_email, break_type, completed, bypassed):
        """Logs eye breaks and long movement breaks."""
        try:
            with cls.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO break_log (user_email, break_type, completed, bypassed)
                    VALUES (?, ?, ?, ?)
                """, (user_email, break_type, 1 if completed else 0, 1 if bypassed else 0))
                conn.commit()
        except Exception as e:
            print(f"Database error logging break: {e}", file=sys.stderr)

    @classmethod
    def get_today_total_screen_time(cls, user_email):
        """Returns total screen time today in minutes for a given user."""
        try:
            with cls.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT SUM(duration_seconds) as total FROM app_usage_log
                    WHERE user_email = ? AND date(start_time, 'localtime') = date('now', 'localtime')
                """, (user_email,))
                row = cursor.fetchone()
                if row and row['total']:
                    return row['total'] / 60.0
                return 0.0
        except Exception as e:
            print(f"Database error fetching screen time: {e}", file=sys.stderr)
            return 0.0

    @classmethod
    def get_today_app_usage(cls, user_email):
        """Returns a dict mapping process_name to total active minutes today for a given user."""
        try:
            with cls.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT process_name, SUM(duration_seconds) as total_sec FROM app_usage_log
                    WHERE user_email = ? AND date(start_time, 'localtime') = date('now', 'localtime')
                    GROUP BY process_name
                """, (user_email,))
                return {row['process_name']: row['total_sec'] / 60.0 for row in cursor.fetchall()}
        except Exception as e:
            print(f"Database error fetching today's app usage: {e}", file=sys.stderr)
            return {}

    @classmethod
    def get_recent_web_history(cls, user_email, limit=50):
        """Returns list of recent web history records for a given user."""
        try:
            with cls.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT timestamp, browser_name, url, domain FROM web_usage_log
                    WHERE user_email = ?
                    ORDER BY timestamp DESC LIMIT ?
                """, (user_email, limit))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Database error fetching web history: {e}", file=sys.stderr)
            return []
