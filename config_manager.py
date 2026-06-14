import os
import json
import hashlib
import sys
import getpass

class ConfigManager:
    DEFAULT_CONFIG = {
        "user_email": "",
        "work_duration_minutes": 20,
        "break_duration_seconds": 30,
        "long_break_duration_minutes": 5,
        "long_break_interval_hours": 1,
        "parent_password_hash": "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9", # SHA-256 of "admin123"
        "break_message": "Time to rest your eyes! Look at something 20 feet away for 30 seconds.",
        "long_break_message": "Time for a movement break! Stretch and walk around for 5 minutes.",
        "eye_break_enabled": True,
        "long_break_enabled": True,
        "daily_limits": {
            "Mon": 120, "Tue": 120, "Wed": 120,
            "Thu": 120, "Fri": 120,
            "Sat": 180, "Sun": 180
        },
        "app_schedule": {
            "Minecraft.exe": { "max_minutes": 60, "allowed_days": ["Sat", "Sun"] },
            "RobloxPlayerBeta.exe": { "max_minutes": 30, "allowed_days": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"] }
        },
    }

    @staticmethod
    def get_app_dir():
        """Returns the standard application data folder for configuration and database."""
        if sys.platform == "win32":
            # ProgramData is accessible by both Windows Service (SYSTEM) and standard user client processes
            base_dir = os.environ.get("ProgramData", "C:\\ProgramData")
            app_dir = os.path.join(base_dir, "WellnessFocus")
        else:
            # Fallback for development/testing on macOS or Linux
            app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        
        os.makedirs(app_dir, exist_ok=True)
        return app_dir

    @classmethod
    def get_config_path(cls):
        return os.path.join(cls.get_app_dir(), "config.json")

    @classmethod
    def load_config(cls):
        path = cls.get_config_path()
        if not os.path.exists(path):
            cls.save_config(cls.DEFAULT_CONFIG)
            return cls.DEFAULT_CONFIG.copy()
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Fill in any missing default keys (migration safety)
                updated = False
                for k, v in cls.DEFAULT_CONFIG.items():
                    if k not in config:
                        config[k] = v
                        updated = True
                if updated:
                    cls.save_config(config)
                return config
        except Exception:
            return cls.DEFAULT_CONFIG.copy()

    @classmethod
    def save_config(cls, config):
        path = cls.get_config_path()
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config: {e}", file=sys.stderr)
            return False

    @classmethod
    def hash_password(cls, password):
        """Returns the SHA-256 hash of a password."""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    @classmethod
    def verify_password(cls, password):
        """Verifies a password against the stored hash."""
        config = cls.load_config()
        stored_hash = config.get("parent_password_hash", "")
        return cls.hash_password(password) == stored_hash

    @classmethod
    def update_password(cls, new_password):
        """Hashes and updates the admin/parent password."""
        config = cls.load_config()
        config["parent_password_hash"] = cls.hash_password(new_password)
        return cls.save_config(config)

    @classmethod
    def get_user_email(cls):
        """Returns the email identifier for the current user."""
        config = cls.load_config()
        return config.get("user_email", "")

    @classmethod
    def set_user_email(cls, email):
        """Sets the email identifier for the current user."""
        config = cls.load_config()
        config["user_email"] = email
        return cls.save_config(config)

    @staticmethod
    def get_windows_username():
        """Returns the current Windows username (auto-detected, no setup needed)."""
        if sys.platform == "win32":
            return os.environ.get("USERNAME") or getpass.getuser()
        return os.environ.get("USER") or getpass.getuser()

    @classmethod
    def get_active_user_id(cls):
        """Returns the best available user identifier.
        Uses Windows username by default (no setup), falls back to email if set."""
        config = cls.load_config()
        email = config.get("user_email", "")
        if email:
            return email
        return cls.get_windows_username()
