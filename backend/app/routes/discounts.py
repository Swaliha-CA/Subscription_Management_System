"""Discount management routes — admin-only creation."""
from datetime import date
from decimal import Decimal
from flask import Blueprint, request, jsonify, g
from app.database import SessionLocal
from app.models.discount import Discount, DiscountApplication
from app.models.product import Product
from app.utils.auth_middleware import require_auth, require_admin_or_staff, require_admin, audit

discounts_bp = Blueprint("discounts", __name__, url_prefix="/api/discounts")


def _discount_dict(d: Discount) -> dict:
    return {
        "id": d.id,
        "name": d.name,
        "code": d.code,
        "discount_type": d.discount_type,
        "value": float(d.value or 0),
        "min_purchase_amount": float(d.min_purchase_amount or 0),
        "min_quantity": float(d.min_quantity or 1),
        "applicable_to_subscription": d.applicable_to_subscription,
        "start_date": str(d.start_date) if d.start_date else None,
        "end_date": str(d.end_date) if d.end_date else None,
        "max_usage_count": d.max_usage_count,
        "current_usage_count": d.current_usage_count,
        "is_active": d.is_active,
        "notes": d.notes,
        "product_ids": [p.id for p in d.applicable_products],
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


@discounts_bp.route("", methods=["GET"])
@require_admin_or_staff
def list_discounts():
    db = SessionLocal()
    try:
        q = db.query(Discount)
        is_active = request.args.get("is_active")
        if is_active is not None:
            q = q.filter(Discount.is_active == (is_active.lower() != "false"))
        items = q.order_by(Discount.created_at.desc()).all()
        return jsonify({"items": [_discount_dict(d) for d in items], "total": len(items)})
    finally:
        db.close()


@discounts_bp.route("/<discount_id>", methods=["GET"])
@require_admin_or_staff
def get_discount(discount_id):
    db = SessionLocal()
    try:
        d = db.query(Discount).filter(Discount.id == discount_id).first()
        if not d:
            return jsonify({"error": "Discount not found"}), 404
        return jsonify(_discount_dict(d))
    finally:
        db.close()


@discounts_bp.route("", methods=["POST"])
@require_admin
def create_discount():
    data = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        d = Discount(
            name=data.get("name", ""),
            code=data.get("code") or None,
            discount_type=data.get("discount_type", "percentage"),
            value=Decimal(str(data.get("value", 0))),
            min_purchase_amount=Decimal(str(data.get("min_purchase_amount", 0))),
            min_quantity=Decimal(str(data.get("min_quantity", 1))),
            applicable_to_subscription=bool(data.get("applicable_to_subscription", True)),
            max_usage_count=int(data["max_usage_count"]) if data.get("max_usage_count") is not None else None,
            notes=data.get("notes"),
            created_by=g.current_user.id,
        )
        if data.get("start_date"):
            d.start_date = date.fromisoformat(data["start_date"])
        if data.get("end_date"):
            d.end_date = date.fromisoformat(data["end_date"])
        for pid in data.get("product_ids", []):
            prod = db.query(Product).filter(Product.id == pid).first()
            if prod:
                d.applicable_products.append(prod)

        db.add(d)
        audit(db, g.current_user, "discount.created", "discount", d.id, notes=d.name)
        db.commit()
        db.refresh(d)
        return jsonify(_discount_dict(d)), 201
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@discounts_bp.route("/<discount_id>", methods=["PUT"])
@require_admin
def update_discount(discount_id):
    db = SessionLocal()
    try:
        d = db.query(Discount).filter(Discount.id == discount_id).first()
        if not d:
            return jsonify({"error": "Discount not found"}), 404
        data = request.get_json(silent=True) or {}
        for field in ("name", "code", "discount_type", "notes"):
            if field in data:
                setattr(d, field, data[field] or None)
        for field in ("value", "min_purchase_amount", "min_quantity"):
            if field in data:
                setattr(d, field, Decimal(str(data[field])))
        for field in ("applicable_to_subscription", "is_active"):
            if field in data:
                setattr(d, field, bool(data[field]))
        if "max_usage_count" in data:
            d.max_usage_count = int(data["max_usage_count"]) if data["max_usage_count"] is not None else None
        if "start_date" in data:
            d.start_date = date.fromisoformat(data["start_date"]) if data["start_date"] else None
        if "end_date" in data:
            d.end_date = date.fromisoformat(data["end_date"]) if data["end_date"] else None

        audit(db, g.current_user, "discount.updated", "discount", discount_id)
        db.commit()
        db.refresh(d)
        return jsonify(_discount_dict(d))
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@discounts_bp.route("/validate", methods=["POST"])
@require_auth
def validate_discount():
    """Check if a discount code is applicable for a given amount/quantity."""
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip().upper()
    amount = Decimal(str(data.get("amount", 0)))
    quantity = Decimal(str(data.get("quantity", 1)))
    today = date.today()

    db = SessionLocal()
    try:
        d = db.query(Discount).filter(
            Discount.code == code,
            Discount.is_active == True,
        ).first()

        if not d:
            return jsonify({"valid": False, "reason": "Discount code not found or inactive."}), 200
        if d.start_date and today < d.start_date:
            return jsonify({"valid": False, "reason": "Discount is not yet active."}), 200
        if d.end_date and today > d.end_date:
            return jsonify({"valid": False, "reason": "Discount has expired."}), 200
        if d.max_usage_count is not None and d.current_usage_count >= d.max_usage_count:
            return jsonify({"valid": False, "reason": "Discount usage limit reached."}), 200
        if amount < d.min_purchase_amount:
            return jsonify({"valid": False, "reason": f"Minimum purchase amount ₹{d.min_purchase_amount} required."}), 200
        if quantity < d.min_quantity:
            return jsonify({"valid": False, "reason": f"Minimum quantity {d.min_quantity} required."}), 200

        if d.discount_type == "percentage":
            savings = (amount * d.value / 100).quantize(Decimal("0.01"))
        else:
            savings = min(d.value, amount)

        return jsonify({
            "valid": True,
            "discount_id": d.id,
            "discount_name": d.name,
            "discount_type": d.discount_type,
            "value": float(d.value),
            "savings": float(savings),
        })
    finally:
        db.close()
