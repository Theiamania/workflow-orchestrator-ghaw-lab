"""Deterministic acceptance tests for the E-01 fixture. Do not modify."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from normalize import slugify  # noqa: E402


class SlugifyTests(unittest.TestCase):
    def test_examples(self):
        self.assertEqual(slugify("Hello, World!"), "hello-world")
        self.assertEqual(slugify("  Café  crème  "), "cafe-creme")
        self.assertEqual(slugify("a---b___c"), "a-b-c")
        self.assertEqual(slugify("Ünïcödé 2026"), "unicode-2026")

    def test_digits_and_case(self):
        self.assertEqual(slugify("ABC123def"), "abc123def")

    def test_non_ascii_without_decomposition_is_dropped(self):
        self.assertEqual(slugify("snow ☃ man"), "snow-man")
        self.assertEqual(slugify("東京 tokyo"), "tokyo")

    def test_truncation_then_strip(self):
        text = "a" * 39 + " bcdef"
        self.assertEqual(slugify(text), "a" * 39)
        self.assertEqual(slugify("x" * 60), "x" * 40)

    def test_empty_results(self):
        for bad in ["", "!!!", "   ", "☃☃"]:
            with self.assertRaises(ValueError):
                slugify(bad)

    def test_type_error(self):
        for bad in [123, None, b"bytes", ["a"]]:
            with self.assertRaises(TypeError):
                slugify(bad)


if __name__ == "__main__":
    unittest.main()
