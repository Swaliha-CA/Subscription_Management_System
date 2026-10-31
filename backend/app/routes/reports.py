"""Analytics, dashboard, and reporting routes."""
from datetime import date, timedelta
from decimal import Decimal
from flask import Blueprint, request, jsonify, g
from sqlalchemy import func, and_
from app.database import SessionLocal
from app.utils.auth_middleware import require_admin, require_admin_or_staff

reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")


@reports_bp.route("/dashboard", methods=["GET"])
@require_admin_or_staff
def dashboard():
    db = SessionLocal()
    try:
        from app.models.customer import Customer
        from app.models.subscription import Subscription
        from app.models.invoice import Invoice
        from app.models.payment import Payment

        today = date.today()
        first_of_month = today.replace(day=1)
        year_start = today.replace(month=1, day=1)

        # ── Customers ──────────────────────────────────────────────────────
        total_customers = db.query(Customer).count()

        # ── Subscriptions ──────────────────────────────────────────────────
        all_subs = db.query(Subscription).all()
        total_subs = len(all_subs)
        active_subs = [s for s in all_subs if s.status == "active"]
        paused_subs = [s for s in all_subs if s.status == "paused"]
        new_this_month = [s for s in all_subs if s.created_at and s.created_at.date() >= first_of_month]

        # ── MRR / ARR ─────────────────────────────────────────────────────
        # Normalized: convert each active subscription's total to monthly equivalent
        mrr = Decimal("0")
        for s in active_subs:
            freq = s.plan.billing_frequency if s.plan else "monthly"
            amount = s.total_amount or Decimal("0")
            if freq == "daily":
                mrr += amount * 30
            elif freq == "weekly":
                mrr += amount * 4
            elif freq == "monthly":
                mrr += amount
            elif freq == "yearly":
                mrr += amount / 12
        arr = mrr * 12

        # ── Revenue ────────────────────────────────────────────────────────
        all_invoices = db.query(Invoice).all()
        billed_invoices = [i for i in all_invoices if i.status != "cancelled"]
        revenue_collected = sum(float(i.paid_amount or 0) for i in billed_invoices)
        outstanding_revenue = sum(float(i.outstanding_amount or 0) for i in billed_invoices)
        overdue_invoices = [i for i in billed_invoices if i.is_overdue]

        # Paid vs unpaid
        paid_count = sum(1 for i in billed_invoices if i.status == "paid")
        unpaid_count = sum(1 for i in billed_invoices if i.status in ("confirmed", "partially_paid", "overdue"))

        # ── Renewal rate ───────────────────────────────────────────────────
        renewed = sum(1 for s in all_subs if s.status == "active" and s.start_date and s.start_date < first_of_month)
        renewal_rate = round((renewed / total_subs * 100) if total_subs else 0, 1)

        # ── Monthly revenue trend (last 6 months) ─────────────────────────
        monthly_trend = []
        for i in range(5, -1, -1):
            month_start = (today.replace(day=1) - timedelta(days=i * 28)).replace(day=1)
            if i == 0:
                month_end = today
            else:
                next_month = month_start.replace(day=28) + timedelta(days=4)
                month_end = next_month - timedelta(days=next_month.day)
            month_invoices = [
                inv for inv in billed_invoices
                if inv.invoice_date and month_start <= inv.invoice_date <= month_end
            ]
            monthly_trend.append({
                "month": month_start.strftime("%b %Y"),
                "billed": float(sum(i.grand_total or 0 for i in month_invoices)),
                "collected": float(sum(i.paid_amount or 0 for i in month_invoices)),
            })

        # ── Subscription status distribution ──────────────────────────────
        status_counts = {}
        for s in all_subs:
            status_counts[s.status] = status_counts.get(s.status, 0) + 1

        # ── Upcoming renewals (next 30 days) ──────────────────────────────
        in_30 = today + timedelta(days=30)
        upcoming = [
            {
                "subscription_number": s.subscription_number,
                "customer_name": s.customer.user.full_name if s.customer and s.customer.user else "",
                "next_billing_date": str(s.next_billing_date),
                "amount": float(s.total_amount or 0),
            }
            for s in active_subs
            if s.next_billing_date and today <= s.next_billing_date <= in_30
        ]

        # ── Revenue by product ────────────────────────────────────────────
        rev_by_product = {}
        for inv in billed_invoices:
            for line in inv.lines:
                pname = line.product.name if line.product else "Other"
                rev_by_product[pname] = rev_by_product.get(pname, 0.0) + float(line.total or 0)
        revenue_by_product = [{"product": k, "revenue": v} for k, v in
                               sorted(rev_by_product.items(), key=lambda x: -x[1])[:8]]

        return jsonify({
            "total_customers": total_customers,
            "total_subscriptions": total_subs,
            "active_subscriptions": len(active_subs),
            "paused_subscriptions": len(paused_subs),
            "new_subscriptions_this_month": len(new_this_month),
            "mrr": float(mrr.quantize(Decimal("0.01"))),
            "arr": float(arr.quantize(Decimal("0.01"))),
            "revenue_collected": revenue_collected,
            "outstanding_revenue": outstanding_revenue,
            "overdue_invoices_count": len(overdue_invoices),
            "overdue_invoices_amount": float(sum(i.outstanding_amount or 0 for i in overdue_invoices)),
            "renewal_rate": renewal_rate,
            "paid_invoices": paid_count,
            "unpaid_invoices": unpaid_count,
            "monthly_revenue_trend": monthly_trend,
            "subscription_status_distribution": status_counts,
            "upcoming_renewals": sorted(upcoming, key=lambda x: x["next_billing_date"])[:10],
            "revenue_by_product": revenue_by_product,
            "as_of": str(today),
        })
    finally:
        db.close()


@reports_bp.route("/overdue", methods=["GET"])
@require_admin_or_staff
def overdue_report():
    db = SessionLocal()
    try:
        from app.models.invoice import Invoice
        today = date.today()
        q = db.query(Invoice).filter(
            Invoice.status.notin_(["paid", "cancelled"]),
            Invoice.due_date < today,
            Invoice.outstanding_amount > 0,
        )
        total = q.count()
        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(int(request.args.get("per_page", 20)), 100)
        items = q.order_by(Invoice.due_date.asc()).offset((page - 1) * per_page).limit(per_page).all()
        return jsonify({
            "items": [{
                "invoice_id": i.id,
                "invoice_number": i.invoice_number,
                "customer_name": i.customer.user.full_name if i.customer and i.customer.user else "",
                "customer_id": i.customer_id,
                "due_date": str(i.due_date),
                "outstanding_amount": float(i.outstanding_amount or 0),
                "overdue_days": (today - i.due_date).days,
                "status": i.status,
            } for i in items],
            "total": total, "page": page, "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        })
    finally:
        db.close()


@reports_bp.route("/mrr-arr", methods=["GET"])
@require_admin_or_staff
def mrr_arr():
    db = SessionLocal()
    try:
        from app.models.subscription import Subscription
        active_subs = db.query(Subscription).filter(Subscription.status == "active").all()
        mrr = Decimal("0")
        breakdown = []
        for s in active_subs:
            freq = s.plan.billing_frequency if s.plan else "monthly"
            amount = s.total_amount or Decimal("0")
            monthly = amount
            if freq == "daily":
                monthly = amount * 30
            elif freq == "weekly":
                monthly = amount * 4
            elif freq == "yearly":
                monthly = amount / 12
            mrr += monthly
            breakdown.append({
                "subscription_number": s.subscription_number,
                "customer": s.customer.user.full_name if s.customer and s.customer.user else "",
                "plan": s.plan.name if s.plan else "",
                "frequency": freq,
                "amount": float(amount),
                "monthly_equivalent": float(monthly.quantize(Decimal("0.01"))),
            })

        arr = mrr * 12
        return jsonify({
            "mrr": float(mrr.quantize(Decimal("0.01"))),
            "arr": float(arr.quantize(Decimal("0.01"))),
            "active_subscription_count": len(active_subs),
            "breakdown": breakdown,
        })
    finally:
        db.close()


@reports_bp.route("/subscriptions", methods=["GET"])
@require_admin_or_staff
def subscription_report():
    db = SessionLocal()
    try:
        from app.models.subscription import Subscription
        q = db.query(Subscription)
        status = request.args.get("status")
        if status:
            q = q.filter(Subscription.status == status)
        items = q.order_by(Subscription.created_at.desc()).limit(200).all()
        return jsonify([{
            "subscription_number": s.subscription_number,
            "customer": s.customer.user.full_name if s.customer and s.customer.user else "",
            "plan": s.plan.name if s.plan else "",
            "status": s.status,
            "start_date": str(s.start_date) if s.start_date else None,
            "next_billing_date": str(s.next_billing_date) if s.next_billing_date else None,
            "total_amount": float(s.total_amount or 0),
        } for s in items])
    finally:
        db.close()


@reports_bp.route("/revenue", methods=["GET"])
@require_admin_or_staff
def revenue_report():
    db = SessionLocal()
    try:
        from app.models.invoice import Invoice
        q = db.query(Invoice).filter(Invoice.status != "cancelled")
        date_from = request.args.get("from")
        date_to = request.args.get("to")
        if date_from:
            q = q.filter(Invoice.invoice_date >= date.fromisoformat(date_from))
        if date_to:
            q = q.filter(Invoice.invoice_date <= date.fromisoformat(date_to))
        items = q.order_by(Invoice.invoice_date.desc()).all()
        total_billed = sum(float(i.grand_total or 0) for i in items)
        total_collected = sum(float(i.paid_amount or 0) for i in items)
        total_outstanding = sum(float(i.outstanding_amount or 0) for i in items)
        return jsonify({
            "total_billed": total_billed,
            "total_collected": total_collected,
            "total_outstanding": total_outstanding,
            "invoice_count": len(items),
            "items": [{
                "invoice_number": i.invoice_number,
                "customer": i.customer.user.full_name if i.customer and i.customer.user else "",
                "date": str(i.invoice_date),
                "grand_total": float(i.grand_total or 0),
                "paid_amount": float(i.paid_amount or 0),
                "outstanding_amount": float(i.outstanding_amount or 0),
                "status": i.status,
            } for i in items],
        })
    finally:
        db.close()


@reports_bp.route("/audit-logs", methods=["GET"])
@require_admin
def audit_logs():
    db = SessionLocal()
    try:
        from app.models.audit import AuditLog
        q = db.query(AuditLog)
        entity_type = request.args.get("entity_type")
        if entity_type:
            q = q.filter(AuditLog.entity_type == entity_type)
        total = q.count()
        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(int(request.args.get("per_page", 50)), 200)
        items = q.order_by(AuditLog.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        return jsonify({
            "items": [{
                "id": l.id,
                "actor": l.actor_email,
                "action": l.action,
                "entity_type": l.entity_type,
                "entity_id": l.entity_id,
                "notes": l.notes,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            } for l in items],
            "total": total, "page": page, "per_page": per_page,
        })
    finally:
        db.close()


@reports_bp.route("/forecast", methods=["GET"])
@require_admin_or_staff
def revenue_forecast():
    """Estimate next 12 months of recurring revenue from active subscriptions."""
    db = SessionLocal()
    try:
        from app.models.subscription import Subscription
        active_subs = db.query(Subscription).filter(Subscription.status == "active").all()
        today = date.today()
        months = []
        for m in range(12):
            month_start = (today.replace(day=1) + timedelta(days=m * 31)).replace(day=1)
            projected = Decimal("0")
            for s in active_subs:
                freq = s.plan.billing_frequency if s.plan else "monthly"
                amount = s.total_amount or Decimal("0")
                if freq == "monthly":
                    projected += amount
                elif freq == "yearly" and month_start.month == (s.start_date.month if s.start_date else 1):
                    projected += amount
                elif freq == "weekly":
                    projected += amount * 4
                elif freq == "daily":
                    projected += amount * 30
            months.append({
                "month": month_start.strftime("%b %Y"),
                "projected_revenue": float(projected.quantize(Decimal("0.01"))),
                "is_forecast": True,
            })
        return jsonify({"forecast": months, "note": "Forecast based on current active subscriptions. Actual revenue may vary."})
    finally:
        db.close()
