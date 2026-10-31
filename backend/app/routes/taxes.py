"""Tax management routes."""
from flask import Blueprint, request, jsonify, g
from app.database import SessionLocal
from app.models.tax import Tax
from app.utils.auth_middleware import require_auth, require_admin

taxes_bp = Blueprint("taxes", __name__, url_prefix="/api/taxes")


def _tax_dict(t: Tax) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "percentage": float(t.percentage or 0),
        "tax_type": t.tax_type,
        "description": t.description,
        "active_from": str(t.active_from) if t.active_from else None,
        "active_until": str(t.active_until) if t.active_until else None,
        "is_active": t.is_active,
    }


@taxes_bp.route("", methods=["GET"])
@require_auth
def list_taxes():
    db = SessionLocal()
    try:
        items = db.query(Tax).filter(Tax.is_active == True).all()
        return jsonify([_tax_dict(t) for t in items])
    finally:
        db.close()


@taxes_bp.route("", methods=["POST"])
@require_admin
def create_tax():
    data = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        from decimal import Decimal
        t = Tax(
            name=data.get("name", ""),
            percentage=Decimal(str(data.get("percentage", 0))),
            tax_type=data.get("tax_type", "GST"),
            description=data.get("description"),
        )
        if data.get("active_from"):
            from datetime import date
            t.active_from = date.fromisoformat(data["active_from"])
        if data.get("active_until"):
            from datetime import date
            t.active_until = date.fromisoformat(data["active_until"])
        db.add(t)
        db.commit()
        db.refresh(t)
        return jsonify(_tax_dict(t)), 201
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@taxes_bp.route("/<tax_id>", methods=["PUT"])
@require_admin
def update_tax(tax_id):
    db = SessionLocal()
    try:
        t = db.query(Tax).filter(Tax.id == tax_id).first()
        if not t:
            return jsonify({"error": "Tax not found"}), 404
        data = request.get_json(silent=True) or {}
        from decimal import Decimal
        for field in ("name", "tax_type", "description"):
            if field in data:
                setattr(t, field, data[field])
        if "percentage" in data:
            t.percentage = Decimal(str(data["percentage"]))
        if "is_active" in data:
            t.is_active = bool(data["is_active"])
        db.commit()
        db.refresh(t)
        return jsonify(_tax_dict(t))
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()
