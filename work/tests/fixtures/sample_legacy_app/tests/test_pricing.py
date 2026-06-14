import unittest

from legacy_shop import checkout_total


class PricingTest(unittest.TestCase):
    def test_valid_discount(self) -> None:
        self.assertEqual(checkout_total(1000, 20), 800)

    def test_discount_above_maximum_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            checkout_total(1000, 51)


if __name__ == "__main__":
    unittest.main()
