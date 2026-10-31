"""Invoice management routes."""
from datetime import date, datetime, timezone
from decimal import Decimal
from flask import Blueprint, request, jsonify, g
from app.database import SessionLocal
from app.models.invoice import Invoice, InvoiceLine
from app.utils.auth_middleware import require_auth, require_admin_or_staff, require_admin, audit
from app.utils.numbering import next_invoice_number
from app.utils.billing_calc import calculate_line_totals, calculate_document_totals

invoices_bp = Blueprint("invoices", __name__, url_prefix="/api/invoices")


def _invoice_dict(inv: Invoice) -> dict:
    return {
        "id": inv.id,
        "invoice_number": inv.invoice_number,
        "customer_id": inv.customer_id,
        "customer_name": inv.customer.user.full_name if inv.customer and inv.customer.user else None,
        "subscription_id": inv.subscription_id,
        "subscription_number": inv.subscription.subscription_number if inv.subscription else None,
        "status": inv.status,
        "invoice_date": str(inv.invoice_date) if inv.invoice_date else None,
        "due_date": str(inv.due_date) if inv.due_date else None,
        "billing_period_start": str(inv.billing_period_start) if inv.billing_period_start else None,
        "billing_period_end": str(inv.billing_period_end) if inv.billing_period_end else None,
        "subtotal": float(inv.subtotal or 0),
        "tax_amount": float(inv.tax_amount or 0),
        "discount_amount": float(inv.discount_amount or 0),
        "grand_total": float(inv.grand_total or 0),
        "paid_amount": float(inv.paid_amount or 0),
        "outstanding_amount": float(inv.outstanding_amount or 0),
        "payment_terms": inv.payment_terms,
        "notes": inv.notes,
        "is_overdue": inv.is_overdue,
        "overdue_days": (date.today() - inv.due_date).days if inv.is_overdue and inv.due_date else 0,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
        "confirmed_at": inv.confirmed_at.isoformat() if inv.confirmed_at else None,
        "lines": [{
            "id": l.id,
            "description": l.description,
            "product_name": l.product.name if l.product else None,
            "variant_name": l.variant.name if l.variant else None,
            "quantity": float(l.quantity or 1),
            "unit_price": float(l.unit_price or 0),
            "discount_pct": float(l.discount_pct or 0),
            "tax_pct": float(l.tax_pct or 0),
            "subtotal": float(l.subtotal or 0),
            "tax_amount": float(l.tax_amount or 0),
            "total": float(l.total or 0),
        } for l in inv.lines],
        "payments": [{
            "id": a.payment.id,
            "payment_number": a.payment.payment_number,
            "amount": float(a.amount or 0),
            "method": a.payment.payment_method,
            "date": str(a.payment.payment_date),
            "reference": a.payment.reference_number,
        } for a in inv.payment_allocations],
    }


@invoices_bp.route("", methods=["GET"])
@require_auth
def list_invoices():
    db = SessionLocal()
    try:
        q = db.query(Invoice)
        role = g.current_user.role_name
        if role == "customer":
            if not g.current_user.customer:
                return jsonify({"items": [], "total": 0})
            q = q.filter(Invoice.customer_id == g.current_user.customer.id)
        else:
            customer_id = request.args.get("customer_id")
            if customer_id:
                q = q.filter(Invoice.customer_id == customer_id)

        status = request.args.get("status")
        if status:
            q = q.filter(Invoice.status == status)
        search = request.args.get("search", "").strip()
        if search:
            q = q.filter(Invoice.invoice_number.ilike(f"%{search}%"))
        overdue_only = request.args.get("overdue", "").lower() == "true"
        if overdue_only:
            q = q.filter(
                Invoice.status.notin_(["paid", "cancelled"]),
                Invoice.due_date < date.today(),
                Invoice.outstanding_amount > 0,
            )

        total = q.count()
        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(int(request.args.get("per_page", 20)), 100)
        items = q.order_by(Invoice.invoice_date.desc()).offset((page - 1) * per_page).limit(per_page).all()
        return jsonify({
            "items": [_invoice_dict(i) for i in items],
            "total": total, "page": page, "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        })
    finally:
        db.close()


@invoices_bp.route("/<inv_id>", methods=["GET"])
@require_auth
def get_invoice(inv_id):
    db = SessionLocal()
    try:
        inv = db.query(Invoice).filter(Invoice.id == inv_id).first()
        if not inv:
            return jsonify({"error": "Invoice not found"}), 404
        role = g.current_user.role_name
        if role == "customer":
            if not inv.customer or not inv.customer.user or inv.customer.user.id != g.current_user.id:
                return jsonify({"error": "Access denied"}), 403
        return jsonify(_invoice_dict(inv))
    finally:
        db.close()


@invoices_bp.route("", methods=["POST"])
@require_admin_or_staff
def create_invoice():
    data = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        inv_date = date.fromisoformat(data.get("invoice_date", str(date.today())))
        due_days = int(data.get("due_days", 7))
        from datetime import timedelta
        inv = Invoice(
            invoice_number=next_invoice_number(db),
            customer_id=data["customer_id"],
            subscription_id=data.get("subscription_id"),
            status="draft",
            invoice_date=inv_date,
            due_date=inv_date + timedelta(days=due_days),
            payment_terms=data.get("payment_terms", "Due on receipt"),
            notes=data.get("notes"),
            created_by=g.current_user.id,
        )
        db.add(inv)
        db.flush()

        line_calcs = []
        for ld in data.get("lines", []):
            calc = calculate_line_totals(
                Decimal(str(ld.get("quantity", 1))),
                Decimal(str(ld.get("unit_price", 0))),
                Decimal(str(ld.get("discount_pct", 0))),
                Decimal(str(ld.get("tax_pct", 0))),
            )
            l = InvoiceLine(
                invoice_id=inv.id,
                product_id=ld.get("product_id"),
                description=ld.get("description", ""),
                quantity=Decimal(str(ld.get("quantity", 1))),
                unit_price=Decimal(str(ld.get("unit_price", 0))),
                discount_pct=Decimal(str(ld.get("discount_pct", 0))),
                tax_pct=Decimal(str(ld.get("tax_pct", 0))),
                subtotal=calc["subtotal"],
                tax_amount=calc["tax_amount"],
                total=calc["total"],
            )
            db.add(l)
            line_calcs.append(calc)

        totals = calculate_document_totals(line_calcs)
        inv.subtotal = totals["subtotal"]
        inv.tax_amount = totals["tax_amount"]
        inv.discount_amount = totals["discount_amount"]
        inv.grand_total = totals["grand_total"]
        inv.outstanding_amount = totals["grand_total"]

        audit(db, g.current_user, "invoice.created", "invoice", inv.id, notes=inv.invoice_number)
        db.commit()
        db.refresh(inv)
        return jsonify(_invoice_dict(inv)), 201
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@invoices_bp.route("/<inv_id>/confirm", methods=["POST"])
@require_admin_or_staff
def confirm_invoice(inv_id):
    db = SessionLocal()
    try:
        inv = db.query(Invoice).filter(Invoice.id == inv_id).first()
        if not inv:
            return jsonify({"error": "Invoice not found"}), 404
        if inv.status != "draft":
            return jsonify({"error": f"Invoice is already '{inv.status}'."}), 400
        inv.status = "confirmed"
        inv.confirmed_at = datetime.now(timezone.utc)
        audit(db, g.current_user, "invoice.confirmed", "invoice", inv_id)
        db.commit()
        db.refresh(inv)
        return jsonify(_invoice_dict(inv))
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@invoices_bp.route("/<inv_id>/cancel", methods=["POST"])
@require_admin
def cancel_invoice(inv_id):
    db = SessionLocal()
    try:
        inv = db.query(Invoice).filter(Invoice.id == inv_id).first()
        if not inv:
            return jsonify({"error": "Invoice not found"}), 404
        if inv.status == "paid":
            return jsonify({"error": "Cannot cancel a paid invoice."}), 400
        inv.status = "cancelled"
        inv.cancelled_at = datetime.now(timezone.utc)
        audit(db, g.current_user, "invoice.cancelled", "invoice", inv_id)
        db.commit()
        db.refresh(inv)
        return jsonify(_invoice_dict(inv))
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@invoices_bp.route("/<inv_id>/send-reminder", methods=["POST"])
@require_admin_or_staff
def send_reminder(inv_id):
    db = SessionLocal()
    try:
        inv = db.query(Invoice).filter(Invoice.id == inv_id).first()
        if not inv:
            return jsonify({"error": "Invoice not found"}), 404
        from app.utils.email_service import send_invoice_reminder
        from app.models.notification import Notification
        c = inv.customer
        email = c.user.email if c and c.user else None
        if not email:
            return jsonify({"error": "Customer email not found"}), 400

        result = send_invoice_reminder(
            email, c.user.full_name,
            inv.invoice_number,
            str(inv.outstanding_amount or 0),
            str(inv.due_date),
        )
        notif = Notification(
            customer_id=c.id,
            notification_type="payment_reminder",
            subject=f"Payment Reminder — {inv.invoice_number}",
            body=f"Reminder sent for ₹{inv.outstanding_amount} due {inv.due_date}",
            reference_id=inv.id,
            reference_type="invoice",
            sent_at=datetime.now(timezone.utc),
            send_status=result.get("status", "unknown"),
        )
        db.add(notif)
        audit(db, g.current_user, "invoice.reminder_sent", "invoice", inv_id)
        db.commit()
        return jsonify({"message": "Reminder sent.", "result": result})
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()
