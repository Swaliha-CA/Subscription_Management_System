"""Quotation template and quotation routes."""
from datetime import date, timedelta
from decimal import Decimal
from flask import Blueprint, request, jsonify, g
from app.database import SessionLocal
from app.models.quotation import Quotation, QuotationLine, QuotationTemplate
from app.models.subscription import Subscription, SubscriptionLine
from app.utils.auth_middleware import require_auth, require_admin_or_staff, audit
from app.utils.numbering import next_quotation_number, next_subscription_number
from app.utils.billing_calc import calculate_line_totals, calculate_document_totals, next_billing_date, is_plan_available

quotations_bp = Blueprint("quotations", __name__, url_prefix="/api/quotations")


def _line_dict(l: QuotationLine) -> dict:
    return {
        "id": l.id,
        "product_id": l.product_id,
        "product_name": l.product.name if l.product else None,
        "variant_id": l.variant_id,
        "variant_name": l.variant.name if l.variant else None,
        "description": l.description,
        "quantity": float(l.quantity or 1),
        "unit_price": float(l.unit_price or 0),
        "discount_pct": float(l.discount_pct or 0),
        "tax_pct": float(l.tax_pct or 0),
        "subtotal": float(l.subtotal or 0),
        "tax_amount": float(l.tax_amount or 0),
        "total": float(l.total or 0),
    }


def _quotation_dict(q: Quotation) -> dict:
    return {
        "id": q.id,
        "quotation_number": q.quotation_number,
        "customer_id": q.customer_id,
        "customer_name": q.customer.user.full_name if q.customer and q.customer.user else None,
        "plan_id": q.plan_id,
        "plan_name": q.plan.name if q.plan else None,
        "status": q.status,
        "validity_days": q.validity_days,
        "expiry_date": str(q.expiry_date) if q.expiry_date else None,
        "payment_terms": q.payment_terms,
        "notes": q.notes,
        "subtotal": float(q.subtotal or 0),
        "tax_amount": float(q.tax_amount or 0),
        "discount_amount": float(q.discount_amount or 0),
        "grand_total": float(q.grand_total or 0),
        "subscription_id": q.subscription.id if q.subscription else None,
        "created_at": q.created_at.isoformat() if q.created_at else None,
        "lines": [_line_dict(l) for l in q.lines],
    }


def _recalc_quotation(db, q: Quotation):
    """Recalculate all line totals and quotation totals from raw inputs."""
    line_dicts = []
    for line in q.lines:
        result = calculate_line_totals(
            line.quantity or Decimal("1"),
            line.unit_price or Decimal("0"),
            line.discount_pct or Decimal("0"),
            line.tax_pct or Decimal("0"),
        )
        line.subtotal = result["subtotal"]
        line.tax_amount = result["tax_amount"]
        line.total = result["total"]
        line_dicts.append(result)

    totals = calculate_document_totals(line_dicts)
    q.subtotal = totals["subtotal"]
    q.tax_amount = totals["tax_amount"]
    q.discount_amount = totals["discount_amount"]
    q.grand_total = totals["grand_total"]


@quotations_bp.route("", methods=["GET"])
@require_admin_or_staff
def list_quotations():
    db = SessionLocal()
    try:
        q = db.query(Quotation)
        search = request.args.get("search", "").strip()
        if search:
            q = q.filter(Quotation.quotation_number.ilike(f"%{search}%"))
        status = request.args.get("status")
        if status:
            q = q.filter(Quotation.status == status)
        customer_id = request.args.get("customer_id")
        if customer_id:
            q = q.filter(Quotation.customer_id == customer_id)

        total = q.count()
        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(int(request.args.get("per_page", 20)), 100)
        items = q.order_by(Quotation.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        return jsonify({
            "items": [_quotation_dict(qq) for qq in items],
            "total": total, "page": page, "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        })
    finally:
        db.close()


@quotations_bp.route("/<qid>", methods=["GET"])
@require_auth
def get_quotation(qid):
    db = SessionLocal()
    try:
        q = db.query(Quotation).filter(Quotation.id == qid).first()
        if not q:
            return jsonify({"error": "Quotation not found"}), 404
        role = g.current_user.role_name
        if role == "customer":
            if not q.customer or not q.customer.user or q.customer.user.id != g.current_user.id:
                return jsonify({"error": "Access denied"}), 403
        return jsonify(_quotation_dict(q))
    finally:
        db.close()


@quotations_bp.route("", methods=["POST"])
@require_admin_or_staff
def create_quotation():
    data = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        validity = int(data.get("validity_days", 30))
        today = date.today()
        q = Quotation(
            quotation_number=next_quotation_number(db),
            customer_id=data["customer_id"],
            plan_id=data.get("plan_id"),
            template_id=data.get("template_id"),
            status="draft",
            validity_days=validity,
            expiry_date=today + timedelta(days=validity),
            payment_terms=data.get("payment_terms", "Due on receipt"),
            notes=data.get("notes"),
            created_by=g.current_user.id,
        )
        db.add(q)
        db.flush()

        for ld in data.get("lines", []):
            line = QuotationLine(
                quotation_id=q.id,
                product_id=ld["product_id"],
                variant_id=ld.get("variant_id"),
                description=ld.get("description"),
                quantity=Decimal(str(ld.get("quantity", 1))),
                unit_price=Decimal(str(ld.get("unit_price", 0))),
                discount_pct=Decimal(str(ld.get("discount_pct", 0))),
                tax_pct=Decimal(str(ld.get("tax_pct", 0))),
            )
            db.add(line)

        db.flush()
        _recalc_quotation(db, q)
        audit(db, g.current_user, "quotation.created", "quotation", q.id, notes=q.quotation_number)
        db.commit()
        db.refresh(q)
        return jsonify(_quotation_dict(q)), 201
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@quotations_bp.route("/<qid>", methods=["PUT"])
@require_admin_or_staff
def update_quotation(qid):
    db = SessionLocal()
    try:
        q = db.query(Quotation).filter(Quotation.id == qid).first()
        if not q:
            return jsonify({"error": "Quotation not found"}), 404
        if q.status not in ("draft", "sent"):
            return jsonify({"error": f"Cannot edit a quotation in '{q.status}' status."}), 400

        data = request.get_json(silent=True) or {}
        for field in ("plan_id", "payment_terms", "notes"):
            if field in data:
                setattr(q, field, data[field])
        if "validity_days" in data:
            q.validity_days = int(data["validity_days"])
            q.expiry_date = date.today() + timedelta(days=q.validity_days)

        if "lines" in data:
            # Replace lines
            for old_line in q.lines:
                db.delete(old_line)
            db.flush()
            for ld in data["lines"]:
                line = QuotationLine(
                    quotation_id=q.id,
                    product_id=ld["product_id"],
                    variant_id=ld.get("variant_id"),
                    description=ld.get("description"),
                    quantity=Decimal(str(ld.get("quantity", 1))),
                    unit_price=Decimal(str(ld.get("unit_price", 0))),
                    discount_pct=Decimal(str(ld.get("discount_pct", 0))),
                    tax_pct=Decimal(str(ld.get("tax_pct", 0))),
                )
                db.add(line)
            db.flush()

        _recalc_quotation(db, q)
        audit(db, g.current_user, "quotation.updated", "quotation", qid)
        db.commit()
        db.refresh(q)
        return jsonify(_quotation_dict(q))
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@quotations_bp.route("/<qid>/confirm", methods=["POST"])
@require_admin_or_staff
def confirm_quotation(qid):
    db = SessionLocal()
    try:
        q = db.query(Quotation).filter(Quotation.id == qid).first()
        if not q:
            return jsonify({"error": "Quotation not found"}), 404
        if q.status not in ("draft", "sent"):
            return jsonify({"error": f"Cannot confirm quotation in '{q.status}' status."}), 400
        if q.expiry_date and q.expiry_date < date.today() and g.current_user.role_name != "admin":
            return jsonify({"error": "Quotation has expired. Only admin can confirm expired quotations."}), 400

        from datetime import datetime, timezone
        q.status = "confirmed"
        q.confirmed_by = g.current_user.id
        q.confirmed_at = datetime.now(timezone.utc)
        audit(db, g.current_user, "quotation.confirmed", "quotation", qid)
        db.commit()
        return jsonify(_quotation_dict(q))
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@quotations_bp.route("/<qid>/convert", methods=["POST"])
@require_admin_or_staff
def convert_to_subscription(qid):
    """Convert a confirmed quotation into a subscription."""
    db = SessionLocal()
    try:
        q = db.query(Quotation).filter(Quotation.id == qid).first()
        if not q:
            return jsonify({"error": "Quotation not found"}), 404
        if q.status != "confirmed":
            return jsonify({"error": "Only confirmed quotations can be converted."}), 400
        if q.subscription:
            return jsonify({"error": "This quotation has already been converted.", "subscription_id": q.subscription.id}), 409

        plan = q.plan
        if not plan:
            return jsonify({"error": "Quotation has no plan assigned."}), 400
        ok, msg = is_plan_available(plan)
        if not ok:
            return jsonify({"error": msg}), 400

        data = request.get_json(silent=True) or {}
        today = date.today()
        start = date.fromisoformat(data.get("start_date", str(today)))

        sub = Subscription(
            subscription_number=next_subscription_number(db),
            customer_id=q.customer_id,
            plan_id=q.plan_id,
            quotation_id=q.id,
            status="confirmed",
            start_date=start,
            next_billing_date=start,
            payment_terms=q.payment_terms,
            quantity=Decimal("1"),
            unit_price=plan.base_price,
            subtotal=q.subtotal,
            tax_amount=q.tax_amount,
            discount_amount=q.discount_amount,
            total_amount=q.grand_total,
            created_by=g.current_user.id,
        )
        # Copy lines from quotation
        for ql in q.lines:
            sl = SubscriptionLine(
                product_id=ql.product_id,
                variant_id=ql.variant_id,
                description=ql.description,
                quantity=ql.quantity,
                unit_price=ql.unit_price,
                discount_pct=ql.discount_pct,
                tax_pct=ql.tax_pct,
                subtotal=ql.subtotal,
                tax_amount=ql.tax_amount,
                total=ql.total,
            )
            sub.lines.append(sl)

        q.status = "confirmed"
        db.add(sub)
        db.flush()
        audit(db, g.current_user, "subscription.created_from_quotation", "subscription", sub.id, notes=sub.subscription_number)
        db.commit()
        db.refresh(sub)

        from app.routes.subscriptions import _subscription_dict
        return jsonify(_subscription_dict(sub)), 201
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


# ── Quotation Templates ──────────────────────────────────────────────────────

@quotations_bp.route("/templates", methods=["GET"])
@require_auth
def list_templates():
    db = SessionLocal()
    try:
        items = db.query(QuotationTemplate).filter(QuotationTemplate.is_active == True).all()
        return jsonify([{
            "id": t.id, "name": t.name, "plan_id": t.plan_id,
            "validity_days": t.validity_days, "payment_terms": t.payment_terms,
        } for t in items])
    finally:
        db.close()


@quotations_bp.route("/templates", methods=["POST"])
@require_admin_or_staff
def create_template():
    data = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        t = QuotationTemplate(
            name=data.get("name", ""),
            plan_id=data.get("plan_id"),
            validity_days=int(data.get("validity_days", 30)),
            payment_terms=data.get("payment_terms", "Due on receipt"),
            notes=data.get("notes"),
        )
        db.add(t)
        db.commit()
        db.refresh(t)
        return jsonify({"id": t.id, "name": t.name}), 201
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()
