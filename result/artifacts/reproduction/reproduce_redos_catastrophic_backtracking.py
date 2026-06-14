#!/usr/bin/env python3
"""Minimal reproduction: ReDoS in code/app/routes/profile.js:59

Vulnerable regex: /([0-9]+)+\#/
Source: code/app/routes/profile.js, line 59
Impact: Denial of Service — CPU exhaustion via catastrophic backtracking

Trigger:
  POST /profile with bankRouting = "111111111111111111111111111111" (30 digits, no #)
  The server thread blocks for >90 seconds attempting to match the regex.

Root cause:
  The nested quantifier ([0-9]+)+ creates O(2^n) backtracking paths.
  When the input has many digits but no trailing '#', the regex engine
  exhaustively tries every possible split of digits across the inner and
  outer quantifiers.

Fix:
  Remove the redundant outer quantifier: /([0-9]+)\#/
  Or better: use a strict format like /^\d+#$/ with appropriate boundaries.
"""

import re
import time

VULNERABLE = r'([0-9]+)+\#'
FIXED = r'([0-9]+)\#'

# Minimal trigger: 30 digits with no trailing hash
ATTACK_INPUT = "1" * 30

print("Minimal ReDoS Reproduction")
print(f"Pattern: {VULNERABLE}")
print(f"Input:   '{ATTACK_INPUT}' (len={len(ATTACK_INPUT)})")
print()

# Normal control: valid input with #
print("--- Normal Control ---")
start = time.time()
re.compile(VULNERABLE).search("123456#")
print(f"Valid input: {time.time() - start:.6f}s (expected: <0.001s)")

# Attack
print("\n--- ReDoS Attack ---")
start = time.time()
re.compile(VULNERABLE).search(ATTACK_INPUT)
elapsed = time.time() - start
print(f"Attack input: {elapsed:.3f}s (expected: >1s for vulnerability confirmation)")

# Fixed regex
print("\n--- Fixed Regex ---")
start = time.time()
re.compile(FIXED).search(ATTACK_INPUT)
print(f"Same input, fixed regex: {time.time() - start:.6f}s (expected: <0.001s)")

print(f"\nVERDICT: ", end="")
if elapsed > 1.0:
    print(f"CONFIRMED — ReDoS catastrophic backtracking ({elapsed:.1f}s)")
else:
    print("NOT CONFIRMED")
