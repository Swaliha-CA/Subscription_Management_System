"""Payment recording and allocation routes."""
from datetime import date, datetime, timezone
from decimal import Decimal
from flask import Blueprint, request, jsonify, g
from app.database import SessionLocal
from app.models.payment import Payment, PaymentAllocation
from app.models.invoice import Invoice
from app.utils.auth_middleware import require_auth, require_admin_or_staff, require_admin, audit
from app.utils.numbering import next_payment_number

payments_bp = Blueprint("payments", __name__, url_prefix="/api/payments")


def _payment_dict(p: Payment) -> dict:
    return {
        "id": p.id,
        "payment_number": p.payment_number,
        "customer_id": p.customer_id,
        "customer_name": p.customer.user.full_name if p.customer and p.customer.user else None,
        "payment_method": p.payment_method,
        "amount": float(p.amount or 0),
        "payment_date": str(p.payment_date) if p.payment_date else None,
        "reference_number": p.reference_number,
        "transaction_id": p.transaction_id,
        "gateway": p.gateway,
        "notes": p.notes,
        "status": p.status,
        "allocated_amount": float(p.allocated_amount),
        "unallocated_amount": float(p.unallocated_amount),
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "allocations": [{
            "invoice_id": a.invoice_id,
            "invoice_number": a.invoice.invoice_number if a.invoice else None,
            "amount": float(a.amount or 0),
        } for a in p.allocations],
    }


@payments_bp.route("", methods=["GET"])
@require_auth
def list_payments():
    db = SessionLocal()
    try:
        q = db.query(Payment)
        role = g.current_user.role_name
        if role == "customer":
            if not g.current_user.customer:
                return jsonify({"items": [], "total": 0})
            q = q.filter(Payment.customer_id == g.current_user.customer.id)
        else:
            customer_id = request.args.get("customer_id")
            if customer_id:
                q = q.filter(Payment.customer_id == customer_id)

        total = q.count()
        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(int(request.args.get("per_page", 20)), 100)
        items = q.order_by(Payment.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        return jsonify({
            "items": [_payment_dict(p) for p in items],
            "total": total, "page": page, "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        })
    finally:
        db.close()


@payments_bp.route("", methods=["POST"])
@require_admin_or_staff
def record_payment():
    """Record a payment and optionally allocate it to one or more invoices."""
    data = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        amount = Decimal(str(data.get("amount", 0)))
        if amount <= 0:
            return jsonify({"error": "Payment amount must be positive."}), 400

        p = Payment(
            payment_number=next_payment_number(db),
            customer_id=data["customer_id"],
            payment_method=data.get("payment_method", "cash"),
            amount=amount,
            payment_date=date.fromisoformat(data.get("payment_date", str(date.today()))),
            reference_number=data.get("reference_number"),
            transaction_id=data.get("transaction_id"),
            gateway=data.get("gateway", "manual"),
            notes=data.get("notes"),
            status="confirmed",
            recorded_by=g.current_user.id,
        )
        db.add(p)
        db.flush()

        remaining = amount
        for alloc_data in data.get("allocations", []):
            if remaining <= 0:
                break
            inv = db.query(Invoice).filter(Invoice.id == alloc_data["invoice_id"]).first()
            if not inv or inv.status in ("paid", "cancelled"):
                continue
            # Enforce customer ownership
            if inv.customer_id != data["customer_id"]:
                return jsonify({"error": f"Invoice {inv.invoice_number} does not belong to this customer."}), 400

            outstanding = inv.outstanding_amount or Decimal("0")
            if outstanding <= 0:
                continue

            alloc_amount = min(remaining, outstanding, Decimal(str(alloc_data.get("amount", outstanding))))
            if alloc_amount <= 0:
                continue

            # Prevent overpayment
            if alloc_amount > outstanding:
                return jsonify({
                    "error": f"Allocation amount {alloc_amount} exceeds outstanding {outstanding} on {inv.invoice_number}."
                }), 400

            alloc = PaymentAllocation(
                payment_id=p.id,
                invoice_id=inv.id,
                amount=alloc_amount,
            )
            db.add(alloc)

            inv.paid_amount = (inv.paid_amount or Decimal("0")) + alloc_amount
            inv.outstanding_amount = (inv.outstanding_amount or Decimal("0")) - alloc_amount
            if inv.outstanding_amount <= Decimal("0.01"):
                inv.outstanding_amount = Decimal("0.00")
                inv.status = "paid"
            else:
                inv.status = "partially_paid"

            remaining -= alloc_amount

        audit(db, g.current_user, "payment.recorded", "payment", p.id,
              notes=f"{p.payment_number} ₹{amount}")
        db.commit()
        db.refresh(p)
        return jsonify(_payment_dict(p)), 201
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@payments_bp.route("/<pay_id>", methods=["GET"])
@require_auth
def get_payment(pay_id):
    db = SessionLocal()
    try:
        p = db.query(Payment).filter(Payment.id == pay_id).first()
        if not p:
            return jsonify({"error": "Payment not found"}), 404
        role = g.current_user.role_name
        if role == "customer":
            if not p.customer or not p.customer.user or p.customer.user.id != g.current_user.id:
                return jsonify({"error": "Access denied"}), 403
        return jsonify(_payment_dict(p))
    finally:
        db.close()
