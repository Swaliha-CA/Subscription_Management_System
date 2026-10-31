"""Subscription lifecycle routes."""
from datetime import date, datetime, timezone
from decimal import Decimal
from flask import Blueprint, request, jsonify, g
from app.database import SessionLocal
from app.models.subscription import Subscription, SubscriptionLine
from app.utils.auth_middleware import require_auth, require_admin_or_staff, require_admin, audit
from app.utils.billing_calc import next_billing_date, is_plan_available

subscriptions_bp = Blueprint("subscriptions", __name__, url_prefix="/api/subscriptions")


def _subscription_dict(s: Subscription) -> dict:
    return {
        "id": s.id,
        "subscription_number": s.subscription_number,
        "customer_id": s.customer_id,
        "customer_name": s.customer.user.full_name if s.customer and s.customer.user else None,
        "plan_id": s.plan_id,
        "plan_name": s.plan.name if s.plan else None,
        "billing_frequency": s.plan.billing_frequency if s.plan else None,
        "quotation_id": s.quotation_id,
        "status": s.status,
        "start_date": str(s.start_date) if s.start_date else None,
        "expiry_date": str(s.expiry_date) if s.expiry_date else None,
        "next_billing_date": str(s.next_billing_date) if s.next_billing_date else None,
        "payment_terms": s.payment_terms,
        "quantity": float(s.quantity or 1),
        "unit_price": float(s.unit_price or 0),
        "tax_pct": float(s.tax_pct or 0),
        "discount_pct": float(s.discount_pct or 0),
        "subtotal": float(s.subtotal or 0),
        "tax_amount": float(s.tax_amount or 0),
        "discount_amount": float(s.discount_amount or 0),
        "total_amount": float(s.total_amount or 0),
        "notes": s.notes,
        "paused_at": s.paused_at.isoformat() if s.paused_at else None,
        "resumed_at": s.resumed_at.isoformat() if s.resumed_at else None,
        "closed_at": s.closed_at.isoformat() if s.closed_at else None,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "lines": [_line_dict(l) for l in (s.lines or [])],
    }


def _line_dict(l: SubscriptionLine) -> dict:
    return {
        "id": l.id,
        "product_id": l.product_id,
        "product_name": l.product.name if l.product else None,
        "variant_id": l.variant_id,
        "variant_name": l.variant.name if l.variant else None,
        "quantity": float(l.quantity or 1),
        "unit_price": float(l.unit_price or 0),
        "discount_pct": float(l.discount_pct or 0),
        "tax_pct": float(l.tax_pct or 0),
        "subtotal": float(l.subtotal or 0),
        "tax_amount": float(l.tax_amount or 0),
        "total": float(l.total or 0),
    }


@subscriptions_bp.route("", methods=["GET"])
@require_auth
def list_subscriptions():
    db = SessionLocal()
    try:
        q = db.query(Subscription)
        role = g.current_user.role_name

        # Customers can only see their own
        if role == "customer":
            if not g.current_user.customer:
                return jsonify({"items": [], "total": 0})
            q = q.filter(Subscription.customer_id == g.current_user.customer.id)
        else:
            customer_id = request.args.get("customer_id")
            if customer_id:
                q = q.filter(Subscription.customer_id == customer_id)

        status = request.args.get("status")
        if status:
            q = q.filter(Subscription.status == status)
        plan_id = request.args.get("plan_id")
        if plan_id:
            q = q.filter(Subscription.plan_id == plan_id)
        search = request.args.get("search", "").strip()
        if search:
            q = q.filter(Subscription.subscription_number.ilike(f"%{search}%"))

        total = q.count()
        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(int(request.args.get("per_page", 20)), 100)
        items = q.order_by(Subscription.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        return jsonify({
            "items": [_subscription_dict(s) for s in items],
            "total": total, "page": page, "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        })
    finally:
        db.close()


@subscriptions_bp.route("/<sub_id>", methods=["GET"])
@require_auth
def get_subscription(sub_id):
    db = SessionLocal()
    try:
        s = db.query(Subscription).filter(Subscription.id == sub_id).first()
        if not s:
            return jsonify({"error": "Subscription not found"}), 404
        role = g.current_user.role_name
        if role == "customer":
            if not s.customer or not s.customer.user or s.customer.user.id != g.current_user.id:
                return jsonify({"error": "Access denied"}), 403
        return jsonify(_subscription_dict(s))
    finally:
        db.close()


@subscriptions_bp.route("", methods=["POST"])
@require_admin_or_staff
def create_subscription():
    """Create a subscription directly (without a quotation)."""
    data = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        from app.models.plan import SubscriptionPlan
        from app.utils.numbering import next_subscription_number
        from app.utils.billing_calc import calculate_line_totals, calculate_document_totals

        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == data.get("plan_id")).first()
        if not plan:
            return jsonify({"error": "Plan not found"}), 404
        ok, msg = is_plan_available(plan)
        if not ok:
            return jsonify({"error": msg}), 400

        today = date.today()
        start = date.fromisoformat(data.get("start_date", str(today)))

        s = Subscription(
            subscription_number=next_subscription_number(db),
            customer_id=data["customer_id"],
            plan_id=plan.id,
            status="confirmed",
            start_date=start,
            next_billing_date=start,
            payment_terms=data.get("payment_terms", "Due on receipt"),
            quantity=Decimal(str(data.get("quantity", 1))),
            unit_price=Decimal(str(data.get("unit_price", float(plan.base_price)))),
            tax_pct=Decimal(str(data.get("tax_pct", 0))),
            discount_pct=Decimal(str(data.get("discount_pct", 0))),
            notes=data.get("notes"),
            created_by=g.current_user.id,
        )
        # Compute totals
        result = calculate_line_totals(s.quantity, s.unit_price, s.discount_pct, s.tax_pct)
        s.subtotal = result["subtotal"]
        s.tax_amount = result["tax_amount"]
        s.discount_amount = result["discount_amount"]
        s.total_amount = result["total"]

        db.add(s)
        db.flush()

        for ld in data.get("lines", []):
            calc = calculate_line_totals(
                Decimal(str(ld.get("quantity", 1))),
                Decimal(str(ld.get("unit_price", 0))),
                Decimal(str(ld.get("discount_pct", 0))),
                Decimal(str(ld.get("tax_pct", 0))),
            )
            sl = SubscriptionLine(
                subscription_id=s.id,
                product_id=ld["product_id"],
                variant_id=ld.get("variant_id"),
                description=ld.get("description"),
                quantity=Decimal(str(ld.get("quantity", 1))),
                unit_price=Decimal(str(ld.get("unit_price", 0))),
                discount_pct=Decimal(str(ld.get("discount_pct", 0))),
                tax_pct=Decimal(str(ld.get("tax_pct", 0))),
                subtotal=calc["subtotal"],
                tax_amount=calc["tax_amount"],
                total=calc["total"],
            )
            db.add(sl)

        audit(db, g.current_user, "subscription.created", "subscription", s.id, notes=s.subscription_number)
        db.commit()
        db.refresh(s)
        return jsonify(_subscription_dict(s)), 201
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


def _transition(sub_id: str, new_status: str, action_name: str,
                allowed_from: list, extra_fn=None):
    db = SessionLocal()
    try:
        s = db.query(Subscription).filter(Subscription.id == sub_id).first()
        if not s:
            return jsonify({"error": "Subscription not found"}), 404
        if s.status not in allowed_from:
            return jsonify({"error": f"Cannot {action_name} from '{s.status}' status."}), 400

        s.status = new_status
        if extra_fn:
            extra_fn(s, db)

        audit(db, g.current_user, f"subscription.{action_name}", "subscription", sub_id,
              old_values={"status": s.status}, new_values={"status": new_status})
        db.commit()
        db.refresh(s)
        return jsonify(_subscription_dict(s))
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@subscriptions_bp.route("/<sub_id>/activate", methods=["POST"])
@require_admin_or_staff
def activate(sub_id):
    def _activate_extra(s, db):
        s.start_date = s.start_date or date.today()
        s.next_billing_date = s.start_date
    return _transition(sub_id, "active", "activated", ["confirmed"], _activate_extra)


@subscriptions_bp.route("/<sub_id>/pause", methods=["POST"])
@require_admin_or_staff
def pause(sub_id):
    db = SessionLocal()
    try:
        s = db.query(Subscription).filter(Subscription.id == sub_id).first()
        if not s:
            return jsonify({"error": "Subscription not found"}), 404
        if s.status != "active":
            return jsonify({"error": "Only active subscriptions can be paused."}), 400
        if not s.plan.allow_pause:
            return jsonify({"error": "This plan does not allow pausing."}), 400
        s.status = "paused"
        s.paused_at = datetime.now(timezone.utc)
        audit(db, g.current_user, "subscription.paused", "subscription", sub_id)
        db.commit()
        db.refresh(s)
        return jsonify(_subscription_dict(s))
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@subscriptions_bp.route("/<sub_id>/resume", methods=["POST"])
@require_admin_or_staff
def resume(sub_id):
    def _resume_extra(s, db):
        s.resumed_at = datetime.now(timezone.utc)
        # Reset next billing date to today
        s.next_billing_date = date.today()
    return _transition(sub_id, "active", "resumed", ["paused"], _resume_extra)


@subscriptions_bp.route("/<sub_id>/renew", methods=["POST"])
@require_admin_or_staff
def renew(sub_id):
    db = SessionLocal()
    try:
        s = db.query(Subscription).filter(Subscription.id == sub_id).first()
        if not s:
            return jsonify({"error": "Subscription not found"}), 404
        if not s.plan.allow_renewal:
            return jsonify({"error": "This plan does not allow renewal."}), 400
        if s.status not in ("active", "expired", "closed"):
            return jsonify({"error": "Subscription cannot be renewed in its current state."}), 400

        data = request.get_json(silent=True) or {}
        new_start = date.fromisoformat(data.get("start_date", str(date.today())))
        s.start_date = new_start
        s.next_billing_date = new_start
        s.expiry_date = None
        s.status = "active"
        s.closed_at = None
        audit(db, g.current_user, "subscription.renewed", "subscription", sub_id)
        db.commit()
        db.refresh(s)
        return jsonify(_subscription_dict(s))
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@subscriptions_bp.route("/<sub_id>/close", methods=["POST"])
@require_admin_or_staff
def close_subscription(sub_id):
    def _close_extra(s, db):
        s.closed_at = datetime.now(timezone.utc)
    return _transition(sub_id, "closed", "closed", ["active", "paused", "confirmed", "expired"], _close_extra)


@subscriptions_bp.route("/<sub_id>/cancel", methods=["POST"])
@require_admin_or_staff
def cancel_subscription(sub_id):
    db = SessionLocal()
    try:
        s = db.query(Subscription).filter(Subscription.id == sub_id).first()
        if not s:
            return jsonify({"error": "Subscription not found"}), 404
        if s.status == "closed":
            return jsonify({"error": "Already closed."}), 400
        if s.status == "active" and not s.plan.allow_early_cancellation:
            return jsonify({"error": "This plan does not allow early cancellation."}), 400
        s.status = "closed"
        s.closed_at = datetime.now(timezone.utc)
        audit(db, g.current_user, "subscription.cancelled", "subscription", sub_id)
        db.commit()
        db.refresh(s)
        return jsonify(_subscription_dict(s))
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()
