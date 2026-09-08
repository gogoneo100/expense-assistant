import unittest
from app.database import init_db
from app.models import Category
from app.classifier import parse_manual_input, classify_merchant

class TestClassifier(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_classify_merchant(self):
        self.assertEqual(classify_merchant("星巴克信義門市"), Category.DINING_SELF)
        self.assertEqual(classify_merchant("和女友吃 燒肉"), Category.DINING_GIRLFRIEND)
        self.assertEqual(classify_merchant("家人聚餐 鼎泰豐"), Category.DINING_FAMILY)
        self.assertEqual(classify_merchant("Uber 乘車"), Category.TRANSPORT)
        self.assertEqual(classify_merchant("蝦皮購物"), Category.SHOPPING)
        self.assertEqual(classify_merchant("Netflix 串流影音"), Category.ENTERTAINMENT)
        self.assertEqual(classify_merchant("中華電信行動帳單"), Category.BILLS)

    def test_parse_manual_input(self):
        # Case 1: Simple food (defaults to 自己吃)
        amt, merchant, cat, note = parse_manual_input("午餐 120")
        self.assertEqual(amt, 120.0)
        self.assertEqual(merchant, "午餐")
        self.assertEqual(cat, Category.DINING_SELF)

        # Case 2: Dining with girlfriend
        amt, merchant, cat, note = parse_manual_input("和女友吃 燒肉 1500")
        self.assertEqual(amt, 1500.0)
        self.assertEqual(merchant, "燒肉")
        self.assertEqual(cat, Category.DINING_GIRLFRIEND)

        # Case 3: Dining with family
        amt, merchant, cat, note = parse_manual_input("跟家人聚餐 2600 父親節聚餐")
        self.assertEqual(amt, 2600.0)
        self.assertEqual(merchant, "父親節聚餐")
        self.assertEqual(cat, Category.DINING_FAMILY)

        # Case 4: Eating alone
        amt, merchant, cat, note = parse_manual_input("自己吃 便當 100")
        self.assertEqual(amt, 100.0)
        self.assertEqual(merchant, "便當")
        self.assertEqual(cat, Category.DINING_SELF)

        # Case 5: Taxi with category
        amt, merchant, cat, note = parse_manual_input("計程車 250 交通")
        self.assertEqual(amt, 250.0)
        self.assertEqual(merchant, "計程車")
        self.assertEqual(cat, Category.TRANSPORT)

        # Case 6: Shopping with note
        amt, merchant, cat, note = parse_manual_input("好市多 1500 購物 採買下週食材")
        self.assertEqual(amt, 1500.0)
        self.assertEqual(merchant, "好市多")
        self.assertEqual(cat, Category.SHOPPING)
        self.assertIn("採買下週食材", note)

if __name__ == "__main__":
    unittest.main()
