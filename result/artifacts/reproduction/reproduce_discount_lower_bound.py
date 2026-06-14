"""Minimal reproduction generated during run dev-multistrategy-20260614."""

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = PROJECT_ROOT / "work/tests/fixtures/sample_legacy_app"
sys.path.insert(0, str(FIXTURE_ROOT))

from legacy_shop import checkout_total


test_input = {"subtotal_cents": 1000, "discount_percent": -1}
actual_total = checkout_total(**test_input)
print(
    json.dumps(
        {
            "input": test_input,
            "expected": "ValueError for discount_percent outside 0 through 50",
            "actual_total": actual_total,
            "total_increased": actual_total > test_input["subtotal_cents"],
        },
        sort_keys=True,
    )
)
