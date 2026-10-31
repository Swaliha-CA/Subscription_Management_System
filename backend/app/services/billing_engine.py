"""
Recurring Billing Engine
========================
Core rules:
- Only processes active subscriptions whose next_billing_date <= today.
- Uses BillingCycle unique constraint to prevent duplicate invoices.
- Wraps each subscription billing in its own savepoint (nested transaction).
- Idempotent: safe to retry; duplicate attempts are skipped cleanly.
- Logs every run in BillingExecutionLog.
"""
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models.subscription import Subscription, BillingCycle
from app.models.invoice import Invoice, InvoiceLine
from app.models.billing_log import BillingExecutionLog
from app.utils.billing_calc import (
    next_billing_date as calc_next_billing_date,
    cycle_end_date,
    calculate_line_totals,
    calculate_document_totals,
)
from app.utils.numbering import next_invoice_number


def _generate_invoice_for_subscription(db: Session, sub: Subscription, today: date) -> Invoice:
    """
    Generate one invoice for `sub` covering the current billing cycle.
    Raises IntegrityError if a BillingCycle record for this period already exists
    (preventing duplicate invoices automatically).
    """
    freq = sub.plan.billing_frequency
    cycle_start = sub.next_billing_date
    cycle_end = cycle_end_date(cycle_start, freq)

    # Check for existing cycle first (belt-and-suspenders — the DB constraint is the authoritative guard)
    existing = db.query(BillingCycle).filter(
        BillingCycle.subscription_id == sub.id,
        BillingCycle.cycle_start == cycle_start,
    ).first()
    if existing:
        if existing.invoice_id:
            return None  # Already billed — skip silently
        # Cycle exists but no invoice — attempt to create invoice

    # Build invoice
    inv_number = next_invoice_number(db)
    invoice = Invoice(
        invoice_number=inv_number,
        customer_id=sub.customer_id,
        subscription_id=sub.id,
        status="confirmed",
        invoice_date=today,
        due_date=_due_date(today, sub.payment_terms),
        billing_period_start=cycle_start,
        billing_period_end=cycle_end,
        payment_terms=sub.payment_terms,
        notes=f"Auto-generated for {sub.subscription_number} — {cycle_start} to {cycle_end}",
    )
    db.add(invoice)
    db.flush()

    # Build invoice lines from subscription lines (or a single line if no explicit lines)
    if sub.lines:
        line_calcs = []
        for sl in sub.lines:
            calc = calculate_line_totals(sl.quantity, sl.unit_price, sl.discount_pct, sl.tax_pct)
            line = InvoiceLine(
                invoice_id=invoice.id,
                product_id=sl.product_id,
                variant_id=sl.variant_id,
                description=sl.description or (sl.product.name if sl.product else "Subscription"),
                quantity=sl.quantity,
                unit_price=sl.unit_price,
                discount_pct=sl.discount_pct,
                tax_pct=sl.tax_pct,
                subtotal=calc["subtotal"],
                tax_amount=calc["tax_amount"],
                total=calc["total"],
            )
            db.add(line)
            line_calcs.append(calc)
        totals = calculate_document_totals(line_calcs)
    else:
        # Single-line fallback from subscription header
        calc = calculate_line_totals(sub.quantity, sub.unit_price, sub.discount_pct, sub.tax_pct)
        product_name = sub.plan.product.name if sub.plan and sub.plan.product else "Subscription"
        line = InvoiceLine(
            invoice_id=invoice.id,
            product_id=sub.plan.product_id if sub.plan else None,
            description=f"{product_name} — {sub.plan.name if sub.plan else ''} ({cycle_start} – {cycle_end})",
            quantity=sub.quantity,
            unit_price=sub.unit_price,
            discount_pct=sub.discount_pct,
            tax_pct=sub.tax_pct,
            subtotal=calc["subtotal"],
            tax_amount=calc["tax_amount"],
            total=calc["total"],
        )
        db.add(line)
        totals = calculate_document_totals([calc])

    invoice.subtotal = totals["subtotal"]
    invoice.tax_amount = totals["tax_amount"]
    invoice.discount_amount = totals["discount_amount"]
    invoice.grand_total = totals["grand_total"]
    invoice.outstanding_amount = totals["grand_total"]
    db.flush()

    # Record billing cycle (unique constraint prevents duplicates at DB level)
    cycle = BillingCycle(
        subscription_id=sub.id,
        invoice_id=invoice.id,
        cycle_start=cycle_start,
        cycle_end=cycle_end,
        status="billed",
    )
    db.add(cycle)
    db.flush()  # Will raise IntegrityError if duplicate

    # Advance next_billing_date
    sub.next_billing_date = calc_next_billing_date(cycle_start, freq)
    return invoice


def _due_date(invoice_date: date, terms: str) -> date:
    from datetime import timedelta
    t = (terms or "").lower()
    if "15" in t:
        return invoice_date + timedelta(days=15)
    if "30" in t or "net 30" in t:
        return invoice_date + timedelta(days=30)
    if "60" in t:
        return invoice_date + timedelta(days=60)
    # "Due on receipt" or anything else → 7 days
    return invoice_date + timedelta(days=7)


def run_billing(run_type: str = "manual", actor_id: str = None) -> dict:
    """
    Execute one full billing run.
    Returns a summary dict.
    """
    db = SessionLocal()
    today = date.today()
    log = BillingExecutionLog(
        run_type=run_type,
        started_at=datetime.now(timezone.utc),
        status="running",
        created_by=actor_id,
    )
    db.add(log)
    db.commit()

    due_subs = (
        db.query(Subscription)
        .filter(
            Subscription.status == "active",
            Subscription.next_billing_date <= today,
        )
        .all()
    )

    log.subscriptions_due = len(due_subs)
    generated = 0
    failed = 0
    skipped = 0
    total_billed = Decimal("0.00")
    errors = []

    for sub in due_subs:
        # Each subscription gets its own nested savepoint so a failure
        # in one does not roll back the entire run.
        try:
            nested = db.begin_nested()
            invoice = _generate_invoice_for_subscription(db, sub, today)
            if invoice is None:
                skipped += 1
                nested.rollback()
            else:
                nested.commit()
                generated += 1
                total_billed += invoice.grand_total or Decimal("0")
        except IntegrityError:
            nested.rollback()
            skipped += 1  # Duplicate billing cycle — already billed
        except Exception as exc:
            nested.rollback()
            failed += 1
            errors.append({"subscription_id": sub.id, "error": str(exc)})

    log.invoices_generated = generated
    log.invoices_failed = failed
    log.invoices_skipped = skipped
    log.total_billed = total_billed
    log.completed_at = datetime.now(timezone.utc)
    log.status = "completed" if failed == 0 else "completed_with_errors"
    if errors:
        import json
        log.error_details = json.dumps(errors[:50])  # Cap to avoid huge blobs

    db.commit()
    # Capture values before session closes
    result_dict = {
        "run_id": log.id,
        "run_type": log.run_type,
        "date": str(today),
        "subscriptions_due": log.subscriptions_due,
        "invoices_generated": log.invoices_generated,
        "invoices_failed": log.invoices_failed,
        "invoices_skipped": log.invoices_skipped,
        "total_billed": float(log.total_billed or 0),
        "status": log.status,
        "errors": errors,
    }
    db.close()
    return result_dict


def get_billing_due_count() -> int:
    db = SessionLocal()
    try:
        return (
            db.query(Subscription)
            .filter(
                Subscription.status == "active",
                Subscription.next_billing_date <= date.today(),
            )
            .count()
        )
    finally:
        db.close()
