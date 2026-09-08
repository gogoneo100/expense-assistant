from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional, List
from datetime import datetime

class Category:
    DINING_SELF = "飲食 (自己吃)"
    DINING_GIRLFRIEND = "飲食 (和女友吃)"
    DINING_FAMILY = "飲食 (和家人吃)"
    DINING = "飲食 (其他)"
    TRANSPORT = "交通"
    SHOPPING = "購物"
    ENTERTAINMENT = "娛樂"
    BILLS = "居家帳單"
    HEALTH = "醫療保健"
    EDUCATION = "學習教育"
    OTHER = "其他"

    ALL = [
        DINING_SELF,
        DINING_GIRLFRIEND,
        DINING_FAMILY,
        DINING,
        TRANSPORT,
        SHOPPING,
        ENTERTAINMENT,
        BILLS,
        HEALTH,
        EDUCATION,
        OTHER
    ]

@dataclass
class Transaction:
    trans_date: str                 # YYYY-MM-DD
    trans_time: str                 # HH:MM:SS
    amount: float
    merchant: str
    category: str = Category.OTHER
    currency: str = "TWD"
    source: str = "manual"          # "gmail" or "manual"
    bank: Optional[str] = None      # e.g., "國泰世華", "中國信託"
    card_last4: Optional[str] = None
    note: str = ""
    email_id: Optional[str] = None  # IMAP Message-ID or UID for deduplication
    created_at: str = ""
    id: Optional[int] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self):
        return asdict(self)

@dataclass
class CategoryRule:
    keyword: str
    category: str
    id: Optional[int] = None

    def to_dict(self):
        return asdict(self)

@dataclass
class CategoryBudget:
    category: str
    monthly_budget: float = 0.0
    warning_percent: float = 80.0
    updated_at: str = ""
    id: Optional[int] = None

    def __post_init__(self):
        if not self.updated_at:
            self.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self):
        return asdict(self)
