from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class ParsedTransaction:
    trans_date: str                 # YYYY-MM-DD
    trans_time: str                 # HH:MM:SS
    amount: float
    currency: str = "TWD"
    merchant: str = "未知商店"
    card_last4: Optional[str] = None
    bank: str = "信用卡消費"
    raw_snippet: str = ""

class BaseBankParser:
    bank_name: str = "通用銀行"

    def can_parse(self, subject: str, sender: str, body: str) -> bool:
        raise NotImplementedError

    def parse(self, subject: str, sender: str, body: str, email_datetime: datetime) -> List[ParsedTransaction]:
        raise NotImplementedError
