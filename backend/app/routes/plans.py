"""Subscription Plan routes."""
from flask import Blueprint, request, jsonify, g
from app.database import SessionLocal
from app.models.plan import SubscriptionPlan, PlanPricing
from app.utils.auth_middleware import require_auth, require_admin_or_staff, require_admin, audit
from app.utils.billing_calc import is_plan_available

plans_bp = Blueprint("plans", __name__, url_prefix="/api/plans")


def _plan_dict(p: SubscriptionPlan) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "product_id": p.product_id,
        "product_name": p.product.name if p.product else None,
        "billing_frequency": p.billing_frequency,
        "base_price": float(p.base_price or 0),
        "min_quantity": p.min_quantity,
        "available_from": str(p.available_from) if p.available_from else None,
        "available_until": str(p.available_until) if p.available_until else None,
        "auto_close_on_expiry": p.auto_close_on_expiry,
        "allow_early_cancellation": p.allow_early_cancellation,
        "allow_pause": p.allow_pause,
        "allow_renewal": p.allow_renewal,
        "description": p.description,
        "is_active": p.is_active,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


@plans_bp.route("", methods=["GET"])
@require_auth
def list_plans():
    db = SessionLocal()
    try:
        q = db.query(SubscriptionPlan)
        search = request.args.get("search", "").strip()
        if search:
            q = q.filter(SubscriptionPlan.name.ilike(f"%{search}%"))
        is_active = request.args.get("is_active")
        if is_active is not None:
            q = q.filter(SubscriptionPlan.is_active == (is_active.lower() != "false"))
        product_id = request.args.get("product_id")
        if product_id:
            q = q.filter(SubscriptionPlan.product_id == product_id)

        total = q.count()
        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(int(request.args.get("per_page", 20)), 100)
        items = q.order_by(SubscriptionPlan.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        return jsonify({
            "items": [_plan_dict(p) for p in items],
            "total": total, "page": page, "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        })
    finally:
        db.close()


@plans_bp.route("/<plan_id>", methods=["GET"])
@require_auth
def get_plan(plan_id):
    db = SessionLocal()
    try:
        p = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
        if not p:
            return jsonify({"error": "Plan not found"}), 404
        return jsonify(_plan_dict(p))
    finally:
        db.close()


@plans_bp.route("", methods=["POST"])
@require_admin_or_staff
def create_plan():
    data = request.get_json(silent=True) or {}
    if not data.get("name") or not data.get("product_id"):
        return jsonify({"error": "Name and product_id are required."}), 400

    db = SessionLocal()
    try:
        from decimal import Decimal
        from datetime import date
        p = SubscriptionPlan(
            name=data["name"].strip(),
            product_id=data["product_id"],
            billing_frequency=data.get("billing_frequency", "monthly"),
            base_price=Decimal(str(data.get("base_price", 0))),
            min_quantity=int(data.get("min_quantity", 1)),
            description=data.get("description"),
            auto_close_on_expiry=bool(data.get("auto_close_on_expiry", True)),
            allow_early_cancellation=bool(data.get("allow_early_cancellation", True)),
            allow_pause=bool(data.get("allow_pause", True)),
            allow_renewal=bool(data.get("allow_renewal", True)),
        )
        if data.get("available_from"):
            p.available_from = date.fromisoformat(data["available_from"])
        if data.get("available_until"):
            p.available_until = date.fromisoformat(data["available_until"])

        db.add(p)
        audit(db, g.current_user, "plan.created", "plan", p.id, notes=p.name)
        db.commit()
        db.refresh(p)
        return jsonify(_plan_dict(p)), 201
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@plans_bp.route("/<plan_id>", methods=["PUT"])
@require_admin_or_staff
def update_plan(plan_id):
    db = SessionLocal()
    try:
        p = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
        if not p:
            return jsonify({"error": "Plan not found"}), 404
        data = request.get_json(silent=True) or {}
        from decimal import Decimal
        from datetime import date

        for field in ("name", "billing_frequency", "description"):
            if field in data:
                setattr(p, field, data[field])
        for field in ("base_price",):
            if field in data:
                setattr(p, field, Decimal(str(data[field])))
        for field in ("min_quantity",):
            if field in data:
                setattr(p, field, int(data[field]))
        for field in ("auto_close_on_expiry", "allow_early_cancellation",
                      "allow_pause", "allow_renewal", "is_active"):
            if field in data:
                setattr(p, field, bool(data[field]))
        if "available_from" in data:
            p.available_from = date.fromisoformat(data["available_from"]) if data["available_from"] else None
        if "available_until" in data:
            p.available_until = date.fromisoformat(data["available_until"]) if data["available_until"] else None

        audit(db, g.current_user, "plan.updated", "plan", plan_id)
        db.commit()
        db.refresh(p)
        return jsonify(_plan_dict(p))
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()
