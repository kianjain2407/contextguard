import unittest
from sample_data.shopkit.cart import cart_total

class TestCart(unittest.TestCase):
    def test_cart_total_simple(self):
        items = [{"price": 10.0, "quantity": 2}, {"price": 5.0, "quantity": 1}]
        self.assertEqual(cart_total(items), 25.0)

    def test_cart_total_with_discount(self):
        items = [{"price": 100.0, "quantity": 1}]
        self.assertEqual(cart_total(items, discount_pct=10.0), 90.0)

    def test_cart_total_rounding(self):
        items = [{"price": 19.99, "quantity": 3}]
        self.assertEqual(cart_total(items, discount_pct=15.0), 50.97)

if __name__ == "__main__":
    unittest.main()
