import unittest
from sample_data.shopkit.mathutil import clamp, average, percent

class TestMathUtil(unittest.TestCase):
    def test_clamp_within_bounds(self):
        self.assertEqual(clamp(5, 0, 10), 5)

    def test_clamp_below_low(self):
        self.assertEqual(clamp(-5, 0, 10), 0)

    def test_clamp_above_high(self):
        self.assertEqual(clamp(15, 0, 10), 10)

    def test_average_non_empty(self):
        self.assertEqual(average([10, 20, 30]), 20.0)

    def test_percent_basic(self):
        self.assertEqual(percent(25, 100), 25.0)

    def test_percent_zero_whole(self):
        self.assertEqual(percent(10, 0), 0.0)

if __name__ == "__main__":
    unittest.main()
