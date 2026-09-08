import re
from datetime import datetime
from typing import Optional, List
from html.parser import HTMLParser
from app.parsers.base import BaseBankParser, ParsedTransaction

class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.ignore = False

    def handle_starttag(self, tag, attrs):
        if tag.lower() in ("style", "script", "head"):
            self.ignore = True

    def handle_endtag(self, tag):
        if tag.lower() in ("style", "script", "head"):
            self.ignore = False

    def handle_data(self, data):
        if not self.ignore:
            cleaned = data.strip()
            if cleaned:
                self.text_parts.append(cleaned)

    def get_text(self) -> str:
        return "\n".join(self.text_parts)

def strip_html(html_content: str) -> str:
    try:
        cleaned = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", html_content, flags=re.DOTALL | re.IGNORECASE)
        parser = HTMLTextExtractor()
        parser.feed(cleaned)
        return parser.get_text()
    except Exception:
        return re.sub(r"<[^>]+>", " ", html_content)

def clean_amount(val_str: str) -> float:
    try:
        cleaned = re.sub(r"[^\d.]", "", val_str)
        return float(cleaned) if cleaned else 0.0
    except Exception:
        return 0.0

def parse_trans_time(text: str, default_dt: datetime) -> tuple[str, str]:
    match = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})(?:日)?(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?", text)
    if match:
        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
        hour = int(match.group(4)) if match.group(4) else default_dt.hour
        minute = int(match.group(5)) if match.group(5) else default_dt.minute
        second = int(match.group(6)) if match.group(6) else 0
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        time_str = f"{hour:02d}:{minute:02d}:{second:02d}"
        return date_str, time_str
    return default_dt.strftime("%Y-%m-%d"), default_dt.strftime("%H:%M:%S")

def extract_merchant(text: str) -> str:
    # Remove header row labels if present
    cleaned = re.sub(r"(?:消費店家|特約商店|商店名稱)\s+(?:消費類別|類別)\s+(?:備註|金額)", " ", text)
    patterns = [
        r"(?:特約商店|特店名稱|消費商店|交易特店|消費店家|特店|商店名稱)[：:\s]+([^\r\n<,，。]{2,40})",
        r"(?:於|在)\s*([^\r\n<,，。]{2,30}?)\s*(?:刷卡|消費|授權|交易)",
    ]
    for p in patterns:
        m = re.search(p, cleaned)
        if m:
            m_text = m.group(1).strip()
            m_text = re.sub(r"\(.*?\)|（.*?）", "", m_text).strip()
            m_text = re.sub(r"[約]$", "", m_text).strip()
            # If accidentally matched table headers
            if m_text in ["消費類別", "類別", "備註", "金額", "註一"]:
                continue
            if m_text and not m_text.startswith("http"):
                return m_text
    return "一般特店"

def extract_card_last4(text: str) -> Optional[str]:
    patterns = [
        r"(?:卡號|末|後|尾號|尾數)[四4]?碼?[：:\s為]*([0-9]{4})",
        r"(?:末|後|尾)[：:\s]*([0-9]{4})",
        r"(?:\*{4}[-–]?|\*{4})([0-9]{4})",
        r"卡號[^\d\n]*[末後尾]?\s*([0-9]{4})"
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1)
    return None

def extract_amount(text: str) -> float:
    patterns = [
        r"(?:新[台臺]幣|NT\$?|TWD)\s*((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*元?",
        r"(?:消費金額|交易金額|刷卡金額|授權金額|金額)[：:\s]*(?:新[台臺]幣|NT\$?|TWD)?\s*((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*元?",
        r"((?:\d{1,3}(?:,\d{3})+|\d+))\s*元"
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            amt = clean_amount(m.group(1))
            if amt > 0:
                return amt
    return 0.0

def is_statement_or_repayment(subject: str) -> bool:
    """Filter out monthly statements and payment receipts to avoid counting bills as purchases"""
    keywords = ["電子帳單", "信用卡帳單", "信用卡繳款入帳", "繳款入帳彙整", "對帳單", "繳款確認", "繳款入帳通知"]
    return any(k in subject for k in keywords)

def is_promotional_or_marketing(subject: str) -> bool:
    """Filter out marketing ads, loan promos, installment promos, etc."""
    subj = subject.lower()
    PROMO_KEYWORDS = [
        "信貸", "貸款", "借貸", "房貸", "車貸", "融資", "月付金",
        "分期", "分期利率", "刷卡分期",
        "優惠", "促銷", "好康", "回饋", "抽獎", "抽", "活動登錄",
        "理財", "基金", "投資", "外匯", "高利活存", "利息", "定存", "etf",
        "保險", "產險", "壽險", "保單",
        "開戶", "數位帳戶", "新卡", "辦卡", "申辦", "核卡",
        "好友推薦", "專屬禮", "會員專屬", "限時", "滿額", "折扣",
        "美好回憶", "精選推薦", "即刻出發"
    ]
    return any(p in subj for p in PROMO_KEYWORDS)

# ----------------- Specific Bank Parsers -----------------

class CathayBankParser(BaseBankParser):
    bank_name = "國泰世華"

    def can_parse(self, subject: str, sender: str, body: str) -> bool:
        if is_statement_or_repayment(subject) or is_promotional_or_marketing(subject):
            return False
        if not any(k in subject for k in ["消費", "刷卡", "授權", "扣款", "交易"]):
            return False
        return "國泰世華" in subject or "cathaybk.com.tw" in sender or "國泰世華" in body

    def parse(self, subject: str, sender: str, body: str, email_dt: datetime) -> List[ParsedTransaction]:
        plain = strip_html(body)
        results = []

        # Check if this is Cathay's "消費彙整通知"
        if "消費彙整" in subject or "消費彙整" in plain or "消費授權紀錄" in plain:
            card_last4 = extract_card_last4(plain)
            blocks = re.split(r"(?:卡別\s+行動卡號後4碼|卡別)", plain)
            for b in blocks:
                amt_match = re.search(r"(?:NT\$?|TWD)\s*([0-9,]+(?:\.[0-9]+)?)", b)
                date_match = re.search(r"(\d{4}[-/]\d{2}[-/]\d{2})\s+(\d{2}:\d{2})", b)
                if amt_match and date_match:
                    amt = float(amt_match.group(1).replace(",", ""))
                    d_str = date_match.group(1).replace("/", "-")
                    t_str = date_match.group(2) + ":00"

                    # Extract merchant from text after amount
                    after_amt = b[amt_match.end():].strip().splitlines()
                    first_line = after_amt[0].strip() if after_amt else ""
                    parts = first_line.split()

                    merchant = "國泰特店消費"
                    if len(parts) >= 2:
                        if parts[0] in ["餐飲", "交通", "購物", "娛樂", "電信服務", "生活代繳", "旅行"]:
                            merchant = f"{parts[0]}消費"
                        else:
                            merchant = parts[0]
                    elif len(parts) == 1 and parts[0] not in ["註一", "註二", "無"]:
                        merchant = parts[0]

                    results.append(ParsedTransaction(
                        trans_date=d_str,
                        trans_time=t_str,
                        amount=amt,
                        currency="TWD",
                        merchant=merchant,
                        card_last4=card_last4,
                        bank=self.bank_name,
                        raw_snippet=b[:150]
                    ))
            if results:
                return results

        # Single transaction notice
        amt = extract_amount(plain)
        if amt <= 0:
            return []
        date_str, time_str = parse_trans_time(plain, email_dt)
        merchant = extract_merchant(plain)
        last4 = extract_card_last4(plain)
        return [ParsedTransaction(
            trans_date=date_str,
            trans_time=time_str,
            amount=amt,
            currency="TWD",
            merchant=merchant,
            card_last4=last4,
            bank=self.bank_name,
            raw_snippet=plain[:150]
        )]

class CTBCBankParser(BaseBankParser):
    bank_name = "中國信託"

    def can_parse(self, subject: str, sender: str, body: str) -> bool:
        if is_statement_or_repayment(subject) or is_promotional_or_marketing(subject):
            return False
        if not any(k in subject for k in ["消費", "刷卡", "授權", "扣款", "交易"]):
            return False
        return "中國信託" in subject or "ctbcbank.com" in sender or "中信卡" in subject or "中國信託" in body

    def parse(self, subject: str, sender: str, body: str, email_dt: datetime) -> List[ParsedTransaction]:
        plain = strip_html(body)
        amt = extract_amount(plain)
        if amt <= 0:
            return []
        date_str, time_str = parse_trans_time(plain, email_dt)
        merchant = extract_merchant(plain)
        last4 = extract_card_last4(plain)
        return [ParsedTransaction(
            trans_date=date_str,
            trans_time=time_str,
            amount=amt,
            currency="TWD",
            merchant=merchant,
            card_last4=last4,
            bank=self.bank_name,
            raw_snippet=plain[:150]
        )]

class ESUNBankParser(BaseBankParser):
    bank_name = "玉山銀行"

    def can_parse(self, subject: str, sender: str, body: str) -> bool:
        if is_statement_or_repayment(subject) or is_promotional_or_marketing(subject):
            return False
        if not any(k in subject for k in ["消費", "刷卡", "授權", "扣款", "交易"]):
            return False
        return "玉山" in subject or "esunbank.com.tw" in sender or "玉山銀行" in body

    def parse(self, subject: str, sender: str, body: str, email_dt: datetime) -> List[ParsedTransaction]:
        plain = strip_html(body)
        amt = extract_amount(plain)
        if amt <= 0:
            return []
        date_str, time_str = parse_trans_time(plain, email_dt)
        merchant = extract_merchant(plain)
        last4 = extract_card_last4(plain)
        return [ParsedTransaction(
            trans_date=date_str,
            trans_time=time_str,
            amount=amt,
            currency="TWD",
            merchant=merchant,
            card_last4=last4,
            bank=self.bank_name,
            raw_snippet=plain[:150]
        )]

class FubonBankParser(BaseBankParser):
    bank_name = "台北富邦"

    def can_parse(self, subject: str, sender: str, body: str) -> bool:
        if is_statement_or_repayment(subject) or is_promotional_or_marketing(subject):
            return False
        if not any(k in subject for k in ["消費", "刷卡", "授權", "扣款", "交易"]):
            return False
        return "富邦" in subject or "fubon.com" in sender or "台北富邦" in body

    def parse(self, subject: str, sender: str, body: str, email_dt: datetime) -> List[ParsedTransaction]:
        plain = strip_html(body)
        amt = extract_amount(plain)
        if amt <= 0:
            return []
        date_str, time_str = parse_trans_time(plain, email_dt)
        merchant = extract_merchant(plain)
        last4 = extract_card_last4(plain)
        return [ParsedTransaction(
            trans_date=date_str,
            trans_time=time_str,
            amount=amt,
            currency="TWD",
            merchant=merchant,
            card_last4=last4,
            bank=self.bank_name,
            raw_snippet=plain[:150]
        )]

class TaishinBankParser(BaseBankParser):
    bank_name = "台新銀行"

    def can_parse(self, subject: str, sender: str, body: str) -> bool:
        if is_statement_or_repayment(subject) or is_promotional_or_marketing(subject):
            return False
        if not any(k in subject for k in ["消費", "刷卡", "授權", "扣款", "交易"]):
            return False
        return "台新" in subject or "taishinbank.com.tw" in sender or "Richart" in subject or "台新銀行" in body

    def parse(self, subject: str, sender: str, body: str, email_dt: datetime) -> List[ParsedTransaction]:
        plain = strip_html(body)
        amt = extract_amount(plain)
        if amt <= 0:
            return []
        date_str, time_str = parse_trans_time(plain, email_dt)
        merchant = extract_merchant(plain)
        last4 = extract_card_last4(plain)
        return [ParsedTransaction(
            trans_date=date_str,
            trans_time=time_str,
            amount=amt,
            currency="TWD",
            merchant=merchant,
            card_last4=last4,
            bank=self.bank_name,
            raw_snippet=plain[:150]
        )]

class UniversalBankParser(BaseBankParser):
    bank_name = "信用卡通知"

    def can_parse(self, subject: str, sender: str, body: str) -> bool:
        if is_statement_or_repayment(subject) or is_promotional_or_marketing(subject):
            return False
        full = (subject + " " + body).lower()
        if any(w in full for w in ["信用卡", "刷卡", "簽帳"]):
            if any(k in full for k in ["消費", "授權", "扣款", "交易"]):
                return True
        keywords = ["消費通知", "授權通知", "刷卡通知", "即時通知", "交易確認", "扣款通知", "授權確認"]
        return any(k in full for k in keywords)

    def parse(self, subject: str, sender: str, body: str, email_dt: datetime) -> List[ParsedTransaction]:
        plain = strip_html(body)
        amt = extract_amount(plain)
        if amt <= 0:
            amt = extract_amount(subject)
        if amt <= 0:
            return []

        date_str, time_str = parse_trans_time(plain, email_dt)
        merchant = extract_merchant(plain)
        last4 = extract_card_last4(plain) or extract_card_last4(subject)

        detected_bank = "信用卡消費"
        for name in ["國泰世華", "中國信託", "玉山銀行", "台北富邦", "台新銀行", "聯邦銀行", "星展銀行", "永豐銀行", "兆豐銀行", "第一銀行", "華南銀行", "合庫", "渣打"]:
            if name in subject or name in plain or name in sender:
                detected_bank = name
                break

        return [ParsedTransaction(
            trans_date=date_str,
            trans_time=time_str,
            amount=amt,
            currency="TWD",
            merchant=merchant,
            card_last4=last4,
            bank=detected_bank,
            raw_snippet=plain[:150]
        )]

# Registry of parsers in order of priority
ALL_PARSERS: List[BaseBankParser] = [
    CathayBankParser(),
    CTBCBankParser(),
    ESUNBankParser(),
    FubonBankParser(),
    TaishinBankParser(),
    UniversalBankParser(),
]

def parse_email(subject: str, sender: str, body: str, email_dt: datetime) -> List[ParsedTransaction]:
    for parser in ALL_PARSERS:
        if parser.can_parse(subject, sender, body):
            results = parser.parse(subject, sender, body, email_dt)
            if results:
                return results
    return []
