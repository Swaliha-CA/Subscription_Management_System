"""Authentication routes: register, login, logout, forgot/reset password."""
import re
from datetime import datetime, timedelta, timezone

from flask import Blueprint, request, jsonify, g

from app.database import SessionLocal
from app.models.user import User, Role
from app.models.customer import Customer
from app.utils.security import (
    hash_password, verify_password, create_access_token,
    validate_password_strength, generate_reset_token,
)
from app.utils.email_service import send_password_reset
from app.utils.auth_middleware import require_auth, audit
from app.utils.numbering import next_customer_code

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password", "")
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    phone = (data.get("phone") or "").strip()

    if not email or not EMAIL_RE.match(email):
        return jsonify({"error": "Invalid email address."}), 400
    if not first_name or not last_name:
        return jsonify({"error": "First and last name are required."}), 400

    ok, msg = validate_password_strength(password)
    if not ok:
        return jsonify({"error": msg}), 400

    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            return jsonify({"error": "Email is already registered."}), 409

        customer_role = db.query(Role).filter(Role.name == "customer").first()
        if not customer_role:
            return jsonify({"error": "System not initialised. Run seed first."}), 500

        user = User(
            email=email,
            password_hash=hash_password(password),
            first_name=first_name,
            last_name=last_name,
            phone=phone or None,
            role_id=customer_role.id,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        db.flush()

        customer = Customer(
            user_id=user.id,
            customer_code=next_customer_code(db),
        )
        db.add(customer)
        audit(db, None, "user.registered", "user", user.id, notes=email)
        db.commit()
        db.refresh(user)

        token = create_access_token({"sub": user.id, "role": "customer", "email": user.email})
        return jsonify({
            "access_token": token,
            "token_type": "bearer",
            "user": _user_dict(user),
        }), 201
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password", "")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user or not verify_password(password, user.password_hash):
            return jsonify({"error": "Invalid email or password."}), 401
        if not user.is_active:
            return jsonify({"error": "Account is deactivated. Contact support."}), 403

        user.last_login = datetime.now(timezone.utc)
        audit(db, user, "user.login", "user", user.id)
        db.commit()

        token = create_access_token({
            "sub": user.id,
            "role": user.role_name,
            "email": user.email,
        })
        return jsonify({
            "access_token": token,
            "token_type": "bearer",
            "user": _user_dict(user),
        })
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@auth_bp.route("/me", methods=["GET"])
@require_auth
def me():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == g.current_user.id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify(_user_dict(user))
    finally:
        db.close()


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        # Always return 200 to prevent email enumeration
        if user and user.is_active:
            token = generate_reset_token()
            user.password_reset_token = token
            user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
            db.commit()
            result = send_password_reset(user.email, token)
            # In dev mode, log the token for demo convenience
            if result.get("status") == "dev_mode":
                return jsonify({
                    "message": "Password reset link created (dev mode).",
                    "dev_token": token,
                    "dev_file": result.get("file"),
                })
        return jsonify({"message": "If that email is registered, a reset link has been sent."})
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    new_password = data.get("password", "")

    ok, msg = validate_password_strength(new_password)
    if not ok:
        return jsonify({"error": msg}), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.password_reset_token == token).first()
        if not user:
            return jsonify({"error": "Invalid or expired reset token."}), 400
        if user.password_reset_expires < datetime.now(timezone.utc):
            return jsonify({"error": "Reset token has expired."}), 400

        user.password_hash = hash_password(new_password)
        user.password_reset_token = None
        user.password_reset_expires = None
        audit(db, user, "user.password_reset", "user", user.id)
        db.commit()
        return jsonify({"message": "Password updated successfully."})
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@auth_bp.route("/change-password", methods=["POST"])
@require_auth
def change_password():
    data = request.get_json(silent=True) or {}
    current_pwd = data.get("current_password", "")
    new_pwd = data.get("new_password", "")

    ok, msg = validate_password_strength(new_pwd)
    if not ok:
        return jsonify({"error": msg}), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == g.current_user.id).first()
        if not verify_password(current_pwd, user.password_hash):
            return jsonify({"error": "Current password is incorrect."}), 400
        user.password_hash = hash_password(new_pwd)
        audit(db, user, "user.password_changed", "user", user.id)
        db.commit()
        return jsonify({"message": "Password changed successfully."})
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


def _user_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.full_name,
        "phone": user.phone,
        "role": user.role_name,
        "is_active": user.is_active,
        "avatar_url": user.avatar_url,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "customer_id": user.customer.id if user.customer else None,
    }
