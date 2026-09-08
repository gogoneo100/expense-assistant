import unittest
import os
from pathlib import Path
import app.database as db_module
from app.models import Transaction, Category
from app.database import (
    is_duplicate,
    add_transaction,
    get_transactions,
    deduplicate_existing_transactions,
    clear_all_transactions
)

TEST_DB_PATH = db_module.DATA_DIR / 'test_dedup.db'

class TestDeduplication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orig_db_path = db_module.DB_PATH
        db_module.DB_PATH = TEST_DB_PATH
        db_module.init_db()

    @classmethod
    def tearDownClass(cls):
        db_module.DB_PATH = cls.orig_db_path
        if TEST_DB_PATH.exists():
            try: os.remove(TEST_DB_PATH)
            except Exception: pass

    def setUp(self):
        clear_all_transactions()

    def tearDown(self):
        clear_all_transactions()

    def test_instant_then_digest_deduplication(self):
        tx1 = Transaction(
            trans_date='2026-09-03',
            trans_time='23:21:04',
            amount=5258.0,
            currency='TWD',
            merchant='JALAN NET',
            category='交通',
            source='gmail',
            bank='國泰世華',
            card_last4='8092',
            email_id='<msg_instant_1>'
        )
        add_transaction(tx1)

        is_dup = is_duplicate(
            email_id='<msg_digest_1>',
            trans_date='2026-09-03',
            amount=5258.0,
            merchant='JALAN',
            card_last4='8092',
            trans_time='23:21:00',
            category='交通'
        )
        self.assertTrue(is_dup)

        txs = get_transactions()
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0]['merchant'], 'JALAN NET')
        self.assertEqual(txs[0]['trans_time'], '23:21:04')

    def test_digest_then_instant_deduplication_and_enrichment(self):
        tx1 = Transaction(
            trans_date='2026-09-03',
            trans_time='23:21:00',
            amount=5258.0,
            currency='TWD',
            merchant='JALAN',
            category='交通',
            source='gmail',
            bank='國泰世華',
            card_last4='8092',
            email_id='<msg_digest_1>'
        )
        add_transaction(tx1)

        is_dup = is_duplicate(
            email_id='<msg_instant_1>',
            trans_date='2026-09-03',
            amount=5258.0,
            merchant='JALAN NET',
            card_last4='8092',
            trans_time='23:21:04',
            category='交通'
        )
        self.assertTrue(is_dup)

        txs = get_transactions()
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0]['merchant'], 'JALAN NET')
        self.assertEqual(txs[0]['trans_time'], '23:21:04')

    def test_generic_merchant_enrichment(self):
        tx1 = Transaction(
            trans_date='2026-09-05',
            trans_time='16:37:00',
            amount=326.0,
            merchant='餐飲',
            category='飲食',
            source='gmail',
            bank='國泰世華',
            card_last4='8092',
            email_id='<msg_digest_2>'
        )
        add_transaction(tx1)

        is_dup = is_duplicate(
            email_id='<msg_instant_2>',
            trans_date='2026-09-05',
            amount=326.0,
            merchant='鼎泰豐 信義店',
            card_last4='8092',
            trans_time='16:37:12',
            category='飲食'
        )
        self.assertTrue(is_dup)

        txs = get_transactions()
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0]['merchant'], '鼎泰豐 信義店')
        self.assertEqual(txs[0]['trans_time'], '16:37:12')

    def test_same_amount_different_times_not_duplicate(self):
        tx1 = Transaction(
            trans_date='2026-09-06',
            trans_time='08:30:00',
            amount=150.0,
            merchant='星巴克',
            category='飲食',
            source='gmail',
            bank='國泰世華',
            card_last4='8092',
            email_id='<msg_coffee_1>'
        )
        add_transaction(tx1)

        is_dup = is_duplicate(
            email_id='<msg_coffee_2>',
            trans_date='2026-09-06',
            amount=150.0,
            merchant='星巴克',
            card_last4='8092',
            trans_time='15:30:00',
            category='飲食'
        )
        self.assertFalse(is_dup)

    def test_same_amount_different_cards_not_duplicate(self):
        tx1 = Transaction(
            trans_date='2026-09-06',
            trans_time='12:00:00',
            amount=500.0,
            merchant='全聯福利中心',
            category='購物',
            card_last4='8092',
            email_id='<card_a>'
        )
        add_transaction(tx1)

        is_dup = is_duplicate(
            email_id='<card_b>',
            trans_date='2026-09-06',
            amount=500.0,
            merchant='全聯福利中心',
            card_last4='1688',
            trans_time='12:00:00',
            category='購物'
        )
        self.assertFalse(is_dup)

    def test_deduplicate_existing_transactions(self):
        tx1 = Transaction(
            trans_date='2026-09-03',
            trans_time='23:21:00',
            amount=5258.0,
            merchant='JALAN',
            category='交通',
            card_last4='8092'
        )
        tx2 = Transaction(
            trans_date='2026-09-03',
            trans_time='23:21:04',
            amount=5258.0,
            merchant='JALAN NET',
            category='交通',
            card_last4='8092'
        )
        add_transaction(tx1)
        add_transaction(tx2)

        self.assertEqual(len(get_transactions()), 2)
        cleaned = deduplicate_existing_transactions()
        self.assertEqual(cleaned, 1)

        remaining = get_transactions()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]['merchant'], 'JALAN NET')
        self.assertEqual(remaining[0]['trans_time'], '23:21:04')

if __name__ == '__main__':
    unittest.main()
