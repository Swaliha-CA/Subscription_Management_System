"""Billing cycle date calculations — backend-only, handles edge cases correctly."""
from datetime import date, timedelta
import calendar
from decimal import Decimal, ROUND_HALF_UP


def add_months(d: date, months: int) -> date:
    """Add months to a date, clamping to end-of-month when needed."""
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def next_billing_date(current: date, frequency: str) -> date:
    """
    Calculate the next billing date from `current` based on frequency.

    Supported frequencies: daily | weekly | monthly | yearly
    """
    freq = frequency.lower()
    if freq == "daily":
        return current + timedelta(days=1)
    elif freq == "weekly":
        return current + timedelta(weeks=1)
    elif freq == "monthly":
        return add_months(current, 1)
    elif freq == "yearly":
        return add_months(current, 12)
    else:
        raise ValueError(f"Unknown billing frequency: {frequency!r}")


def cycle_end_date(start: date, frequency: str) -> date:
    """Return the last day of the current billing cycle (one day before the next billing date)."""
    nbd = next_billing_date(start, frequency)
    return nbd - timedelta(days=1)


def calculate_line_totals(
    quantity: Decimal,
    unit_price: Decimal,
    discount_pct: Decimal,
    tax_pct: Decimal,
) -> dict:
    """
    Calculate subtotal, discount amount, taxable amount, tax amount, and total
    for one invoice/quotation/subscription line.

    All values rounded to 2 decimal places using ROUND_HALF_UP.
    """
    qty = Decimal(str(quantity))
    price = Decimal(str(unit_price))
    disc = Decimal(str(discount_pct))
    tax = Decimal(str(tax_pct))

    gross = (qty * price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    discount_amount = (gross * disc / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    subtotal = gross - discount_amount
    tax_amount = (subtotal * tax / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = subtotal + tax_amount

    return {
        "gross": gross,
        "subtotal": subtotal,
        "discount_amount": discount_amount,
        "tax_amount": tax_amount,
        "total": total,
    }


def calculate_document_totals(lines: list[dict]) -> dict:
    """
    Aggregate line totals into document-level subtotal / tax / discount / grand_total.
    Each line dict must have keys: subtotal, tax_amount, discount_amount, total.
    """
    subtotal = Decimal("0.00")
    tax_amount = Decimal("0.00")
    discount_amount = Decimal("0.00")
    grand_total = Decimal("0.00")

    for line in lines:
        subtotal += Decimal(str(line.get("subtotal", "0")))
        tax_amount += Decimal(str(line.get("tax_amount", "0")))
        discount_amount += Decimal(str(line.get("discount_amount", "0")))
        grand_total += Decimal(str(line.get("total", "0")))

    return {
        "subtotal": subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "tax_amount": tax_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "discount_amount": discount_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "grand_total": grand_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
    }


def is_plan_available(plan) -> tuple[bool, str]:
    """Check if a subscription plan is currently available for new subscriptions."""
    today = date.today()
    if not plan.is_active:
        return False, "Plan is inactive."
    if plan.available_from and today < plan.available_from:
        return False, f"Plan is not available until {plan.available_from}."
    if plan.available_until and today > plan.available_until:
        return False, f"Plan expired on {plan.available_until}."
    return True, ""
