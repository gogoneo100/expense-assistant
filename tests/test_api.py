import unittest
import os
from pathlib import Path
from fastapi.testclient import TestClient

import app.database as db_module
from web.server import app

TEST_DB_PATH = db_module.DATA_DIR / "test_expenses.db"

class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Point to dedicated test DB
        cls.orig_db_path = db_module.DB_PATH
        db_module.DB_PATH = TEST_DB_PATH
        if TEST_DB_PATH.exists():
            try: os.remove(TEST_DB_PATH)
            except Exception: pass
        db_module.init_db()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        db_module.DB_PATH = cls.orig_db_path
        if TEST_DB_PATH.exists():
            try: os.remove(TEST_DB_PATH)
            except Exception: pass

    def test_create_transaction_natural(self):
        res = self.client.post("/api/transactions", json={"text": "午餐便當 110"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["transaction"]["amount"], 110.0)
        self.assertEqual(data["transaction"]["category"], db_module.Category.DINING_SELF)

    def test_create_transaction_structured(self):
        res = self.client.post("/api/transactions", json={
            "amount": 250.0,
            "merchant": "計程車返家",
            "category": "交通",
            "note": "下雨天搭車"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        tx_id = data["id"]

        # Verify in transactions list
        res_list = self.client.get("/api/transactions?category=交通")
        self.assertEqual(res_list.status_code, 200)
        items = res_list.json()["transactions"]
        self.assertTrue(any(i["id"] == tx_id for i in items))

    def test_stats_today(self):
        res = self.client.get("/api/stats/today")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_amount", data)
        self.assertIn("credit_card_amount", data)
        self.assertIn("manual_amount", data)
        self.assertIn("by_category", data)

    def test_remind_endpoint(self):
        res = self.client.post("/api/remind")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn("summary_text", data)
        self.assertIn("【消費每日彙整通知】", data["summary_text"])

    from unittest.mock import patch

    @patch("web.server.sync_gmail")
    def test_sync_endpoint_with_range(self, mock_sync):
        mock_sync.return_value = {"success": True, "synced_count": 3, "skipped_count": 0}
        res = self.client.post("/api/sync", json={
            "start_date": "2026-08-01",
            "end_date": "2026-09-08"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["synced_count"], 3)
        mock_sync.assert_called_once_with(start_date="2026-08-01", end_date="2026-09-08", lookback_days=None)

    def test_budgets_endpoints(self):
        # 1. Get budgets
        res = self.client.get("/api/budgets")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("budgets", data)
        self.assertTrue(len(data["budgets"]) > 0)

        # 2. Update budget
        res_set = self.client.post("/api/budgets", json={
            "category": "飲食 (和女友吃)",
            "monthly_budget": 12000.0,
            "warning_percent": 85.0
        })
        self.assertEqual(res_set.status_code, 200)
        self.assertTrue(res_set.json()["success"])

        # 3. Verify updated budget
        res_verify = self.client.get("/api/budgets")
        b_list = res_verify.json()["budgets"]
        gf_budget = next((b for b in b_list if b["category"] == "飲食 (和女友吃)"), None)
        self.assertIsNotNone(gf_budget)
        self.assertEqual(gf_budget["monthly_budget"], 12000.0)
        self.assertEqual(gf_budget["warning_percent"], 85.0)

        # 4. Batch update budgets
        res_batch = self.client.post("/api/budgets/batch", json={
            "budgets": [
                {"category": "飲食 (自己吃)", "monthly_budget": 9500.0, "warning_percent": 80.0},
                {"category": "飲食 (和家人吃)", "monthly_budget": 7500.0, "warning_percent": 80.0}
            ]
        })
        self.assertEqual(res_batch.status_code, 200)
        self.assertTrue(res_batch.json()["success"])

    def test_edit_transaction_custom_merchant(self):
        # Create a generic transaction
        res = self.client.post("/api/transactions", json={
            "amount": 326.0,
            "merchant": "餐飲",
            "category": "飲食 (自己吃)",
            "note": "Gmail 自動匯入"
        })
        self.assertEqual(res.status_code, 200)
        tx_id = res.json()["id"]

        # Edit merchant to specific restaurant and change companion category
        res_edit = self.client.put(f"/api/transactions/{tx_id}", json={
            "merchant": "麥當勞台北館前店",
            "category": "飲食 (和女友吃)",
            "note": "跟女友約會晚餐外帶"
        })
        self.assertEqual(res_edit.status_code, 200)
        self.assertTrue(res_edit.json()["success"])

        # Verify
        res_check = self.client.get("/api/transactions")
        items = res_check.json()["transactions"]
        matched = next((i for i in items if i["id"] == tx_id), None)
        self.assertIsNotNone(matched)
        self.assertEqual(matched["merchant"], "麥當勞台北館前店")
        self.assertEqual(matched["category"], "飲食 (和女友吃)")
        self.assertEqual(matched["note"], "跟女友約會晚餐外帶")
        self.assertEqual(matched["amount"], 326.0)

if __name__ == "__main__":
    unittest.main()
