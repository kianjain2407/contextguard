import unittest
from sample_data.shopkit.text import is_palindrome, slugify, truncate

class TestText(unittest.TestCase):
    def test_is_palindrome_simple(self):
        self.assertTrue(is_palindrome("racecar"))
        self.assertTrue(is_palindrome("Madam"))
        self.assertFalse(is_palindrome("hello"))

    def test_slugify_basic(self):
        self.assertEqual(slugify("Hello World"), "hello-world")

    def test_slugify_collapses_whitespace(self):
        """
        Critical test case for PR-4 verification:
        Ensures multiple consecutive spaces and whitespace are collapsed into single dash.
        """
        self.assertEqual(slugify("Hello   World  Test"), "hello-world-test")

    def test_truncate_basic(self):
        self.assertEqual(truncate("Short", 10), "Short")
        self.assertEqual(truncate("A very long sentence here", 10), "A very lon...")

if __name__ == "__main__":
    unittest.main()
