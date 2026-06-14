"""Generated during run dev-multistrategy-20260614."""

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = PROJECT_ROOT / "work/tests/fixtures/sample_legacy_app"
sys.path.insert(0, str(FIXTURE_ROOT))

from legacy_shop import checkout_total


class GeneratedDiscountBoundaryTest(unittest.TestCase):
    def test_discount_below_documented_minimum_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            checkout_total(1000, -1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
