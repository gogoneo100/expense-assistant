from datetime import datetime
from typing import Dict, Any
import requests

from app.config import config
from app.database import get_day_stats, get_db, get_budgets_status
from app.models import Category

def generate_daily_digest(date_str: str = "") -> str:
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    stats = get_day_stats(date_str)
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday_str = weekdays[dt.weekday()]

    lines = [
        f"📊 【消費每日彙整通知】",
        f"📅 日期：{date_str} ({weekday_str})",
        f"💰 今日總支出：${stats['total_amount']:,.0f} 元 (共 {stats['total_count']} 筆)",
        "--------------------------------",
        f"💳 信用卡消費：${stats['credit_card_amount']:,.0f} 元 ({stats['credit_card_count']} 筆)",
        f"💵 手動申報項目：${stats['manual_amount']:,.0f} 元 ({stats['manual_count']} 筆)",
        "--------------------------------",
        "📂 各類別支出佔比："
    ]

    if stats["by_category"]:
        # Sort by amount desc
        sorted_cat = sorted(stats["by_category"].items(), key=lambda x: x[1], reverse=True)
        for cat, amt in sorted_cat:
            percent = (amt / stats["total_amount"] * 100) if stats["total_amount"] > 0 else 0
            lines.append(f"  • {cat}: ${amt:,.0f} ({percent:.1f}%)")
    else:
        lines.append("  今日尚無任何消費紀錄")

    lines.append("--------------------------------")
    lines.append("📝 今日消費明細：")

    if stats["items"]:
        for item in stats["items"][:10]:  # Up to 10 items
            src_icon = "💳" if item["source"] == "gmail" else "💵"
            lines.append(f"  {src_icon} {item['merchant']} - ${item['amount']:,.0f} [{item['category']}]")
        if len(stats["items"]) > 10:
            lines.append(f"  ...其餘 {len(stats['items']) - 10} 筆請於網頁查看")
    else:
        lines.append("  (暫無紀錄)")

    # Check monthly budget watermark
    year_month = dt.strftime("%Y-%m")
    budgets = get_budgets_status(year_month)
    warnings = [b for b in budgets if b["status"] in ("warning", "exceeded")]
    if warnings:
        lines.append("--------------------------------")
        lines.append("⚠️ 【當月預算水位預警】")
        for w in warnings:
            if w["status"] == "exceeded":
                over = w["spent_amount"] - w["monthly_budget"]
                lines.append(f"  🚨 {w['category']}: 已用 {w['percentage']:.0f}% (${w['spent_amount']:,.0f} / 預算 ${w['monthly_budget']:,.0f}，超支 ${over:,.0f})")
            else:
                lines.append(f"  ⚠️ {w['category']}: 已達 {w['percentage']:.0f}% 水位 (${w['spent_amount']:,.0f} / 預算 ${w['monthly_budget']:,.0f}，剩餘 ${w['remaining_amount']:,.0f})")

    lines.append("--------------------------------")
    lines.append("💡 貼心提醒：今天還有現金消費或額外未記帳項目嗎？直接回傳（例如：和女友吃 1200）即可自動補記喔！")

    return "\n".join(lines)

def send_telegram_message(text: str) -> bool:
    if not config.telegram_bot_token or not config.telegram_chat_id:
        return False
    try:
        url = f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": config.telegram_chat_id,
            "text": text,
        }
        res = requests.post(url, json=payload, timeout=10)
        return res.status_code == 200
    except Exception as e:
        print(f"[Telegram] Failed to send message: {e}")
        return False

def trigger_daily_reminder(date_str: str = "") -> Dict[str, Any]:
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    summary_text = generate_daily_digest(date_str)
    stats = get_day_stats(date_str)

    telegram_sent = False
    if config.telegram_enabled and config.telegram_bot_token:
        telegram_sent = send_telegram_message(summary_text)

    # Save to daily_digests table
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO daily_digests (digest_date, total_amount, count, summary_text, sent_at)
            VALUES (?, ?, ?, ?, ?);
        """, (date_str, stats["total_amount"], stats["total_count"], summary_text, now_str))
        conn.commit()

    return {
        "success": True,
        "date": date_str,
        "summary_text": summary_text,
        "telegram_sent": telegram_sent,
        "total_amount": stats["total_amount"],
        "count": stats["total_count"]
    }
