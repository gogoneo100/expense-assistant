import re
from typing import Optional, Tuple
from app.models import Category
from app.database import get_rules, add_rule

def classify_merchant(merchant: str, note: str = "") -> str:
    """
    Classify transaction into one of Category.ALL based on rules in database and companion semantics.
    """
    text = f"{merchant} {note}".lower().strip()
    if not text:
        return Category.OTHER

    # Check companion keywords first
    if any(k in text for k in ["和女友", "跟女友", "女友", "女朋友", "約會"]):
        return Category.DINING_GIRLFRIEND
    if any(k in text for k in ["和家人", "跟家人", "家人", "家庭", "爸媽", "父母", "長輩"]):
        return Category.DINING_FAMILY
    if any(k in text for k in ["自己吃", "一人吃", "獨食", "自己"]):
        return Category.DINING_SELF

    # Fetch latest rules from database
    rules = get_rules()
    for r in rules:
        kw = r["keyword"].lower()
        if kw in text:
            # Map legacy '飲食' to Category.DINING_SELF
            if r["category"] == "飲食":
                return Category.DINING_SELF
            return r["category"]

    # Simple semantic heuristics
    if any(k in text for k in ["飯", "麵", "食", "餐", "肉", "菜", "茶", "點心", "壽司", "火鍋", "甜點", "咖啡", "午餐", "晚餐", "早餐"]):
        return Category.DINING_SELF
    if any(k in text for k in ["車", "油", "捷運", "公車", "火車", "機票", "航"]):
        return Category.TRANSPORT
    if any(k in text for k in ["衣", "服", "鞋", "包", "超市", "店", "買"]):
        return Category.SHOPPING
    if any(k in text for k in ["電信", "費", "租", "水電", "保險"]):
        return Category.BILLS

    return Category.OTHER

def parse_manual_input(input_text: str) -> Tuple[float, str, str, str]:
    """
    Parse natural text like:
      - "午餐 120"
      - "和女友吃 燒肉 1500"
      - "跟家人聚餐 2600"
      - "自己吃 便當 100"
      - "計程車 250 交通"
    Returns: (amount, merchant/item, category, note)
    """
    raw = input_text.strip()
    if not raw:
        return 0.0, "", Category.OTHER, ""

    # Find number (amount)
    amt_match = re.search(r"(\d+(?:\.\d+)?)", raw)
    if not amt_match:
        return 0.0, raw, Category.OTHER, ""

    amount = float(amt_match.group(1))

    # Remove amount from text
    remaining = (raw[:amt_match.start()] + " " + raw[amt_match.end():]).strip()
    parts = remaining.split()

    explicit_cat = None
    item_parts = []
    note_parts = []

    for p in parts:
        matched_cat = None
        # Check companion shortcuts
        if p in ["和女友吃", "跟女友吃", "女友吃", "和女友", "跟女友", "女友"]:
            matched_cat = Category.DINING_GIRLFRIEND
        elif p in ["和家人吃", "跟家人吃", "家人吃", "和家人", "跟家人", "家人", "家庭聚餐", "家人聚餐", "和家人聚餐", "跟家人聚餐"]:
            matched_cat = Category.DINING_FAMILY
        elif p in ["自己吃", "一人吃", "獨食", "自己"]:
            matched_cat = Category.DINING_SELF
        else:
            for cat in Category.ALL:
                if p == cat or p in [f"#{cat}", f"[{cat}]"]:
                    matched_cat = cat
                    break

        if matched_cat and not explicit_cat:
            explicit_cat = matched_cat
        else:
            if not item_parts:
                item_parts.append(p)
            else:
                note_parts.append(p)

    merchant = " ".join(item_parts) if item_parts else "日常消費"
    note = " ".join(note_parts)

    category = explicit_cat if explicit_cat else classify_merchant(merchant, note)

    return amount, merchant, category, note
