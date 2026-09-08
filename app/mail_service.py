from __future__ import annotations
import imaplib
import email
import email.message
from email.message import Message
import email.utils
from email.header import decode_header
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from app.config import config
from app.parsers.banks import parse_email
from app.classifier import classify_merchant
from app.database import is_duplicate, add_transaction, deduplicate_existing_transactions
from app.models import Transaction, Category

def decode_mime_words(s: Optional[str]) -> str:
    if not s:
        return ""
    parts = []
    try:
        decoded = decode_header(s)
        for part, encoding in decoded:
            if isinstance(part, bytes):
                encoding = encoding or "utf-8"
                try:
                    parts.append(part.decode(encoding, errors="replace"))
                except Exception:
                    parts.append(part.decode("utf-8", errors="replace"))
            else:
                parts.append(str(part))
    except Exception:
        return str(s)
    return "".join(parts)

def get_email_body(msg: Message) -> str:
    body_parts = []
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if "attachment" not in content_disposition:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        text = payload.decode(charset, errors="replace")
                        body_parts.append(text)
                    except Exception:
                        body_parts.append(payload.decode("utf-8", errors="replace"))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            try:
                body_parts.append(payload.decode(charset, errors="replace"))
            except Exception:
                body_parts.append(payload.decode("utf-8", errors="replace"))
    return "\n".join(body_parts)

def sync_gmail(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    lookback_days: Optional[int] = None,
    max_emails: int = 300
) -> Dict[str, Any]:
    """
    Connect to Gmail via IMAP and fetch credit card notification emails.
    Supports custom date ranges (start_date ~ end_date) or lookback_days.
    """
    if not config.gmail_user or not config.gmail_app_password:
        return {
            "success": False,
            "error": "未設定 Gmail 帳號或應用程式密碼，請至設定頁面配置。",
            "synced_count": 0,
            "skipped_count": 0
        }

    synced_count = 0
    skipped_count = 0
    error_list = []

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(config.gmail_user, config.gmail_app_password)
        mail.select(config.gmail_folder or "INBOX")

        # Build search criteria
        criteria_parts = []
        if start_date:
            try:
                s_dt = datetime.strptime(start_date.strip(), "%Y-%m-%d")
                criteria_parts.append(f'SINCE "{s_dt.strftime("%d-%b-%Y")}"')
            except Exception:
                pass
        if end_date:
            try:
                e_dt = datetime.strptime(end_date.strip(), "%Y-%m-%d") + timedelta(days=1)
                criteria_parts.append(f'BEFORE "{e_dt.strftime("%d-%b-%Y")}"')
            except Exception:
                pass

        if not criteria_parts:
            days = lookback_days or config.sync_lookback_days or 7
            since_date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
            criteria_parts.append(f'SINCE "{since_date}"')

        search_criteria = f'({" ".join(criteria_parts)})'
        status, messages = mail.search(None, search_criteria)

        if status != "OK" or not messages[0]:
            mail.logout()
            return {"success": True, "synced_count": 0, "skipped_count": 0, "message": "此期間內無相符信件"}

        msg_ids = messages[0].split()
        # Take the most recent messages up to max_emails
        recent_ids = msg_ids[-max_emails:] if len(msg_ids) > max_emails else msg_ids

        # Keywords for fast header peek pre-filtering
        RELEVANT_KEYWORDS = [
            "消費", "刷卡", "授權", "扣款", "交易", "通知",
            "信用卡", "金融卡", "簽帳", "bank", "card",
            "國泰", "中信", "玉山", "富邦", "台新", "聯邦", "星展", "永豐", "兆豐"
        ]

        from app.parsers.banks import is_statement_or_repayment

        for m_id in reversed(recent_ids):
            try:
                # Fast header peek to check subject and sender first
                res, header_data = mail.fetch(m_id, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE MESSAGE-ID)])")
                if res != "OK" or not header_data or not header_data[0]:
                    continue
                header_msg = email.message_from_bytes(header_data[0][1])
                subject = decode_mime_words(header_msg.get("Subject", ""))
                sender = decode_mime_words(header_msg.get("From", ""))

                # Check if this email looks like a transaction or bank notice
                full_header_text = (subject + " " + sender).lower()
                if not any(k.lower() in full_header_text for k in RELEVANT_KEYWORDS):
                    continue

                if is_statement_or_repayment(subject):
                    continue

                # Download full email
                res, msg_data = mail.fetch(m_id, "(RFC822)")
                if res != "OK":
                    continue
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                message_id = msg.get("Message-ID", f"imap-{m_id.decode()}")

                # Date parsing
                date_header = msg.get("Date")
                email_dt = datetime.now()
                if date_header:
                    parsed_tuple = email.utils.parsedate_to_datetime(date_header)
                    if parsed_tuple:
                        email_dt = parsed_tuple

                body = get_email_body(msg)
                parsed_list = parse_email(subject, sender, body, email_dt)

                for idx, parsed in enumerate(parsed_list):
                    item_email_id = f"{message_id}#{idx}" if len(parsed_list) > 1 else message_id
                    category = classify_merchant(parsed.merchant)

                    # Check duplication (with smart merchant & timestamp matching)
                    if is_duplicate(
                        item_email_id,
                        parsed.trans_date,
                        parsed.amount,
                        parsed.merchant,
                        parsed.card_last4,
                        parsed.trans_time,
                        category
                    ):
                        skipped_count += 1
                        continue

                    tx = Transaction(
                        trans_date=parsed.trans_date,
                        trans_time=parsed.trans_time,
                        amount=parsed.amount,
                        currency=parsed.currency,
                        merchant=parsed.merchant,
                        category=category,
                        source="gmail",
                        bank=parsed.bank,
                        card_last4=parsed.card_last4,
                        note=f"Gmail 自動匯入: {subject[:30]}",
                        email_id=item_email_id
                    )
                    add_transaction(tx)
                    synced_count += 1
            except Exception as item_err:
                error_list.append(f"信件處理失敗: {str(item_err)}")

        mail.logout()
        # Clean any historical duplicates that might have been synced previously
        deduplicate_existing_transactions()
        return {
            "success": True,
            "synced_count": synced_count,
            "skipped_count": skipped_count,
            "errors": error_list[:5]
        }

    except Exception as conn_err:
        return {
            "success": False,
            "error": f"連線至 Gmail 失敗: {str(conn_err)}。請確認帳號與應用程式密碼是否正確。",
            "synced_count": 0,
            "skipped_count": 0
        }

def seed_demo_transactions() -> int:
    """
    Seed realistic sample transactions for demonstration / initial testing.
    """
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    two_days_ago_str = (now - timedelta(days=2)).strftime("%Y-%m-%d")

    samples = [
        # Today
        Transaction(
            trans_date=today_str, trans_time="08:45:00", amount=145.0,
            merchant="星巴克 信義門市", category=Category.DINING, source="gmail",
            bank="國泰世華", card_last4="1688", note="早餐咖啡拿鐵"
        ),
        Transaction(
            trans_date=today_str, trans_time="12:30:00", amount=120.0,
            merchant="八方雲集 鍋貼", category=Category.DINING, source="manual",
            bank=None, card_last4=None, note="午餐現金支付"
        ),
        Transaction(
            trans_date=today_str, trans_time="13:15:00", amount=280.0,
            merchant="Uber 乘車", category=Category.TRANSPORT, source="gmail",
            bank="中信卡", card_last4="8821", note="拜訪客戶計程車"
        ),
        Transaction(
            trans_date=today_str, trans_time="18:20:00", amount=460.0,
            merchant="全聯福利中心", category=Category.SHOPPING, source="gmail",
            bank="玉山銀行", card_last4="3390", note="晚餐食材採買"
        ),
        # Yesterday
        Transaction(
            trans_date=yesterday_str, trans_time="12:10:00", amount=95.0,
            merchant="7-11 統一超商", category=Category.DINING, source="manual",
            bank=None, card_last4=None, note="涼麵加無糖綠"
        ),
        Transaction(
            trans_date=yesterday_str, trans_time="20:00:00", amount=390.0,
            merchant="Netflix 影音串流", category=Category.ENTERTAINMENT, source="gmail",
            bank="台新銀行", card_last4="5512", note="每月高級會員方案"
        ),
        # Two days ago
        Transaction(
            trans_date=two_days_ago_str, trans_time="14:00:00", amount=1490.0,
            merchant="台灣高鐵", category=Category.TRANSPORT, source="gmail",
            bank="富邦銀行", card_last4="7743", note="台北至左營商務車廂"
        ),
        Transaction(
            trans_date=two_days_ago_str, trans_time="19:30:00", amount=1280.0,
            merchant="Uniqlo 網路旗艦店", category=Category.SHOPPING, source="gmail",
            bank="國泰世華", card_last4="1688", note="防風外套與發熱衣"
        ),
    ]

    added = 0
    for s in samples:
        if not is_duplicate(None, s.trans_date, s.amount, s.merchant, s.card_last4):
            add_transaction(s)
            added += 1
    return added
