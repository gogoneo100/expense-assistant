from __future__ import annotations
import time
import threading
from datetime import datetime
from typing import Optional
import requests

from app.config import config
from app.classifier import parse_manual_input
from app.database import add_transaction, get_day_stats
from app.models import Transaction
from app.reminder_service import generate_daily_digest
from app.mail_service import sync_gmail

class TelegramBotWorker:
    def __init__(self):
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.last_update_id = 0

    def start(self):
        if not config.telegram_bot_token or not config.telegram_enabled:
            return
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.thread.start()
        print("[Telegram Bot] Polling started.")

    def stop(self):
        self.running = False

    def _send_reply(self, chat_id: int, text: str):
        url = f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
        except Exception as e:
            print(f"[Telegram Bot] Reply error: {e}")

    def _handle_message(self, message: dict):
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "").strip()
        if not chat_id or not text:
            return

        # Auto record authorized chat id if not set
        if not config.telegram_chat_id:
            config.telegram_chat_id = str(chat_id)
            config.save()

        # Command handling
        if text.startswith("/start") or text.startswith("/help"):
            reply = (
                "👋 歡迎使用【智能消費管家】！\n\n"
                "📌 隨手記帳功能：\n"
                "直接傳送文字，例如：\n"
                " • 「午餐 120」\n"
                " • 「計程車 250 交通」\n"
                " • 「全聯買菜 530 購物」\n\n"
                "📌 常用指令：\n"
                " /today - 查詢今日花費與類別統計\n"
                " /sync  - 立即觸發 Gmail 信用卡信件同步\n"
                " /help  - 查看說明"
            )
            self._send_reply(chat_id, reply)
            return

        if text.startswith("/today"):
            digest = generate_daily_digest()
            self._send_reply(chat_id, digest)
            return

        if text.startswith("/sync"):
            self._send_reply(chat_id, "🔄 正在同步 Gmail 信用卡通知信件中...")
            res = sync_gmail()
            if res.get("success"):
                self._send_reply(chat_id, f"✅ 同步完成！\n新增信件交易：{res.get('synced_count', 0)} 筆\n已存在略過：{res.get('skipped_count', 0)} 筆")
            else:
                self._send_reply(chat_id, f"⚠️ 同步失敗：{res.get('error')}")
            return

        # Natural manual expense entry
        amt, merchant, cat, note = parse_manual_input(text)
        if amt > 0:
            now = datetime.now()
            tx = Transaction(
                trans_date=now.strftime("%Y-%m-%d"),
                trans_time=now.strftime("%H:%M:%S"),
                amount=amt,
                currency="TWD",
                merchant=merchant,
                category=cat,
                source="manual",
                note=note or "Telegram 申報",
                bank=None,
                card_last4=None
            )
            add_transaction(tx)
            today_stats = get_day_stats(now.strftime("%Y-%m-%d"))

            reply = (
                f"✅ 已成功為您記錄花費！\n"
                f"💰 金額：${amt:,.0f} 元\n"
                f"🏷️ 項目：{merchant}\n"
                f"📂 分類：{cat}\n"
                f"--------------------\n"
                f"📊 今日累計支出：${today_stats['total_amount']:,.0f} 元 (共 {today_stats['total_count']} 筆)"
            )
            self._send_reply(chat_id, reply)
        else:
            self._send_reply(
                chat_id,
                "❓ 無法辨識金額，請輸入包含金額的文字，例如：\n「午餐 120」或「停車費 60 交通」"
            )

    def _polling_loop(self):
        while self.running:
            try:
                url = f"https://api.telegram.org/bot{config.telegram_bot_token}/getUpdates"
                params = {"offset": self.last_update_id + 1, "timeout": 20}
                res = requests.get(url, params=params, timeout=25)
                if res.status_code == 200:
                    data = res.json()
                    for update in data.get("result", []):
                        self.last_update_id = update["update_id"]
                        if "message" in update:
                            self._handle_message(update["message"])
            except Exception as e:
                # Network error or timeout, sleep slightly and continue
                time.sleep(5)
            time.sleep(1)

bot_worker = TelegramBotWorker()
