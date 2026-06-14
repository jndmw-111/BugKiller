# Sample Legacy Shop

This local fixture calculates a checkout total.

The legacy service entry point expects an external database driver that is not
included in this fixture. The pricing package and its unit tests are designed
to run offline without that service.

## Business constraints

- `subtotal_cents` must be a non-negative integer.
- `discount_percent` must be an integer from 0 through 50.
- Invalid input must raise `ValueError`.
- A valid discount must never increase the checkout total.

Run existing tests from this directory:

```bash
python3 -m unittest discover -s tests -v
```
