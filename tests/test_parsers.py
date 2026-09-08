import unittest
from datetime import datetime
from app.parsers.banks import parse_email
from app.parsers.base import ParsedTransaction

class TestBankParsers(unittest.TestCase):
    def test_cathay_parser(self):
        subject = "國泰世華銀行 - 信用卡消費即時通知"
        sender = "service@cathaybk.com.tw"
        body = """
        親愛的身為貴賓您好：
        您於 2026/09/08 14:30 使用國泰世華信用卡 (末四碼 1688) 刷卡消費 新台幣 350 元。
        特約商店：星巴克信義門市
        感謝您的愛護與支持。
        """
        results = parse_email(subject, sender, body, datetime.now())
        self.assertTrue(len(results) > 0)
        parsed = results[0]
        self.assertEqual(parsed.amount, 350.0)
        self.assertEqual(parsed.card_last4, "1688")
        self.assertIn("星巴克", parsed.merchant)
        self.assertEqual(parsed.bank, "國泰世華")

    def test_cathay_digest_multi_transaction(self):
        subject = "國泰世華銀行消費彙整通知（請勿直接回覆）"
        sender = "service@cathaybk.com.tw"
        body = """
        卡號後4碼： 8092
        卡別 行動卡號後4碼 授權日期 授權時間 消費地區
        正卡 6893 2026/09/05 16:37 TW
        消費金額 商店名稱 消費類別 備註
        NT$326 餐飲 註一

        卡別 行動卡號後4碼 授權日期 授權時間 消費地區
        正卡 2026/09/05 19:04 SG
        消費金額 商店名稱 消費類別 備註
        NT$2,190 HBOMax help.hbomax.com 電信服務
        """
        results = parse_email(subject, sender, body, datetime.now())
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].amount, 326.0)
        self.assertEqual(results[0].card_last4, "8092")
        self.assertEqual(results[1].amount, 2190.0)
        self.assertEqual(results[1].merchant, "HBOMax")

    def test_ctbc_parser(self):
        subject = "中國信託信用卡即時消費通知"
        sender = "notice@ctbcbank.com"
        body = """
        您於 2026/09/08 12:15 刷卡成功：
        卡號末四碼：8821
        交易金額：NT$ 1,200
        交易特店：Uber Eats
        """
        results = parse_email(subject, sender, body, datetime.now())
        self.assertTrue(len(results) > 0)
        parsed = results[0]
        self.assertEqual(parsed.amount, 1200.0)
        self.assertEqual(parsed.card_last4, "8821")
        self.assertIn("Uber Eats", parsed.merchant)
        self.assertEqual(parsed.bank, "中國信託")

    def test_esun_parser(self):
        subject = "玉山信用卡消費通知"
        sender = "esun@esunbank.com.tw"
        body = """
        敬愛的顧客您好，您的玉山信用卡(卡號末四碼: 3390)
        於 2026/09/08 18:20 消費新臺幣 460 元整。
        特店名稱：全聯福利中心
        """
        results = parse_email(subject, sender, body, datetime.now())
        self.assertTrue(len(results) > 0)
        parsed = results[0]
        self.assertEqual(parsed.amount, 460.0)
        self.assertEqual(parsed.card_last4, "3390")
        self.assertIn("全聯", parsed.merchant)

    def test_universal_fallback_parser(self):
        subject = "【星展銀行】信用卡授權確認通知"
        sender = "alert@dbs.com"
        body = """
        親愛的客戶，您尾號 9988 的信用卡於 2026/09/08 10:00 授權扣款成功。
        金額：TWD 890 元
        特約商店：台灣大車隊
        """
        results = parse_email(subject, sender, body, datetime.now())
        self.assertTrue(len(results) > 0)
        parsed = results[0]
        self.assertEqual(parsed.amount, 890.0)
        self.assertEqual(parsed.card_last4, "9988")
        self.assertIn("台灣大車隊", parsed.merchant)
        self.assertEqual(parsed.bank, "星展銀行")

    def test_ignore_statements(self):
        subject = "國泰世華銀行信用卡2026年9月電子帳單"
        sender = "bill@cathaybk.com.tw"
        body = "本期應繳總金額 3,000 元"
        results = parse_email(subject, sender, body, datetime.now())
        self.assertEqual(len(results), 0)

    def test_ignore_promotional_emails(self):
        # Loan promo
        subj1 = "月付金想輕一點？泰幸福信貸協助您彈性規劃"
        sender = "service@cathaybk.com.tw"
        body1 = "首期超低手續費 30 元，輕鬆申辦"
        results1 = parse_email(subj1, sender, body1, datetime.now())
        self.assertEqual(len(results1), 0)

        # Installment promo
        subj2 = "一起出發，收藏今夏美好回憶!刷卡分期，即刻出發!"
        body2 = "指定旅行社滿額分期享回饋 150 元"
        results2 = parse_email(subj2, sender, body2, datetime.now())
        self.assertEqual(len(results2), 0)

    def test_cathay_online_swipe(self):
        subject = "【國泰世華銀行】網路消費通知 (請勿直接回覆)"
        sender = "service@cathaybk.com.tw"
        body = """
        網路消費通知
        【國泰世華刷卡通知】
        09月03日23:21
        正卡卡號末四碼
        8092
        於JALAN NET交易約
        NT$5258
        """
        results = parse_email(subject, sender, body, datetime.now())
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].amount, 5258.0)
        self.assertEqual(results[0].merchant, "JALAN NET")
        self.assertEqual(results[0].card_last4, "8092")

if __name__ == "__main__":
    unittest.main()
