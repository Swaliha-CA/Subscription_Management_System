"""Flask authentication and authorization helpers."""
from functools import wraps
from flask import request, jsonify, g
from sqlalchemy.orm import Session

from app.utils.security import decode_access_token
from app.database import SessionLocal


def _get_current_user(token: str):
    payload = decode_access_token(token)
    if not payload:
        return None
    db: Session = SessionLocal()
    try:
        from app.models.user import User
        from sqlalchemy.orm import joinedload
        user = (
            db.query(User)
            .options(joinedload(User.role), joinedload(User.customer))
            .filter(User.id == payload.get("sub"))
            .first()
        )
        if user and user.is_active:
            # Detach the object from this session but keep its loaded attributes
            db.expunge(user)
            # Eagerly accessed attributes are now in the instance dict
            return user
    finally:
        db.close()
    return None


def require_auth(f):
    """Decorator: any authenticated user."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        token = auth_header[7:]
        user = _get_current_user(token)
        if not user:
            return jsonify({"error": "Invalid or expired token"}), 401
        g.current_user = user
        return f(*args, **kwargs)
    return decorated


def require_role(*roles):
    """Decorator: authenticated user must have one of the specified role names."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return jsonify({"error": "Missing or invalid Authorization header"}), 401
            token = auth_header[7:]
            user = _get_current_user(token)
            if not user:
                return jsonify({"error": "Invalid or expired token"}), 401
            if user.role_name not in roles:
                return jsonify({"error": "Insufficient permissions"}), 403
            g.current_user = user
            return f(*args, **kwargs)
        return decorated
    return decorator


def require_admin(f):
    return require_role("admin")(f)


def require_admin_or_staff(f):
    return require_role("admin", "staff")(f)


def get_db():
    """Return a short-lived DB session for use inside a request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def audit(db: Session, actor, action: str, entity_type: str = None,
          entity_id: str = None, old_values=None, new_values=None, notes: str = None):
    """Record an audit log entry."""
    import json
    from app.models.audit import AuditLog
    log = AuditLog(
        actor_id=actor.id if actor else None,
        actor_email=actor.email if actor else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_values=json.dumps(old_values) if old_values else None,
        new_values=json.dumps(new_values) if new_values else None,
        ip_address=request.remote_addr if request else None,
        notes=notes,
    )
    db.add(log)
