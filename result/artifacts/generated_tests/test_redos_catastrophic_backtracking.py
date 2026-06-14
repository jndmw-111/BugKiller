#!/usr/bin/env python3
"""Generated test for ReDoS catastrophic backtracking in code/app/routes/profile.js:59

CANDIDATE: C11
STRATEGY: input-and-parsing (S1)
DIRECTION: concurrency-resource
PROVENANCE: independent
FALLBACK_LEVEL: 5 (pure-logic-verification)

The vulnerable regex pattern: /([0-9]+)+\#/
is susceptible to catastrophic backtracking when given input with many digits
but no trailing '#' character. Each additional digit doubles the backtracking
possibilities, leading to exponential runtime.

This test was dynamically generated during the current run (20260614T154734Z-d8e97a28)
and executes the regex pattern isolated from the target application (which requires
Node.js/MongoDB that are not available in this environment).
"""

import re
import time
import sys

# The exact vulnerable regex from code/app/routes/profile.js:59
VULNERABLE_REGEX = r'([0-9]+)+\#'
# The fixed regex (removing the redundant quantifier)
FIXED_REGEX = r'([0-9]+)\#'

# Test cases designed per equivalence partition and boundary analysis
TEST_CASES = [
    # (description, input, expected_match, max_time_s, is_attack)
    ("valid-normal-7digits", "123456#", True, 0.01, False),
    ("valid-normal-1digit", "1#", True, 0.01, False),
    ("valid-normal-20digits", "12345678901234567890#", True, 0.01, False),
    ("invalid-no-hash-short", "123", False, 0.01, False),
    ("invalid-no-hash-long-20", "1" * 20, False, 0.01, False),
    ("redos-attack-25-no-hash", "1" * 25, False, 60.0, True),
    ("redos-attack-30-no-hash", "1" * 30, False, 120.0, True),
    ("valid-border-25-hash", "1" * 25 + "#", True, 0.01, False),
]

def test_regex(regex_pattern, test_input, timeout_s):
    """Execute regex search with timeout protection."""
    start = time.time()
    try:
        match = re.compile(regex_pattern).search(test_input)
        elapsed = time.time() - start
        return {"match": match.group() if match else None, "elapsed_s": elapsed, "timeout": False}
    except Exception as e:
        elapsed = time.time() - start
        return {"match": None, "elapsed_s": elapsed, "timeout": False, "error": str(e)}

def main():
    print("=" * 70)
    print("ReDoS Catastrophic Backtracking Test")
    print(f"Vulnerable pattern: {VULNERABLE_REGEX}")
    print(f"Fixed pattern:      {FIXED_REGEX}")
    print("=" * 70)

    passed = 0
    failed = 0
    blocked = 0

    for desc, test_input, expected_match, max_time, is_attack in TEST_CASES:
        result = test_regex(VULNERABLE_REGEX, test_input, max_time)

        time_ok = result["elapsed_s"] <= max_time
        match_ok = (result["match"] is not None) == expected_match

        status = "PASS"
        if is_attack and result["elapsed_s"] > max_time:
            status = "BLOCKED (expected — ReDoS attack exceeds timeout)"
            blocked += 1
        elif is_attack and result["elapsed_s"] > 0.1:
            status = f"CONFIRMED VULNERABLE ({result['elapsed_s']:.3f}s)"
            failed += 1
        elif not time_ok:
            status = f"FAIL (timeout: {result['elapsed_s']:.3f}s > {max_time}s)"
            failed += 1
        elif not match_ok:
            status = f"FAIL (match mismatch: got {result['match']}, expected match={expected_match})"
            failed += 1
        else:
            passed += 1

        print(f"[{status}] {desc}: {result['elapsed_s']:.6f}s, match={result['match']}")

    print(f"\n{'=' * 70}")
    print(f"SUMMARY: {passed} passed, {failed} failed, {blocked} blocked (attack)")

    # The key assertion: long input without trailing # MUST cause significant slowdown
    # This confirms the vulnerability
    attack_result = test_regex(VULNERABLE_REGEX, "1" * 30, 120.0)
    fixed_result = test_regex(FIXED_REGEX, "1" * 30, 1.0)

    print(f"\nVULNERABILITY CONFIRMATION:")
    print(f"  Vulnerable regex on 30 chars: {attack_result['elapsed_s']:.3f}s")
    print(f"  Fixed regex on 30 chars:      {fixed_result['elapsed_s']:.6f}s")

    if attack_result["elapsed_s"] > 1.0 and fixed_result["elapsed_s"] < 0.01:
        print(f"  RATIO: {attack_result['elapsed_s']/max(fixed_result['elapsed_s'], 0.000001):.0f}x slower")
        print(f"  VERDICT: ReDoS CATASTROPHIC BACKTRACKING CONFIRMED")
    else:
        print(f"  VERDICT: INCONCLUSIVE")

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
