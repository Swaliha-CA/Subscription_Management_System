"""Customer management routes."""
from flask import Blueprint, request, jsonify, g

from app.database import SessionLocal
from app.models.customer import Customer
from app.models.user import User, Role
from app.utils.auth_middleware import require_auth, require_admin_or_staff, require_admin, audit
from app.utils.security import hash_password, validate_password_strength
from app.utils.numbering import next_customer_code

customers_bp = Blueprint("customers", __name__, url_prefix="/api/customers")


def _customer_dict(c: Customer) -> dict:
    u = c.user
    return {
        "id": c.id,
        "customer_code": c.customer_code,
        "user_id": c.user_id,
        "email": u.email if u else None,
        "first_name": u.first_name if u else None,
        "last_name": u.last_name if u else None,
        "full_name": u.full_name if u else None,
        "phone": u.phone if u else None,
        "company_name": c.company_name,
        "billing_address": c.billing_address,
        "shipping_address": c.shipping_address,
        "city": c.city,
        "state": c.state,
        "country": c.country,
        "pincode": c.pincode,
        "gstin": c.gstin,
        "pan": c.pan,
        "notes": c.notes,
        "is_active": c.is_active,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


@customers_bp.route("", methods=["GET"])
@require_admin_or_staff
def list_customers():
    db = SessionLocal()
    try:
        q = db.query(Customer).join(User)
        search = request.args.get("search", "").strip()
        if search:
            like = f"%{search}%"
            q = q.filter(
                (User.first_name.ilike(like))
                | (User.last_name.ilike(like))
                | (User.email.ilike(like))
                | (Customer.customer_code.ilike(like))
                | (Customer.company_name.ilike(like))
            )
        is_active = request.args.get("is_active")
        if is_active is not None:
            q = q.filter(Customer.is_active == (is_active.lower() == "true"))

        total = q.count()
        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(int(request.args.get("per_page", 20)), 100)
        items = q.order_by(Customer.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        return jsonify({
            "items": [_customer_dict(c) for c in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        })
    finally:
        db.close()


@customers_bp.route("/<customer_id>", methods=["GET"])
@require_auth
def get_customer(customer_id):
    db = SessionLocal()
    try:
        c = db.query(Customer).filter(Customer.id == customer_id).first()
        if not c:
            return jsonify({"error": "Customer not found"}), 404
        # Customers can only view themselves
        role = g.current_user.role_name
        if role == "customer" and (not c.user or c.user.id != g.current_user.id):
            return jsonify({"error": "Access denied"}), 403
        return jsonify(_customer_dict(c))
    finally:
        db.close()


@customers_bp.route("", methods=["POST"])
@require_admin_or_staff
def create_customer():
    data = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        import re
        email = (data.get("email") or "").strip().lower()
        if not email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return jsonify({"error": "Valid email is required."}), 400

        password = data.get("password") or "TempPass@123"
        ok, msg = validate_password_strength(password)
        if not ok:
            return jsonify({"error": msg}), 400

        if db.query(User).filter(User.email == email).first():
            return jsonify({"error": "Email already registered."}), 409

        customer_role = db.query(Role).filter(Role.name == "customer").first()
        user = User(
            email=email,
            password_hash=hash_password(password),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            phone=data.get("phone"),
            role_id=customer_role.id,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        db.flush()

        customer = Customer(
            user_id=user.id,
            customer_code=next_customer_code(db),
            company_name=data.get("company_name"),
            billing_address=data.get("billing_address"),
            shipping_address=data.get("shipping_address"),
            city=data.get("city"),
            state=data.get("state"),
            country=data.get("country", "India"),
            pincode=data.get("pincode"),
            gstin=data.get("gstin"),
            pan=data.get("pan"),
            notes=data.get("notes"),
        )
        db.add(customer)
        audit(db, g.current_user, "customer.created", "customer", customer.id, notes=email)
        db.commit()
        db.refresh(customer)
        return jsonify(_customer_dict(customer)), 201
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@customers_bp.route("/<customer_id>", methods=["PUT"])
@require_auth
def update_customer(customer_id):
    db = SessionLocal()
    try:
        c = db.query(Customer).filter(Customer.id == customer_id).first()
        if not c:
            return jsonify({"error": "Customer not found"}), 404

        role = g.current_user.role_name
        if role == "customer" and (not c.user or c.user.id != g.current_user.id):
            return jsonify({"error": "Access denied"}), 403

        data = request.get_json(silent=True) or {}
        u = c.user
        for field in ("first_name", "last_name", "phone"):
            if field in data:
                setattr(u, field, data[field])

        for field in ("company_name", "billing_address", "shipping_address",
                      "city", "state", "country", "pincode", "gstin", "pan", "notes"):
            if field in data:
                setattr(c, field, data[field])

        # Admin/staff can deactivate
        if role in ("admin", "staff") and "is_active" in data:
            c.is_active = bool(data["is_active"])
            u.is_active = bool(data["is_active"])

        audit(db, g.current_user, "customer.updated", "customer", customer_id)
        db.commit()
        db.refresh(c)
        return jsonify(_customer_dict(c))
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@customers_bp.route("/<customer_id>/summary", methods=["GET"])
@require_auth
def customer_summary(customer_id):
    """Quick stats for the customer portal home."""
    db = SessionLocal()
    try:
        c = db.query(Customer).filter(Customer.id == customer_id).first()
        if not c:
            return jsonify({"error": "Customer not found"}), 404
        role = g.current_user.role_name
        if role == "customer" and (not c.user or c.user.id != g.current_user.id):
            return jsonify({"error": "Access denied"}), 403

        from app.models.subscription import Subscription
        from app.models.invoice import Invoice
        from app.models.payment import Payment
        from decimal import Decimal

        subs = db.query(Subscription).filter(Subscription.customer_id == customer_id).all()
        active_subs = [s for s in subs if s.status == "active"]
        invoices = db.query(Invoice).filter(Invoice.customer_id == customer_id).all()
        outstanding = sum(float(i.outstanding_amount or 0) for i in invoices if i.status not in ("paid", "cancelled"))
        overdue = [i for i in invoices if i.is_overdue]

        return jsonify({
            "total_subscriptions": len(subs),
            "active_subscriptions": len(active_subs),
            "outstanding_amount": outstanding,
            "overdue_invoices": len(overdue),
            "recent_invoices": [
                {"id": i.id, "invoice_number": i.invoice_number, "grand_total": float(i.grand_total or 0),
                 "status": i.status, "due_date": str(i.due_date) if i.due_date else None}
                for i in sorted(invoices, key=lambda x: x.created_at or "", reverse=True)[:5]
            ],
        })
    finally:
        db.close()
