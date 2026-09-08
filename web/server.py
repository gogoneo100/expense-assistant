import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.config import config, CONFIG_FILE
from app.database import (
    init_db,
    add_transaction,
    get_transactions,
    update_transaction,
    delete_transaction,
    get_day_stats,
    get_month_stats,
    get_rules,
    add_rule,
    delete_rule,
    clear_demo_transactions,
    clear_all_transactions,
    deduplicate_existing_transactions,
    get_category_budgets,
    save_category_budget,
    get_budgets_status
)
from app.models import Transaction, Category
from app.classifier import parse_manual_input, classify_merchant
from app.mail_service import sync_gmail, seed_demo_transactions
from app.reminder_service import trigger_daily_reminder, generate_daily_digest

app = FastAPI(title="智能消費管家 API", version="1.0.0")

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/")
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse({"message": "Expense Assistant API is running."})

# --- Stats Endpoints ---

@app.get("/api/stats/today")
def get_today_summary(date: Optional[str] = None):
    target_date = date or datetime.now().strftime("%Y-%m-%d")
    return get_day_stats(target_date)

@app.get("/api/stats/month")
def get_monthly_summary(year_month: Optional[str] = None):
    target_ym = year_month or datetime.now().strftime("%Y-%m")
    return get_month_stats(target_ym)

# --- Transactions Endpoints ---

class CreateTransactionRequest(BaseModel):
    # If text is provided, we parse via natural language
    text: Optional[str] = None
    # Otherwise structured fields:
    trans_date: Optional[str] = None
    trans_time: Optional[str] = None
    amount: Optional[float] = None
    merchant: Optional[str] = None
    category: Optional[str] = None
    note: Optional[str] = None
    source: str = "manual"

@app.get("/api/transactions")
def list_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    items = get_transactions(
        start_date=start_date,
        end_date=end_date,
        category=category,
        source=source,
        keyword=keyword,
        limit=limit,
        offset=offset
    )
    return {"transactions": items, "count": len(items)}

@app.post("/api/transactions")
def create_transaction(req: CreateTransactionRequest):
    now = datetime.now()
    if req.text and req.text.strip():
        amt, merchant, cat, note = parse_manual_input(req.text)
        if amt <= 0:
            raise HTTPException(status_code=400, detail="無法自文字中解析出金額，請輸入如「午餐 120」")
        tx = Transaction(
            trans_date=req.trans_date or now.strftime("%Y-%m-%d"),
            trans_time=req.trans_time or now.strftime("%H:%M:%S"),
            amount=amt,
            merchant=merchant,
            category=cat,
            note=note or "快速申報",
            source="manual"
        )
    else:
        if req.amount is None or req.amount <= 0:
            raise HTTPException(status_code=400, detail="金額必須大於 0")
        merchant = req.merchant.strip() if req.merchant else "日常花費"
        category = req.category or classify_merchant(merchant, req.note or "")
        tx = Transaction(
            trans_date=req.trans_date or now.strftime("%Y-%m-%d"),
            trans_time=req.trans_time or now.strftime("%H:%M:%S"),
            amount=req.amount,
            merchant=merchant,
            category=category,
            note=req.note or "",
            source=req.source or "manual"
        )

    new_id = add_transaction(tx)
    return {"success": True, "id": new_id, "transaction": tx.to_dict()}

class UpdateTransactionRequest(BaseModel):
    category: Optional[str] = None
    merchant: Optional[str] = None
    amount: Optional[float] = None
    note: Optional[str] = None
    trans_date: Optional[str] = None

@app.put("/api/transactions/{tx_id}")
def edit_transaction(tx_id: int, req: UpdateTransactionRequest):
    dump = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    data = {k: v for k, v in dump.items() if v is not None}
    success = update_transaction(tx_id, data)
    if not success:
        raise HTTPException(status_code=404, detail="交易不存在")
    return {"success": True}

@app.delete("/api/transactions/{tx_id}")
def remove_transaction(tx_id: int):
    success = delete_transaction(tx_id)
    if not success:
        raise HTTPException(status_code=404, detail="交易不存在")
    return {"success": True}

# --- Categorization Rules Endpoints ---

@app.get("/api/rules")
def list_rules():
    return {"rules": get_rules(), "categories": Category.ALL}

class CreateRuleRequest(BaseModel):
    keyword: str
    category: str

@app.post("/api/rules")
def create_rule(req: CreateRuleRequest):
    if not req.keyword.strip():
        raise HTTPException(status_code=400, detail="關鍵字不可為空")
    add_rule(req.keyword, req.category)
    return {"success": True}

@app.delete("/api/rules/{rule_id}")
def remove_rule(rule_id: int):
    success = delete_rule(rule_id)
    return {"success": success}

# --- Budget & Watermark Endpoints ---

@app.get("/api/budgets")
def list_budgets(month: Optional[str] = None):
    ym = month or datetime.now().strftime("%Y-%m")
    status_list = get_budgets_status(ym)
    return {"year_month": ym, "budgets": status_list, "categories": Category.ALL}

class SetBudgetRequest(BaseModel):
    category: str
    monthly_budget: float
    warning_percent: Optional[float] = 80.0

@app.post("/api/budgets")
def set_budget(req: SetBudgetRequest):
    if not req.category.strip():
        raise HTTPException(status_code=400, detail="類別不可為空")
    if req.monthly_budget < 0:
        raise HTTPException(status_code=400, detail="預算金額不可為負數")
    success = save_category_budget(req.category, req.monthly_budget, req.warning_percent or 80.0)
    return {"success": success}

@app.post("/api/budgets/batch")
def set_budgets_batch(req: Dict[str, Any]):
    budgets = req.get("budgets", [])
    for b in budgets:
        cat = str(b.get("category", "")).strip()
        mb = float(b.get("monthly_budget", 0))
        wp = float(b.get("warning_percent", 80.0))
        if cat and mb >= 0:
            save_category_budget(cat, mb, wp)
    return {"success": True}

# --- Sync & Reminder Endpoints ---

class SyncRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    lookback_days: Optional[int] = None

@app.post("/api/sync")
def trigger_sync(req: Optional[SyncRequest] = None):
    start = req.start_date if req else None
    end = req.end_date if req else None
    days = req.lookback_days if req else None
    result = sync_gmail(start_date=start, end_date=end, lookback_days=days)
    return result

@app.post("/api/seed-demo")
def seed_demo():
    count = seed_demo_transactions()
    return {"success": True, "added": count}

@app.post("/api/clear-demo")
def clear_demo():
    deleted = clear_demo_transactions()
    return {"success": True, "deleted": deleted}

@app.post("/api/clear-all")
def clear_all():
    deleted = clear_all_transactions()
    return {"success": True, "deleted": deleted}

@app.post("/api/deduplicate")
def clean_duplicates():
    removed = deduplicate_existing_transactions()
    return {"success": True, "removed_count": removed}

@app.post("/api/remind")
def manual_remind(date: Optional[str] = None):
    res = trigger_daily_reminder(date or datetime.now().strftime("%Y-%m-%d"))
    return res

# --- Configuration Endpoints ---

@app.get("/api/config")
def get_current_config():
    # Return config with masked password
    masked_pw = ("*" * len(config.gmail_app_password)) if config.gmail_app_password else ""
    return {
        "gmail_user": config.gmail_user,
        "gmail_app_password": masked_pw,
        "is_gmail_configured": bool(config.gmail_user and config.gmail_app_password),
        "reminder_time": config.reminder_time,
        "reminder_enabled": config.reminder_enabled,
        "telegram_enabled": config.telegram_enabled,
        "telegram_bot_token": ("*" * 10) if config.telegram_bot_token else "",
        "telegram_chat_id": config.telegram_chat_id,
        "is_telegram_configured": bool(config.telegram_bot_token and config.telegram_chat_id),
        "server_port": config.server_port,
        "currency": config.currency
    }

class SaveConfigRequest(BaseModel):
    gmail_user: Optional[str] = None
    gmail_app_password: Optional[str] = None
    reminder_time: Optional[str] = None
    reminder_enabled: Optional[bool] = None
    telegram_enabled: Optional[bool] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

@app.post("/api/config")
def save_current_config(req: SaveConfigRequest):
    if req.gmail_user is not None:
        config.gmail_user = req.gmail_user.strip()
    if req.gmail_app_password is not None and req.gmail_app_password != "" and not req.gmail_app_password.startswith("*"):
        config.gmail_app_password = req.gmail_app_password.strip()
    if req.reminder_time is not None:
        config.reminder_time = req.reminder_time.strip()
    if req.reminder_enabled is not None:
        config.reminder_enabled = req.reminder_enabled
    if req.telegram_enabled is not None:
        config.telegram_enabled = req.telegram_enabled
    if req.telegram_bot_token is not None and not req.telegram_bot_token.startswith("*"):
        config.telegram_bot_token = req.telegram_bot_token.strip()
    if req.telegram_chat_id is not None:
        config.telegram_chat_id = req.telegram_chat_id.strip()

    config.save()
    return {"success": True, "message": "設定已儲存"}
