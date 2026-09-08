import os
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config.json"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

@dataclass
class AppConfig:
    gmail_user: str = ""
    gmail_app_password: str = ""
    gmail_folder: str = "INBOX"
    sync_lookback_days: int = 7
    reminder_time: str = "21:30"  # HH:MM 24-hr
    reminder_enabled: bool = True
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_enabled: bool = False
    server_port: int = 8080
    currency: str = "TWD"

    @classmethod
    def load(cls) -> "AppConfig":
        config = cls()
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        if hasattr(config, k):
                            setattr(config, k, v)
            except Exception as e:
                print(f"[Config] Error loading {CONFIG_FILE}: {e}")
        # Environment overrides
        if os.getenv("GMAIL_USER"):
            config.gmail_user = os.getenv("GMAIL_USER")
        if os.getenv("GMAIL_APP_PASSWORD"):
            config.gmail_app_password = os.getenv("GMAIL_APP_PASSWORD")
        if os.getenv("TELEGRAM_BOT_TOKEN"):
            config.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
            config.telegram_enabled = True
        if os.getenv("TELEGRAM_CHAT_ID"):
            config.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if os.getenv("TELEGRAM_ENABLED"):
            config.telegram_enabled = os.getenv("TELEGRAM_ENABLED").lower() in ("true", "1", "yes")
        if os.getenv("REMINDER_TIME"):
            config.reminder_time = os.getenv("REMINDER_TIME")
        if os.getenv("PORT"):
            try:
                config.server_port = int(os.getenv("PORT"))
            except ValueError:
                pass
        return config

    def save(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=2)

config = AppConfig.load()
