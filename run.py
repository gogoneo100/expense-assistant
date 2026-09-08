import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import uvicorn

from app.config import config
from app.database import init_db
from app.scheduler import scheduler
from app.bot_service import bot_worker

def main():
    print("=" * 60)
    print("💳 智能消費管家 (Daily Gmail & Expense Assistant)")
    print("=" * 60)

    # 1. Initialize SQLite Database
    print("[1/3] 初始化資料庫...")
    init_db()

    # 2. Start Background Scheduler (Mail Sync & Daily Reminder)
    print(f"[2/3] 啟動每日定時排程 (預設每日 {config.reminder_time} 提醒)...")
    scheduler.start()

    # 3. Start Telegram Bot if configured
    if config.telegram_enabled and config.telegram_bot_token:
        print("[3/3] 啟動 Telegram Bot 雙向記帳機器人...")
        bot_worker.start()
    else:
        print("[3/3] Telegram Bot 未啟用或未設定 Token (可於網頁設定開啟)")

    print("-" * 60)
    print(f"✨ 系統已就緒！請在瀏覽器開啟控制台：")
    print(f"👉 http://127.0.0.1:{config.server_port}")
    print("=" * 60)

    # Run FastAPI web server
    uvicorn.run(
        "web.server:app",
        host="0.0.0.0",
        port=config.server_port,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
