import os
import sys

# Ensure UTF-8 output on all operating systems and containers
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import uvicorn

from app.config import config
from app.database import init_db
from app.scheduler import scheduler
from app.bot_service import bot_worker
from web.server import app

def main():
    print("=" * 60)
    print("💳 智能消費管家 (Daily Gmail & Expense Assistant)")
    print("=" * 60)

    # Determine runtime port (Render / PaaS uses $PORT)
    port = int(os.environ.get("PORT", config.server_port))

    # 1. Initialize SQLite Database
    print("[1/3] 初始化資料庫...")
    try:
        init_db()
    except Exception as e:
        print(f"[DB] Warning during init_db: {e}")

    # 2. Start Background Scheduler (Mail Sync & Daily Reminder)
    print(f"[2/3] 啟動每日定時排程 (預設每日 {config.reminder_time} 提醒)...")
    try:
        scheduler.start()
    except Exception as e:
        print(f"[Scheduler] Warning starting scheduler: {e}")

    # 3. Start Telegram Bot if configured
    if config.telegram_enabled and config.telegram_bot_token:
        print("[3/3] 啟動 Telegram Bot 雙向記帳機器人...")
        try:
            bot_worker.start()
        except Exception as e:
            print(f"[Bot] Warning starting bot: {e}")
    else:
        print("[3/3] Telegram Bot 未啟用或未設定 Token (可於網頁設定開啟)")

    print("-" * 60)
    print(f"✨ 系統已就緒！服務監聽連接埠：{port}")
    print("=" * 60)

    # Run FastAPI web server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
