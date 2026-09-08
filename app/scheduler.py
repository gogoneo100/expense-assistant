from __future__ import annotations
import time
import threading
from datetime import datetime
from typing import Optional

from app.config import config
from app.mail_service import sync_gmail
from app.reminder_service import trigger_daily_reminder

class DailyScheduler:
    def __init__(self):
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.last_reminder_date: str = ""
        self.last_sync_timestamp: float = 0

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print(f"[Scheduler] Started. Daily reminder scheduled at {config.reminder_time}")

    def stop(self):
        self.running = False

    def _run_loop(self):
        while self.running:
            try:
                now = datetime.now()
                now_str_hm = now.strftime("%H:%M")
                today_str = now.strftime("%Y-%m-%d")

                # Check daily reminder trigger
                if config.reminder_enabled and now_str_hm == config.reminder_time:
                    if self.last_reminder_date != today_str:
                        print(f"[Scheduler] Triggering scheduled daily reminder at {now_str_hm}...")
                        # 1. Sync latest mail
                        if config.gmail_user and config.gmail_app_password:
                            sync_gmail()
                        # 2. Send reminder
                        trigger_daily_reminder(today_str)
                        self.last_reminder_date = today_str

                # Periodic sync (every 60 mins)
                if config.gmail_user and config.gmail_app_password:
                    if time.time() - self.last_sync_timestamp > 3600:
                        sync_gmail()
                        self.last_sync_timestamp = time.time()

            except Exception as e:
                print(f"[Scheduler] Error in loop: {e}")

            time.sleep(30)  # Check every 30 seconds

scheduler = DailyScheduler()
