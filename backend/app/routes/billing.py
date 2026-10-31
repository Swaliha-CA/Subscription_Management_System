"""Billing engine HTTP routes."""
from flask import Blueprint, request, jsonify, g
from app.utils.auth_middleware import require_admin
from app.services.billing_engine import run_billing, get_billing_due_count
from app.database import SessionLocal

billing_bp = Blueprint("billing", __name__, url_prefix="/api/billing")


@billing_bp.route("/run", methods=["POST"])
@require_admin
def manual_billing_run():
    result = run_billing(run_type="manual", actor_id=g.current_user.id)
    return jsonify(result)


@billing_bp.route("/due-count", methods=["GET"])
@require_admin
def due_count():
    return jsonify({"due_count": get_billing_due_count()})


@billing_bp.route("/logs", methods=["GET"])
@require_admin
def billing_logs():
    from app.models.billing_log import BillingExecutionLog
    db = SessionLocal()
    try:
        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(int(request.args.get("per_page", 20)), 100)
        q = db.query(BillingExecutionLog).order_by(BillingExecutionLog.started_at.desc())
        total = q.count()
        items = q.offset((page - 1) * per_page).limit(per_page).all()
        return jsonify({
            "items": [{
                "id": l.id,
                "run_type": l.run_type,
                "started_at": l.started_at.isoformat() if l.started_at else None,
                "completed_at": l.completed_at.isoformat() if l.completed_at else None,
                "subscriptions_due": l.subscriptions_due,
                "invoices_generated": l.invoices_generated,
                "invoices_failed": l.invoices_failed,
                "invoices_skipped": l.invoices_skipped,
                "total_billed": float(l.total_billed or 0),
                "status": l.status,
            } for l in items],
            "total": total, "page": page, "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        })
    finally:
        db.close()
