"""
Seed script — creates demo data for hackathon demonstration.
Run: py seed.py
Idempotent: safe to run multiple times (skips existing records).
"""
from datetime import date, timedelta
from decimal import Decimal

from app.database import SessionLocal, init_db
from app.models.user import User, Role
from app.models.customer import Customer
from app.models.product import Product, ProductVariant
from app.models.tax import Tax
from app.models.plan import SubscriptionPlan
from app.models.quotation import QuotationTemplate, Quotation, QuotationLine
from app.models.subscription import Subscription, SubscriptionLine, BillingCycle
from app.models.invoice import Invoice, InvoiceLine
from app.models.payment import Payment, PaymentAllocation
from app.models.discount import Discount
from app.utils.security import hash_password
from app.utils.billing_calc import next_billing_date, cycle_end_date, calculate_line_totals, calculate_document_totals
from app.utils.numbering import (
    next_customer_code, next_quotation_number, next_subscription_number,
    next_invoice_number, next_payment_number,
)

print("Initialising database...")
init_db()
db = SessionLocal()


def _get_or_create_role(name: str, description: str) -> Role:
    r = db.query(Role).filter(Role.name == name).first()
    if not r:
        r = Role(name=name, description=description)
        db.add(r)
        db.flush()
        print(f"  Role: {name}")
    return r


def _get_or_create_user(email: str, role: Role, **kwargs) -> User:
    u = db.query(User).filter(User.email == email).first()
    if not u:
        u = User(email=email, role_id=role.id, is_active=True, is_verified=True, **kwargs)
        db.add(u)
        db.flush()
        print(f"  User: {email} ({role.name})")
    return u


# ── 1. Roles ─────────────────────────────────────────────────────────────────
print("\n[1/10] Roles")
admin_role = _get_or_create_role("admin", "Full system access")
staff_role = _get_or_create_role("staff", "Operational access")
customer_role = _get_or_create_role("customer", "Self-service portal")
db.commit()

# ── 2. Admin & Staff users ───────────────────────────────────────────────────
print("\n[2/10] Admin & Staff")
admin_user = _get_or_create_user(
    "admin@brightloop.in", admin_role,
    first_name="Arjun", last_name="Menon",
    password_hash=hash_password("Admin@12345"),
)
staff1 = _get_or_create_user(
    "staff1@brightloop.in", staff_role,
    first_name="Priya", last_name="Nair",
    password_hash=hash_password("Staff@12345"),
)
staff2 = _get_or_create_user(
    "staff2@brightloop.in", staff_role,
    first_name="Rahul", last_name="Kumar",
    password_hash=hash_password("Staff@12345"),
)
db.commit()

# ── 3. Customers ─────────────────────────────────────────────────────────────
CUSTOMERS_DATA = [
    ("alice@techvision.in", "Alice", "Thomas", "TechVision Pvt Ltd", "Kochi"),
    ("bob@greenwave.in", "Bob", "Mathew", "GreenWave Solutions", "Bangalore"),
    ("carol@swiftworks.in", "Carol", "Jose", "SwiftWorks Inc", "Chennai"),
    ("david@cloudnine.in", "David", "Pillai", "CloudNine Technologies", "Hyderabad"),
    ("eva@nexussoft.in", "Eva", "Sharma", "NexusSoft Ltd", "Mumbai"),
    ("frank@pixelcraft.in", "Frank", "Iyer", "PixelCraft Studios", "Delhi"),
    ("grace@datasync.in", "Grace", "Mohan", "DataSync Analytics", "Pune"),
    ("henry@loopback.in", "Henry", "Raj", "Loopback Systems", "Kochi"),
    ("iris@brightnode.in", "Iris", "Varma", "BrightNode Corp", "Trivandrum"),
    ("james@codebridge.in", "James", "Kurian", "CodeBridge IT", "Kottayam"),
]
print("\n[3/10] Customers")
customers = []
for email, fn, ln, company, city in CUSTOMERS_DATA:
    u = _get_or_create_user(
        email, customer_role,
        first_name=fn, last_name=ln,
        password_hash=hash_password("Customer@123"),
    )
    c = db.query(Customer).filter(Customer.user_id == u.id).first()
    if not c:
        c = Customer(
            user_id=u.id,
            customer_code=next_customer_code(db),
            company_name=company,
            city=city,
            country="India",
        )
        db.add(c)
        db.flush()
        print(f"  Customer: {fn} {ln} — {company}")
    customers.append(c)
db.commit()

# ── 4. Taxes ─────────────────────────────────────────────────────────────────
print("\n[4/10] Taxes")
def _get_or_create_tax(name, pct, tax_type="GST"):
    t = db.query(Tax).filter(Tax.name == name).first()
    if not t:
        t = Tax(name=name, percentage=Decimal(str(pct)), tax_type=tax_type)
        db.add(t)
        db.flush()
        print(f"  Tax: {name} {pct}%")
    return t

gst18 = _get_or_create_tax("GST 18%", 18)
gst12 = _get_or_create_tax("GST 12%", 12)
gst5 = _get_or_create_tax("GST 5%", 5)
db.commit()

# ── 5. Products ──────────────────────────────────────────────────────────────
print("\n[5/10] Products")
def _get_or_create_product(name, ptype, price, cost, desc=""):
    p = db.query(Product).filter(Product.name == name).first()
    if not p:
        p = Product(
            name=name, product_type=ptype,
            sales_price=Decimal(str(price)),
            cost_price=Decimal(str(cost)),
            description=desc,
            is_active=True,
        )
        p.taxes.append(gst18)
        db.add(p)
        db.flush()
        print(f"  Product: {name}")
    return p

prod_erp = _get_or_create_product(
    "Brightloop ERP Suite", "software", 4999, 1500,
    "Full-featured ERP system for SMBs. Includes accounting, inventory, HR, and CRM modules."
)
prod_crm = _get_or_create_product(
    "Brightloop CRM Pro", "software", 2499, 800,
    "Customer relationship management with pipeline automation and analytics."
)
prod_analytics = _get_or_create_product(
    "DataInsight Analytics", "software", 1999, 600,
    "Business intelligence and reporting platform with drag-and-drop dashboards."
)
prod_support = _get_or_create_product(
    "Priority Support Pack", "service", 999, 200,
    "24/7 priority support with dedicated account manager and SLA guarantee."
)
prod_storage = _get_or_create_product(
    "Cloud Storage Add-on", "addon", 499, 100,
    "Additional 500GB cloud storage for any Brightloop product."
)
db.commit()

# ── 6. Product Variants ───────────────────────────────────────────────────────
print("\n[6/10] Product Variants")
VARIANTS = [
    (prod_erp, "Standard", 0),
    (prod_erp, "Odoo Edition", 560),
    (prod_erp, "Enterprise", 1500),
    (prod_crm, "Starter", 0),
    (prod_crm, "Professional", 500),
    (prod_analytics, "Basic", 0),
    (prod_analytics, "Advanced", 800),
]
for prod, vname, modifier in VARIANTS:
    exists = db.query(ProductVariant).filter(
        ProductVariant.product_id == prod.id,
        ProductVariant.name == vname,
    ).first()
    if not exists:
        v = ProductVariant(
            product_id=prod.id, name=vname,
            price_modifier=Decimal(str(modifier)),
        )
        db.add(v)
        db.flush()
        print(f"  Variant: {prod.name} — {vname} (+₹{modifier})")
db.commit()

# ── 7. Subscription Plans ────────────────────────────────────────────────────
print("\n[7/10] Subscription Plans")
def _get_or_create_plan(name, product, freq, price, desc=""):
    p = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == name).first()
    if not p:
        p = SubscriptionPlan(
            name=name, product_id=product.id,
            billing_frequency=freq,
            base_price=Decimal(str(price)),
            description=desc,
            allow_pause=True, allow_renewal=True, allow_early_cancellation=True,
        )
        db.add(p)
        db.flush()
        print(f"  Plan: {name} ({freq}) ₹{price}")
    return p

plan_erp_monthly = _get_or_create_plan("ERP Suite — Monthly", prod_erp, "monthly", 4999)
plan_erp_yearly = _get_or_create_plan("ERP Suite — Annual", prod_erp, "yearly", 49990)
plan_crm_monthly = _get_or_create_plan("CRM Pro — Monthly", prod_crm, "monthly", 2499)
plan_crm_yearly = _get_or_create_plan("CRM Pro — Annual", prod_crm, "yearly", 24990)
plan_analytics = _get_or_create_plan("DataInsight — Monthly", prod_analytics, "monthly", 1999)
plan_support = _get_or_create_plan("Priority Support — Monthly", prod_support, "monthly", 999)
plan_storage = _get_or_create_plan("Cloud Storage — Monthly", prod_storage, "monthly", 499)
db.commit()

# ── 8. Discounts ─────────────────────────────────────────────────────────────
print("\n[8/10] Discounts")
DISCOUNTS = [
    ("Welcome10", "WELCOME10", "percentage", 10, 0, 1, None, date(2027, 12, 31), 100),
    ("Annual20", "ANNUAL20", "percentage", 20, 10000, 1, None, date(2027, 12, 31), 50),
    ("Flat500", "FLAT500", "fixed", 500, 2000, 1, None, date(2027, 6, 30), 30),
    ("NewYear25", "NY25", "percentage", 25, 0, 1, None, date(2027, 1, 31), 20),
]
for dname, code, dtype, val, min_amt, min_qty, sdate, edate, max_use in DISCOUNTS:
    exists = db.query(Discount).filter(Discount.code == code).first()
    if not exists:
        d = Discount(
            name=dname, code=code, discount_type=dtype,
            value=Decimal(str(val)),
            min_purchase_amount=Decimal(str(min_amt)),
            min_quantity=Decimal(str(min_qty)),
            start_date=sdate or date.today(),
            end_date=edate,
            max_usage_count=max_use,
            created_by=admin_user.id,
        )
        db.add(d)
        db.flush()
        print(f"  Discount: {dname} ({code})")
db.commit()

# ── 9. Subscriptions (various states) ────────────────────────────────────────
print("\n[9/10] Subscriptions & Invoices")

def _make_subscription(customer, plan, status, start_offset_days=0, tax_pct=18):
    sub_num = next_subscription_number(db)
    start = date.today() - timedelta(days=start_offset_days)
    sub = Subscription(
        subscription_number=sub_num,
        customer_id=customer.id,
        plan_id=plan.id,
        status=status,
        start_date=start,
        next_billing_date=start if status == "active" else None,
        payment_terms="Due on receipt",
        quantity=Decimal("1"),
        unit_price=plan.base_price,
        tax_pct=Decimal(str(tax_pct)),
        discount_pct=Decimal("0"),
        created_by=admin_user.id,
    )
    calc = calculate_line_totals(sub.quantity, sub.unit_price, Decimal("0"), Decimal(str(tax_pct)))
    sub.subtotal = calc["subtotal"]
    sub.tax_amount = calc["tax_amount"]
    sub.discount_amount = calc["discount_amount"]
    sub.total_amount = calc["total"]
    db.add(sub)
    db.flush()
    # Add a subscription line
    sl = SubscriptionLine(
        subscription_id=sub.id,
        product_id=plan.product_id,
        description=f"{plan.product.name if plan.product else plan.name}",
        quantity=sub.quantity,
        unit_price=sub.unit_price,
        tax_pct=sub.tax_pct,
        subtotal=sub.subtotal,
        tax_amount=sub.tax_amount,
        total=sub.total_amount,
    )
    db.add(sl)
    db.flush()
    return sub


def _make_invoice(sub, invoice_date, status, due_offset=7):
    inv_num = next_invoice_number(db)
    due = invoice_date + timedelta(days=due_offset)
    freq = sub.plan.billing_frequency if sub.plan else "monthly"
    period_end = cycle_end_date(invoice_date, freq)
    inv = Invoice(
        invoice_number=inv_num,
        customer_id=sub.customer_id,
        subscription_id=sub.id,
        status=status,
        invoice_date=invoice_date,
        due_date=due,
        billing_period_start=invoice_date,
        billing_period_end=period_end,
        payment_terms="Due on receipt",
        created_by=admin_user.id,
    )
    calc = calculate_line_totals(sub.quantity, sub.unit_price, sub.discount_pct, sub.tax_pct)
    inv.subtotal = calc["subtotal"]
    inv.tax_amount = calc["tax_amount"]
    inv.discount_amount = calc["discount_amount"]
    inv.grand_total = calc["total"]
    if status == "paid":
        inv.paid_amount = inv.grand_total
        inv.outstanding_amount = Decimal("0")
    elif status == "partially_paid":
        inv.paid_amount = (inv.grand_total / 2).quantize(Decimal("0.01"))
        inv.outstanding_amount = inv.grand_total - inv.paid_amount
    else:
        inv.outstanding_amount = inv.grand_total
        inv.paid_amount = Decimal("0")
    db.add(inv)
    db.flush()

    # Invoice line
    il = InvoiceLine(
        invoice_id=inv.id,
        product_id=sub.plan.product_id if sub.plan else None,
        description=f"{sub.plan.name if sub.plan else 'Subscription'} — {invoice_date} to {period_end}",
        quantity=sub.quantity,
        unit_price=sub.unit_price,
        tax_pct=sub.tax_pct,
        subtotal=inv.subtotal,
        tax_amount=inv.tax_amount,
        total=inv.grand_total,
    )
    db.add(il)

    # Billing cycle record
    bc = BillingCycle(
        subscription_id=sub.id,
        invoice_id=inv.id,
        cycle_start=invoice_date,
        cycle_end=period_end,
        status="billed",
    )
    db.add(bc)
    db.flush()
    return inv


# Only create if no subscriptions exist
if db.query(Subscription).count() == 0:
    today = date.today()

    # Active subscriptions (8)
    subs = [
        _make_subscription(customers[0], plan_erp_monthly, "active", start_offset_days=95),
        _make_subscription(customers[1], plan_crm_monthly, "active", start_offset_days=60),
        _make_subscription(customers[2], plan_analytics, "active", start_offset_days=45),
        _make_subscription(customers[3], plan_erp_yearly, "active", start_offset_days=120),
        _make_subscription(customers[4], plan_crm_yearly, "active", start_offset_days=30),
        _make_subscription(customers[5], plan_support, "active", start_offset_days=15),
        _make_subscription(customers[6], plan_storage, "active", start_offset_days=10),
        _make_subscription(customers[7], plan_erp_monthly, "active", start_offset_days=5),
    ]

    # Paused subscriptions (2)
    paused_sub1 = _make_subscription(customers[8], plan_crm_monthly, "paused", start_offset_days=50)
    paused_sub2 = _make_subscription(customers[9], plan_analytics, "paused", start_offset_days=35)
    subs += [paused_sub1, paused_sub2]

    # Confirmed subscriptions (2)
    conf_sub1 = _make_subscription(customers[2], plan_support, "confirmed", start_offset_days=0)
    conf_sub2 = _make_subscription(customers[4], plan_storage, "confirmed", start_offset_days=0)
    subs += [conf_sub1, conf_sub2]

    # Closed subscription (1)
    closed_sub = _make_subscription(customers[5], plan_erp_monthly, "closed", start_offset_days=200)
    subs.append(closed_sub)

    db.commit()
    print(f"  Created {len(subs)} subscriptions")

    # ── Invoices ──────────────────────────────────────────────────────────
    # Paid invoices for active subs
    inv1 = _make_invoice(subs[0], today - timedelta(days=90), "paid")
    inv2 = _make_invoice(subs[0], today - timedelta(days=60), "paid")
    inv3 = _make_invoice(subs[1], today - timedelta(days=55), "paid")
    inv4 = _make_invoice(subs[2], today - timedelta(days=40), "paid")
    inv5 = _make_invoice(subs[3], today - timedelta(days=100), "paid")

    # Confirmed (pending) invoices
    inv6 = _make_invoice(subs[0], today - timedelta(days=3), "confirmed")
    inv7 = _make_invoice(subs[1], today - timedelta(days=5), "confirmed")

    # Partially paid
    inv8 = _make_invoice(subs[4], today - timedelta(days=20), "partially_paid")

    # Overdue invoices
    inv9 = _make_invoice(subs[2], today - timedelta(days=35), "confirmed", due_offset=7)
    inv9.due_date = today - timedelta(days=20)  # force overdue
    inv10 = _make_invoice(subs[5], today - timedelta(days=25), "confirmed", due_offset=7)
    inv10.due_date = today - timedelta(days=15)  # force overdue

    db.commit()
    print("  Created demo invoices (paid, pending, overdue)")

    # ── Payments ──────────────────────────────────────────────────────────
    def _pay(customer, amount, inv, method="upi", ref=None):
        pay_num = next_payment_number(db)
        p = Payment(
            payment_number=pay_num,
            customer_id=customer.id,
            payment_method=method,
            amount=Decimal(str(amount)),
            payment_date=date.today() - timedelta(days=1),
            reference_number=ref or f"REF{pay_num[-4:]}",
            status="confirmed",
            recorded_by=admin_user.id,
        )
        db.add(p)
        db.flush()
        alloc = PaymentAllocation(
            payment_id=p.id,
            invoice_id=inv.id,
            amount=Decimal(str(amount)),
        )
        db.add(alloc)
        return p

    _pay(customers[0], float(inv1.grand_total), inv1, "upi", "UPI-001")
    _pay(customers[0], float(inv2.grand_total), inv2, "bank_transfer", "NEFT-002")
    _pay(customers[1], float(inv3.grand_total), inv3, "card", "CARD-003")
    _pay(customers[2], float(inv4.grand_total), inv4, "cash", "CASH-004")
    _pay(customers[3], float(inv5.grand_total), inv5, "upi", "UPI-005")
    # Partial payment for inv8
    _pay(customers[4], float(inv8.paid_amount or 0), inv8, "upi", "UPI-006")

    db.commit()
    print("  Created demo payments")
else:
    print("  Subscriptions already exist — skipping.")

# ── 10. Quotation Templates ───────────────────────────────────────────────────
print("\n[10/10] Quotation Templates")
from app.models.quotation import QuotationTemplate
if db.query(QuotationTemplate).count() == 0:
    for tname, plan in [
        ("Standard ERP Quotation", plan_erp_monthly),
        ("Annual ERP Quotation", plan_erp_yearly),
        ("CRM Quick Quote", plan_crm_monthly),
    ]:
        t = QuotationTemplate(name=tname, plan_id=plan.id, validity_days=30)
        db.add(t)
        print(f"  Template: {tname}")
    db.commit()
else:
    print("  Templates already exist — skipping.")

db.close()
print("\n✅ Seed complete!")
print("\nDemo credentials:")
print("  Admin:    admin@brightloop.in  / Admin@12345")
print("  Staff:    staff1@brightloop.in / Staff@12345")
print("  Customer: alice@techvision.in  / Customer@123")
