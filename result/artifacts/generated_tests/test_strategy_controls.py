"""Multi-strategy control tests generated during this independent run."""

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = PROJECT_ROOT / "work/tests/fixtures/sample_legacy_app"
sys.path.insert(0, str(FIXTURE_ROOT))

import legacy_shop
from legacy_shop import checkout_total


class DataIntegrityStrategyTest(unittest.TestCase):
    def test_valid_discounts_do_not_increase_total(self) -> None:
        for subtotal, discount in ((1000, 0), (1000, 1), (1000, 50), (999, 20)):
            with self.subTest(subtotal=subtotal, discount=discount):
                total = checkout_total(subtotal, discount)
                self.assertGreaterEqual(total, 0)
                self.assertLessEqual(total, subtotal)


class ConfigurationIntegrationStrategyTest(unittest.TestCase):
    def test_public_package_export_is_available_offline(self) -> None:
        self.assertIn("checkout_total", legacy_shop.__all__)
        self.assertIs(legacy_shop.checkout_total, checkout_total)
        self.assertTrue(callable(checkout_total))


if __name__ == "__main__":
    unittest.main(verbosity=2)
