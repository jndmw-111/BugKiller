"""Checkout pricing used by the development fixture."""


def checkout_total(subtotal_cents: int, discount_percent: int) -> int:
    if not isinstance(subtotal_cents, int) or isinstance(subtotal_cents, bool):
        raise ValueError("subtotal_cents must be an integer")
    if subtotal_cents < 0:
        raise ValueError("subtotal_cents must be non-negative")
    if not isinstance(discount_percent, int) or isinstance(discount_percent, bool):
        raise ValueError("discount_percent must be an integer")
    if discount_percent > 50:
        raise ValueError("discount_percent exceeds maximum")

    discount = subtotal_cents * discount_percent // 100
    return subtotal_cents - discount
