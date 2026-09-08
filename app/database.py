import sqlite3
import re
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
from app.config import DATA_DIR
from app.models import Transaction, CategoryRule, Category, CategoryBudget

DB_PATH = DATA_DIR / "expenses.db"

def get_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        # Transactions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trans_date TEXT NOT NULL,
                trans_time TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'TWD',
                merchant TEXT NOT NULL,
                category TEXT NOT NULL,
                source TEXT DEFAULT 'manual',
                bank TEXT,
                card_last4 TEXT,
                note TEXT DEFAULT '',
                email_id TEXT,
                created_at TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trans_date ON transactions(trans_date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trans_email_id ON transactions(email_id);")

        # Category Rules Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS category_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL
            );
        """)

        # Daily Digests Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_digests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                digest_date TEXT UNIQUE NOT NULL,
                total_amount REAL NOT NULL,
                count INTEGER NOT NULL,
                summary_text TEXT NOT NULL,
                sent_at TEXT NOT NULL
            );
        """)

        # Seed initial rules if empty
        cursor.execute("SELECT COUNT(*) FROM category_rules;")
        if cursor.fetchone()[0] == 0:
            default_rules = [
                # 飲食
                ("uber eats", Category.DINING_SELF),
                ("foodpanda", Category.DINING_SELF),
                ("7-11", Category.DINING_SELF),
                ("統一超商", Category.DINING_SELF),
                ("全家", Category.DINING_SELF),
                ("全家便利商店", Category.DINING_SELF),
                ("萊爾富", Category.DINING_SELF),
                ("ok超商", Category.DINING_SELF),
                ("星巴克", Category.DINING_SELF),
                ("starbucks", Category.DINING_SELF),
                ("麥當勞", Category.DINING_SELF),
                ("肯德基", Category.DINING_SELF),
                ("摩斯漢堡", Category.DINING_SELF),
                ("路易莎", Category.DINING_SELF),
                ("八方雲集", Category.DINING_SELF),
                ("壽司郎", Category.DINING_SELF),
                ("爭鮮", Category.DINING_SELF),
                ("藏壽司", Category.DINING_SELF),
                ("瓦城", Category.DINING_SELF),
                ("鼎泰豐", Category.DINING_SELF),
                ("咖啡", Category.DINING_SELF),
                ("午餐", Category.DINING_SELF),
                ("晚餐", Category.DINING_SELF),
                ("早餐", Category.DINING_SELF),
                ("宵夜", Category.DINING_SELF),
                ("便當", Category.DINING_SELF),
                ("飲料", Category.DINING_SELF),
                ("餐廳", Category.DINING_SELF),

                # 交通
                ("uber", Category.TRANSPORT),
                ("台灣大車隊", Category.TRANSPORT),
                ("大都會車隊", Category.TRANSPORT),
                ("yoxi", Category.TRANSPORT),
                ("高鐵", Category.TRANSPORT),
                ("台灣高鐵", Category.TRANSPORT),
                ("台鐵", Category.TRANSPORT),
                ("捷運", Category.TRANSPORT),
                ("悠遊卡", Category.TRANSPORT),
                ("一卡通", Category.TRANSPORT),
                ("中油", Category.TRANSPORT),
                ("台灣中油", Category.TRANSPORT),
                ("全國加油站", Category.TRANSPORT),
                ("台亞", Category.TRANSPORT),
                ("停車", Category.TRANSPORT),
                ("停車費", Category.TRANSPORT),
                ("嘟嘟房", Category.TRANSPORT),
                ("城市車旅", Category.TRANSPORT),
                ("irent", Category.TRANSPORT),
                ("goshare", Category.TRANSPORT),
                ("wemo", Category.TRANSPORT),
                ("長榮航空", Category.TRANSPORT),
                ("中華航空", Category.TRANSPORT),
                ("星宇航空", Category.TRANSPORT),

                # 購物
                ("蝦皮", Category.SHOPPING),
                ("shopee", Category.SHOPPING),
                ("momo", Category.SHOPPING),
                ("pchome", Category.SHOPPING),
                ("yahoo", Category.SHOPPING),
                ("淘寶", Category.SHOPPING),
                ("amazon", Category.SHOPPING),
                ("uniqlo", Category.SHOPPING),
                ("gu", Category.SHOPPING),
                ("zara", Category.SHOPPING),
                ("屈臣氏", Category.SHOPPING),
                ("康是美", Category.SHOPPING),
                ("寶雅", Category.SHOPPING),
                ("全聯", Category.SHOPPING),
                ("全聯福利中心", Category.SHOPPING),
                ("家樂福", Category.SHOPPING),
                ("好市多", Category.SHOPPING),
                ("costco", Category.SHOPPING),
                ("大潤發", Category.SHOPPING),
                ("特力屋", Category.SHOPPING),
                ("ikea", Category.SHOPPING),
                ("無印良品", Category.SHOPPING),
                ("muji", Category.SHOPPING),

                # 娛樂
                ("netflix", Category.ENTERTAINMENT),
                ("hbomax", Category.ENTERTAINMENT),
                ("hbo", Category.ENTERTAINMENT),
                ("spotify", Category.ENTERTAINMENT),
                ("youtube", Category.ENTERTAINMENT),
                ("disney+", Category.ENTERTAINMENT),
                ("steam", Category.ENTERTAINMENT),
                ("playstation", Category.ENTERTAINMENT),
                ("nintendo", Category.ENTERTAINMENT),
                ("威秀影城", Category.ENTERTAINMENT),
                ("國賓影城", Category.ENTERTAINMENT),
                ("秀泰影城", Category.ENTERTAINMENT),
                ("錢櫃", Category.ENTERTAINMENT),
                ("好樂迪", Category.ENTERTAINMENT),

                # 居家帳單
                ("中華電信", Category.BILLS),
                ("台灣大哥大", Category.BILLS),
                ("遠傳電信", Category.BILLS),
                ("台電", Category.BILLS),
                ("台灣電力", Category.BILLS),
                ("自來水", Category.BILLS),
                ("台北自來水", Category.BILLS),
                ("瓦斯", Category.BILLS),
                ("天然氣", Category.BILLS),
                ("管理費", Category.BILLS),
                ("房租", Category.BILLS),

                # 醫療保健
                ("診所", Category.HEALTH),
                ("醫院", Category.HEALTH),
                ("健保", Category.HEALTH),
                ("藥局", Category.HEALTH),
                ("屈臣氏藥妝", Category.HEALTH),

                # 學習教育
                ("博客來", Category.EDUCATION),
                ("誠品", Category.EDUCATION),
                ("hahow", Category.EDUCATION),
                ("udemy", Category.EDUCATION),
                ("coursera", Category.EDUCATION),
            ]
            cursor.executemany("INSERT INTO category_rules (keyword, category) VALUES (?, ?);", default_rules)

        # Companion specific rules for dining
        companion_rules = [
            ("和女友吃", Category.DINING_GIRLFRIEND),
            ("跟女友吃", Category.DINING_GIRLFRIEND),
            ("和女友", Category.DINING_GIRLFRIEND),
            ("跟女友", Category.DINING_GIRLFRIEND),
            ("女朋友", Category.DINING_GIRLFRIEND),
            ("女友", Category.DINING_GIRLFRIEND),
            ("和家人吃", Category.DINING_FAMILY),
            ("跟家人吃", Category.DINING_FAMILY),
            ("和家人", Category.DINING_FAMILY),
            ("跟家人", Category.DINING_FAMILY),
            ("家人聚餐", Category.DINING_FAMILY),
            ("家庭聚餐", Category.DINING_FAMILY),
            ("家人", Category.DINING_FAMILY),
            ("家庭", Category.DINING_FAMILY),
            ("自己吃", Category.DINING_SELF),
            ("一人吃", Category.DINING_SELF),
            ("獨食", Category.DINING_SELF),
            ("自己", Category.DINING_SELF),
        ]
        cursor.executemany("INSERT OR IGNORE INTO category_rules (keyword, category) VALUES (?, ?);", companion_rules)

        # Category Budgets Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS category_budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT UNIQUE NOT NULL,
                monthly_budget REAL NOT NULL DEFAULT 0,
                warning_percent REAL NOT NULL DEFAULT 80.0,
                updated_at TEXT NOT NULL
            );
        """)

        # Seed default budgets if empty
        cursor.execute("SELECT COUNT(*) FROM category_budgets;")
        if cursor.fetchone()[0] == 0:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            default_budgets = [
                (Category.DINING_SELF, 8000.0, 80.0, now_str),
                (Category.DINING_GIRLFRIEND, 10000.0, 80.0, now_str),
                (Category.DINING_FAMILY, 6000.0, 80.0, now_str),
                (Category.DINING, 3000.0, 80.0, now_str),
                (Category.TRANSPORT, 2500.0, 80.0, now_str),
                (Category.SHOPPING, 5000.0, 80.0, now_str),
                (Category.ENTERTAINMENT, 3000.0, 80.0, now_str),
                (Category.BILLS, 4000.0, 80.0, now_str),
                (Category.HEALTH, 2000.0, 80.0, now_str),
                (Category.EDUCATION, 1500.0, 80.0, now_str),
                (Category.OTHER, 2000.0, 80.0, now_str),
            ]
            cursor.executemany("""
                INSERT OR IGNORE INTO category_budgets (category, monthly_budget, warning_percent, updated_at)
                VALUES (?, ?, ?, ?);
            """, default_budgets)

        # Migration: update legacy '飲食' to '飲食 (自己吃)'
        cursor.execute("UPDATE transactions SET category = ? WHERE category = '飲食';", (Category.DINING_SELF,))
        cursor.execute("UPDATE category_rules SET category = ? WHERE category = '飲食';", (Category.DINING_SELF,))

        conn.commit()
    deduplicate_existing_transactions()

GENERIC_MERCHANTS = {
    "餐飲", "餐飲消費", "一般特店", "特約商店", "特店", "國外交易", "國外消費",
    "網路購物", "網路消費", "一般消費", "其他", "日常花費", "海外交易",
    "國泰世華", "玉山銀行", "中國信託", "台新銀行", "台北富邦", "富邦銀行", "國泰特店消費"
}

def _clean_merchant(m: Optional[str]) -> str:
    if not m:
        return ""
    return re.sub(r"[^\w\u4e00-\u9fff]", "", m).lower()

def _parse_time_seconds(t: Optional[str]) -> Optional[int]:
    if not t:
        return None
    try:
        parts = t.strip().split(":")
        if len(parts) >= 2:
            h = int(parts[0])
            m = int(parts[1])
            s = int(parts[2]) if len(parts) > 2 else 0
            return h * 3600 + m * 60 + s
    except Exception:
        return None
    return None

def _is_duplicate_record(
    c_merchant: str,
    n_merchant: str,
    c_time: Optional[str],
    n_time: Optional[str],
    c_card: Optional[str],
    n_card: Optional[str]
) -> bool:
    # 1. Card check: If both records have card_last4 and they don't match, NOT duplicate
    if c_card and n_card and c_card.strip() != n_card.strip():
        return False

    c_sec = _parse_time_seconds(c_time)
    n_sec = _parse_time_seconds(n_time)
    diff_sec = abs(c_sec - n_sec) if (c_sec is not None and n_sec is not None) else None

    # If both have timestamps and they are more than 30 minutes apart,
    # they are distinct transactions (e.g. morning and afternoon swipe of same amount)
    if diff_sec is not None and diff_sec > 1800:
        return False

    norm1 = _clean_merchant(c_merchant)
    norm2 = _clean_merchant(n_merchant)

    # If both have empty merchant name
    if not norm1 and not norm2:
        return True

    # Exact merchant match (case-insensitive & stripped)
    if norm1 == norm2:
        return True

    # Substring match (e.g. JALAN vs JALAN NET, Uber vs Uber Eats)
    if (norm1 in norm2 or norm2 in norm1) and min(len(norm1), len(norm2)) >= 2:
        return True

    # Generic merchant match (e.g. "餐飲", "一般特店" vs actual store name)
    if norm1 in GENERIC_MERCHANTS or norm2 in GENERIC_MERCHANTS:
        if diff_sec is None or diff_sec <= 900:
            return True

    # Very close authorization time (within 5 minutes) on same card and same day
    if diff_sec is not None and diff_sec <= 300:
        return True

    return False

def is_duplicate(
    email_id: Optional[str],
    trans_date: str,
    amount: float,
    merchant: str,
    card_last4: Optional[str] = None,
    trans_time: Optional[str] = None,
    category: Optional[str] = None
) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        if email_id:
            cursor.execute("SELECT 1 FROM transactions WHERE email_id = ? LIMIT 1;", (email_id,))
            if cursor.fetchone():
                return True

        # Check candidate transactions with same date and amount
        cursor.execute("""
            SELECT id, trans_date, trans_time, amount, merchant, category, card_last4, note, email_id
            FROM transactions
            WHERE trans_date = ? AND ABS(amount - ?) < 0.01;
        """, (trans_date, amount))
        candidates = [dict(row) for row in cursor.fetchall()]

        if not candidates:
            return False

        n_clean = _clean_merchant(merchant)

        for c in candidates:
            if _is_duplicate_record(c["merchant"], merchant, c["trans_time"], trans_time, c["card_last4"], card_last4):
                # Found duplicate! Enrich candidate if incoming has more detailed info
                update_fields = {}
                c_clean = _clean_merchant(c["merchant"])

                c_generic = c_clean in GENERIC_MERCHANTS or len(c_clean) <= 2
                n_generic = n_clean in GENERIC_MERCHANTS or len(n_clean) <= 2

                if c_generic and not n_generic:
                    update_fields["merchant"] = merchant.strip()
                    if category and category != Category.OTHER:
                        update_fields["category"] = category
                elif not c_generic and not n_generic:
                    if (c_clean in n_clean) and len(merchant.strip()) > len(c["merchant"].strip()):
                        update_fields["merchant"] = merchant.strip()
                        if category and category != Category.OTHER:
                            update_fields["category"] = category

                # Accurate time with seconds
                if trans_time and c["trans_time"] and c["trans_time"].endswith(":00") and not trans_time.endswith(":00"):
                    update_fields["trans_time"] = trans_time

                # Card last 4
                if not c["card_last4"] and card_last4:
                    update_fields["card_last4"] = card_last4

                if update_fields:
                    set_clauses = [f"{k} = ?" for k in update_fields.keys()]
                    vals = list(update_fields.values()) + [c["id"]]
                    cursor.execute(f"UPDATE transactions SET {', '.join(set_clauses)} WHERE id = ?;", vals)
                    conn.commit()

                return True

        return False

def deduplicate_existing_transactions() -> int:
    """
    Scans the database for duplicate transactions (e.g. instant swipe notice + daily digest notice),
    merges the most detailed info into one record, and removes the redundant record.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions ORDER BY id ASC;")
        rows = [dict(r) for r in cursor.fetchall()]

        removed_ids = set()
        for i in range(len(rows)):
            if rows[i]["id"] in removed_ids:
                continue
            r1 = rows[i]
            for j in range(i + 1, len(rows)):
                if rows[j]["id"] in removed_ids:
                    continue
                r2 = rows[j]

                # Check date and amount
                if r1["trans_date"] != r2["trans_date"]:
                    continue
                if abs(r1["amount"] - r2["amount"]) >= 0.01:
                    continue

                if _is_duplicate_record(r1["merchant"], r2["merchant"], r1["trans_time"], r2["trans_time"], r1["card_last4"], r2["card_last4"]):
                    # Redundant pair found! Keep r1, merge richer details from r2
                    better_merchant = r1["merchant"]
                    m1_norm = _clean_merchant(r1["merchant"])
                    m2_norm = _clean_merchant(r2["merchant"])

                    m1_gen = m1_norm in GENERIC_MERCHANTS or len(m1_norm) <= 2
                    m2_gen = m2_norm in GENERIC_MERCHANTS or len(m2_norm) <= 2

                    if m1_gen and not m2_gen:
                        better_merchant = r2["merchant"]
                    elif not m1_gen and not m2_gen and len(r2["merchant"]) > len(r1["merchant"]) and (m1_norm in m2_norm):
                        better_merchant = r2["merchant"]

                    better_category = r1["category"]
                    if r1["category"] in (Category.OTHER, None) and r2["category"] not in (Category.OTHER, None):
                        better_category = r2["category"]

                    better_time = r1["trans_time"]
                    if r2["trans_time"] and (not r1["trans_time"] or (r1["trans_time"].endswith(":00") and not r2["trans_time"].endswith(":00"))):
                        better_time = r2["trans_time"]

                    better_card = r1["card_last4"] or r2["card_last4"]

                    cursor.execute("""
                        UPDATE transactions
                        SET merchant = ?, category = ?, trans_time = ?, card_last4 = ?
                        WHERE id = ?;
                    """, (better_merchant, better_category, better_time, better_card, r1["id"]))

                    cursor.execute("DELETE FROM transactions WHERE id = ?;", (r2["id"],))
                    removed_ids.add(r2["id"])

        conn.commit()
        return len(removed_ids)

def add_transaction(tx: Transaction) -> Optional[int]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (
                trans_date, trans_time, amount, currency, merchant, category,
                source, bank, card_last4, note, email_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            tx.trans_date, tx.trans_time, tx.amount, tx.currency, tx.merchant,
            tx.category, tx.source, tx.bank, tx.card_last4, tx.note, tx.email_id, tx.created_at
        ))
        conn.commit()
        return cursor.lastrowid

def get_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 200,
    offset: int = 0
) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        conditions = []
        params = []

        if start_date:
            conditions.append("trans_date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("trans_date <= ?")
            params.append(end_date)
        if category:
            conditions.append("category = ?")
            params.append(category)
        if source:
            conditions.append("source = ?")
            params.append(source)
        if keyword:
            conditions.append("(merchant LIKE ? OR note LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        query = f"SELECT * FROM transactions {where_clause} ORDER BY trans_date DESC, trans_time DESC, id DESC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def update_transaction(tx_id: int, updates: Dict[str, Any]) -> bool:
    allowed = {"trans_date", "trans_time", "amount", "merchant", "category", "note", "source", "bank", "card_last4"}
    valid_updates = {k: v for k, v in updates.items() if k in allowed}
    if not valid_updates:
        return False
    set_clause = ", ".join([f"{k} = ?" for k in valid_updates.keys()])
    params = list(valid_updates.values()) + [tx_id]

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM transactions WHERE id = ?;", (tx_id,))
        if not cursor.fetchone():
            return False
        cursor.execute(f"UPDATE transactions SET {set_clause} WHERE id = ?;", params)
        conn.commit()
        return True

def delete_transaction(tx_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions WHERE id = ?;", (tx_id,))
        conn.commit()
        return cursor.rowcount > 0

def clear_demo_transactions() -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM transactions 
            WHERE (source = 'gmail' AND (email_id IS NULL OR email_id = ''))
               OR note LIKE '%示範%'
               OR note LIKE '%測試%'
               OR note LIKE '%早餐咖啡拿鐵%'
               OR note LIKE '%午餐現金支付%'
               OR note LIKE '%拜訪客戶計程車%'
               OR note LIKE '%晚餐食材採買%'
               OR note LIKE '%涼麵加無糖綠%'
               OR note LIKE '%每月高級會員方案%'
               OR note LIKE '%台北至左營商務車廂%'
               OR note LIKE '%防風外套與發熱衣%';
        """)
        conn.commit()
        return cursor.rowcount

def clear_all_transactions() -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions;")
        conn.commit()
        return cursor.rowcount

def get_day_stats(date_str: str) -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions WHERE trans_date = ? ORDER BY trans_time DESC;", (date_str,))
        items = [dict(row) for row in cursor.fetchall()]

        total_amount = sum(item["amount"] for item in items)
        credit_card_items = [i for i in items if i["source"] == "gmail"]
        manual_items = [i for i in items if i["source"] == "manual"]

        by_category: Dict[str, float] = {}
        for item in items:
            cat = item["category"] or Category.OTHER
            by_category[cat] = by_category.get(cat, 0.0) + item["amount"]

        return {
            "date": date_str,
            "total_amount": round(total_amount, 2),
            "total_count": len(items),
            "credit_card_amount": round(sum(i["amount"] for i in credit_card_items), 2),
            "credit_card_count": len(credit_card_items),
            "manual_amount": round(sum(i["amount"] for i in manual_items), 2),
            "manual_count": len(manual_items),
            "by_category": by_category,
            "items": items
        }

def get_month_stats(year_month: str) -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM transactions
            WHERE trans_date LIKE ?
            ORDER BY trans_date ASC, trans_time ASC;
        """, (f"{year_month}%",))
        items = [dict(row) for row in cursor.fetchall()]

        total_amount = sum(item["amount"] for item in items)
        by_category: Dict[str, float] = {}
        by_date: Dict[str, float] = {}

        for item in items:
            cat = item["category"] or Category.OTHER
            by_category[cat] = by_category.get(cat, 0.0) + item["amount"]
            d = item["trans_date"]
            by_date[d] = by_date.get(d, 0.0) + item["amount"]

        return {
            "year_month": year_month,
            "total_amount": round(total_amount, 2),
            "total_count": len(items),
            "by_category": by_category,
            "by_date": by_date
        }

def get_rules() -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, keyword, category FROM category_rules ORDER BY id DESC;")
        return [dict(row) for row in cursor.fetchall()]

def add_rule(keyword: str, category: str) -> bool:
    keyword = keyword.strip().lower()
    if not keyword:
        return False
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO category_rules (keyword, category) VALUES (?, ?);", (keyword, category))
        conn.commit()
        return True

def delete_rule(rule_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM category_rules WHERE id = ?;", (rule_id,))
        conn.commit()
        return cursor.rowcount > 0

# --- Budget & Watermark Management ---

def get_category_budgets() -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM category_budgets ORDER BY id ASC;")
        return [dict(row) for row in cursor.fetchall()]

def save_category_budget(category: str, monthly_budget: float, warning_percent: float = 80.0) -> bool:
    category = category.strip()
    if not category:
        return False
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO category_budgets (category, monthly_budget, warning_percent, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(category) DO UPDATE SET
                monthly_budget = excluded.monthly_budget,
                warning_percent = excluded.warning_percent,
                updated_at = excluded.updated_at;
        """, (category, float(monthly_budget), float(warning_percent), now_str))
        conn.commit()
        return True

def get_budgets_status(year_month: Optional[str] = None) -> List[Dict[str, Any]]:
    if not year_month:
        year_month = datetime.now().strftime("%Y-%m")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT category, SUM(amount) as total_spent
            FROM transactions
            WHERE trans_date LIKE ?
            GROUP BY category;
        """, (f"{year_month}%",))
        spent_map = {row["category"]: row["total_spent"] for row in cursor.fetchall()}

        cursor.execute("SELECT * FROM category_budgets ORDER BY id ASC;")
        budget_rows = [dict(r) for r in cursor.fetchall()]
        existing_budgets = {b["category"]: b for b in budget_rows}

        results = []
        for cat in Category.ALL:
            b = existing_budgets.get(cat, {})
            monthly_budget = float(b.get("monthly_budget", 0.0))
            warning_percent = float(b.get("warning_percent", 80.0))
            spent = round(float(spent_map.get(cat, 0.0)), 2)
            remaining = round(monthly_budget - spent, 2)
            percentage = round((spent / monthly_budget) * 100, 1) if monthly_budget > 0 else 0.0

            if monthly_budget <= 0:
                status = "unbudgeted"
            elif spent >= monthly_budget:
                status = "exceeded"
            elif percentage >= warning_percent:
                status = "warning"
            else:
                status = "normal"

            results.append({
                "category": cat,
                "monthly_budget": monthly_budget,
                "warning_percent": warning_percent,
                "spent_amount": spent,
                "remaining_amount": remaining,
                "percentage": percentage,
                "status": status,
                "year_month": year_month
            })
        return results
