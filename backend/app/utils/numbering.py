"""Sequential number generation for quotations, subscriptions, invoices, payments."""
from sqlalchemy.orm import Session


def _next_seq(db: Session, model_class, column_attr, prefix: str, pad: int = 5) -> str:
    """
    Find the highest existing number with the given prefix, increment by 1,
    and return the new formatted number.
    Thread-safe for SQLite with WAL (single-writer) — for PostgreSQL add advisory locks.
    """
    from sqlalchemy import func, cast, Integer
    col = getattr(model_class, column_attr)
    # Pull only rows with this prefix
    rows = db.query(col).filter(col.like(f"{prefix}%")).all()
    max_n = 0
    for (val,) in rows:
        try:
            max_n = max(max_n, int(val[len(prefix):]))
        except (ValueError, TypeError):
            pass
    return f"{prefix}{str(max_n + 1).zfill(pad)}"


def next_quotation_number(db: Session) -> str:
    from app.models.quotation import Quotation
    return _next_seq(db, Quotation, "quotation_number", "QT-")


def next_subscription_number(db: Session) -> str:
    from app.models.subscription import Subscription
    return _next_seq(db, Subscription, "subscription_number", "SUB-")


def next_invoice_number(db: Session) -> str:
    from app.models.invoice import Invoice
    return _next_seq(db, Invoice, "invoice_number", "INV-")


def next_payment_number(db: Session) -> str:
    from app.models.payment import Payment
    return _next_seq(db, Payment, "payment_number", "PAY-")


def next_customer_code(db: Session) -> str:
    from app.models.customer import Customer
    return _next_seq(db, Customer, "customer_code", "CUST-")
