"""Staff management routes (admin-only)."""
import re
from flask import Blueprint, request, jsonify, g
from app.database import SessionLocal
from app.models.user import User, Role
from app.utils.auth_middleware import require_admin, require_auth, audit
from app.utils.security import hash_password, validate_password_strength

staff_bp = Blueprint("staff", __name__, url_prefix="/api/staff")


def _staff_dict(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "full_name": u.full_name,
        "phone": u.phone,
        "role": u.role_name,
        "is_active": u.is_active,
        "last_login": u.last_login.isoformat() if u.last_login else None,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


@staff_bp.route("", methods=["GET"])
@require_admin
def list_staff():
    db = SessionLocal()
    try:
        q = db.query(User).join(Role).filter(Role.name.in_(["admin", "staff"]))
        search = request.args.get("search", "").strip()
        if search:
            q = q.filter(
                (User.first_name.ilike(f"%{search}%"))
                | (User.last_name.ilike(f"%{search}%"))
                | (User.email.ilike(f"%{search}%"))
            )
        items = q.order_by(User.created_at.desc()).all()
        return jsonify({"items": [_staff_dict(u) for u in items], "total": len(items)})
    finally:
        db.close()


@staff_bp.route("", methods=["POST"])
@require_admin
def create_staff():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    if not email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return jsonify({"error": "Valid email is required."}), 400

    password = data.get("password", "")
    ok, msg = validate_password_strength(password)
    if not ok:
        return jsonify({"error": msg}), 400

    role_name = data.get("role", "staff")
    if role_name not in ("staff", "admin"):
        return jsonify({"error": "Role must be 'staff' or 'admin'."}), 400

    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            return jsonify({"error": "Email already registered."}), 409
        role = db.query(Role).filter(Role.name == role_name).first()
        u = User(
            email=email,
            password_hash=hash_password(password),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            phone=data.get("phone"),
            role_id=role.id,
            is_active=True,
            is_verified=True,
        )
        db.add(u)
        audit(db, g.current_user, "staff.created", "user", u.id, notes=email)
        db.commit()
        db.refresh(u)
        return jsonify(_staff_dict(u)), 201
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@staff_bp.route("/<user_id>", methods=["PUT"])
@require_admin
def update_staff(user_id):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.id == user_id).first()
        if not u:
            return jsonify({"error": "User not found"}), 404
        data = request.get_json(silent=True) or {}
        for field in ("first_name", "last_name", "phone"):
            if field in data:
                setattr(u, field, data[field])
        if "is_active" in data:
            u.is_active = bool(data["is_active"])
        if "role" in data and data["role"] in ("staff", "admin"):
            role = db.query(Role).filter(Role.name == data["role"]).first()
            if role:
                u.role_id = role.id
        audit(db, g.current_user, "staff.updated", "user", user_id)
        db.commit()
        db.refresh(u)
        return jsonify(_staff_dict(u))
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@staff_bp.route("/<user_id>/deactivate", methods=["POST"])
@require_admin
def deactivate_staff(user_id):
    if user_id == g.current_user.id:
        return jsonify({"error": "Cannot deactivate yourself."}), 400
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.id == user_id).first()
        if not u:
            return jsonify({"error": "User not found"}), 404
        u.is_active = False
        audit(db, g.current_user, "staff.deactivated", "user", user_id)
        db.commit()
        return jsonify({"message": "Staff member deactivated."})
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()
