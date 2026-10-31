"""
Core business logic tests for SubscriptIQ.
Run: py -m pytest tests/ -v
"""
import pytest
import json
import os
import sys
from datetime import date, timedelta
from decimal import Decimal

# Ensure the backend package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from app import create_app
from app.database import Base, engine, SessionLocal
from app.models import *  # noqa


@pytest.fixture(scope="module")
def app():
    app = create_app()
    app.config["TESTING"] = True
    Base.metadata.create_all(bind=engine)
    yield app
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


def _seed_base(db):
    """Create minimum roles, admin user, and customer for tests."""
    from app.models.user import Role, User
    from app.models.customer import Customer
    from app.utils.security import hash_password
    from app.utils.numbering import next_customer_code

    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if not admin_role:
        admin_role = Role(name="admin")
        db.add(admin_role)
    staff_role = db.query(Role).filter(Role.name == "staff").first()
    if not staff_role:
        staff_role = Role(name="staff")
        db.add(staff_role)
    cust_role = db.query(Role).filter(Role.name == "customer").first()
    if not cust_role:
        cust_role = Role(name="customer")
        db.add(cust_role)
    db.flush()

    admin = db.query(User).filter(User.email == "test_admin@example.com").first()
    if not admin:
        admin = User(
            email="test_admin@example.com",
            password_hash=hash_password("Admin@Test1"),
            first_name="Test", last_name="Admin",
            role_id=admin_role.id, is_active=True, is_verified=True,
        )
        db.add(admin)
        db.flush()

    cust_user = db.query(User).filter(User.email == "test_cust@example.com").first()
    if not cust_user:
        cust_user = User(
            email="test_cust@example.com",
            password_hash=hash_password("Cust@Test1"),
            first_name="Test", last_name="Customer",
            role_id=cust_role.id, is_active=True, is_verified=True,
        )
        db.add(cust_user)
        db.flush()
        customer = Customer(user_id=cust_user.id, customer_code=next_customer_code(db))
        db.add(customer)

    db.commit()
    return admin_role, staff_role, cust_role


# ─── 1. Password validation ────────────────────────────────────────────────

def test_password_too_short():
    from app.utils.security import validate_password_strength
    ok, msg = validate_password_strength("Ab@1")
    assert not ok
    assert "8 characters" in msg


def test_password_no_uppercase():
    from app.utils.security import validate_password_strength
    ok, msg = validate_password_strength("abcdef@123")
    assert not ok


def test_password_no_special():
    from app.utils.security import validate_password_strength
    ok, msg = validate_password_strength("Abcdef1234")
    assert not ok


def test_password_valid():
    from app.utils.security import validate_password_strength
    ok, msg = validate_password_strength("Admin@12345")
    assert ok


def test_password_hash_verify():
    from app.utils.security import hash_password, verify_password
    h = hash_password("Admin@12345")
    assert verify_password("Admin@12345", h)
    assert not verify_password("Wrong@123", h)


# ─── 2. Duplicate email registration ──────────────────────────────────────

def test_duplicate_email_rejected(client, db):
    _seed_base(db)
    # Register first time
    resp = client.post("/api/auth/register", json={
        "email": "duptest@example.com",
        "password": "Valid@Pass1",
        "first_name": "Dup", "last_name": "Test",
    })
    assert resp.status_code == 201
    # Register again with same email
    resp2 = client.post("/api/auth/register", json={
        "email": "duptest@example.com",
        "password": "Valid@Pass1",
        "first_name": "Dup2", "last_name": "Test2",
    })
    assert resp2.status_code == 409
    data = json.loads(resp2.data)
    assert "already registered" in data["error"].lower()


# ─── 3. Weak password rejected ────────────────────────────────────────────

def test_weak_password_rejected(client, db):
    _seed_base(db)
    resp = client.post("/api/auth/register", json={
        "email": "weakpwd@example.com",
        "password": "password",
        "first_name": "Weak", "last_name": "Pass",
    })
    assert resp.status_code == 400


# ─── 4. Customer cannot access other customer data ────────────────────────

def test_customer_cannot_access_other_customer(client, db):
    _seed_base(db)
    from app.models.customer import Customer
    from app.models.user import User

    # Login as customer
    r = client.post("/api/auth/login", json={"email": "test_cust@example.com", "password": "Cust@Test1"})
    token = json.loads(r.data)["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get their own customer record
    user = db.query(User).filter(User.email == "test_cust@example.com").first()
    own_cust = db.query(Customer).filter(Customer.user_id == user.id).first()

    # Try to access admin's data (no customer record for admin, but we can test list is filtered)
    resp = client.get("/api/customers", headers=headers)
    # Customers don't have access to the customer list endpoint
    assert resp.status_code == 403


# ─── 5. Staff cannot create discount rules ────────────────────────────────

def test_staff_cannot_create_discount(client, db):
    from app.models.user import User, Role
    from app.utils.security import hash_password

    _seed_base(db)
    staff_role = db.query(Role).filter(Role.name == "staff").first()
    staff_user = db.query(User).filter(User.email == "test_staff@example.com").first()
    if not staff_user:
        staff_user = User(
            email="test_staff@example.com",
            password_hash=hash_password("Staff@Test1"),
            first_name="Test", last_name="Staff",
            role_id=staff_role.id, is_active=True, is_verified=True,
        )
        db.add(staff_user)
        db.commit()

    r = client.post("/api/auth/login", json={"email": "test_staff@example.com", "password": "Staff@Test1"})
    token = json.loads(r.data)["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/api/discounts", headers=headers, json={
        "name": "Test Discount", "discount_type": "percentage", "value": 10,
    })
    assert resp.status_code == 403


# ─── 6. Product variant pricing ───────────────────────────────────────────

def test_product_variant_pricing():
    from app.models.product import Product, ProductVariant

    p = Product(name="Test Product", sales_price=Decimal("1000.00"))
    v = ProductVariant(price_modifier=Decimal("560.00"))
    v.product = p
    assert v.effective_price == Decimal("1560.00")


# ─── 7. Billing cycle date calculations ───────────────────────────────────

def test_billing_cycle_monthly():
    from app.utils.billing_calc import next_billing_date, cycle_end_date
    d = date(2026, 1, 31)
    nbd = next_billing_date(d, "monthly")
    assert nbd == date(2026, 2, 28)  # Month-end clamping


def test_billing_cycle_leap_year():
    from app.utils.billing_calc import next_billing_date
    d = date(2027, 2, 28)
    nbd = next_billing_date(d, "monthly")
    assert nbd == date(2027, 3, 28)


def test_billing_cycle_yearly():
    from app.utils.billing_calc import next_billing_date
    d = date(2026, 2, 28)
    nbd = next_billing_date(d, "yearly")
    assert nbd == date(2027, 2, 28)


def test_billing_cycle_weekly():
    from app.utils.billing_calc import next_billing_date
    d = date(2026, 10, 31)
    nbd = next_billing_date(d, "weekly")
    assert nbd == date(2026, 11, 7)


def test_billing_cycle_end_date():
    from app.utils.billing_calc import cycle_end_date
    d = date(2026, 10, 1)
    end = cycle_end_date(d, "monthly")
    assert end == date(2026, 10, 31)


def test_invalid_frequency():
    from app.utils.billing_calc import next_billing_date
    with pytest.raises(ValueError):
        next_billing_date(date.today(), "quarterly")


# ─── 8. Expired plan cannot create subscription ───────────────────────────

def test_expired_plan_rejected():
    from app.utils.billing_calc import is_plan_available

    class FakePlan:
        is_active = True
        available_from = None
        available_until = date(2020, 1, 1)  # Expired in the past

    ok, msg = is_plan_available(FakePlan())
    assert not ok
    assert "expired" in msg.lower()


def test_future_plan_rejected():
    from app.utils.billing_calc import is_plan_available

    class FakePlan:
        is_active = True
        available_from = date(2030, 1, 1)
        available_until = None

    ok, msg = is_plan_available(FakePlan())
    assert not ok
    assert "not available" in msg.lower()


def test_inactive_plan_rejected():
    from app.utils.billing_calc import is_plan_available

    class FakePlan:
        is_active = False
        available_from = None
        available_until = None

    ok, msg = is_plan_available(FakePlan())
    assert not ok


# ─── 9. Tax calculation ───────────────────────────────────────────────────

def test_tax_calculation():
    from app.utils.billing_calc import calculate_line_totals
    result = calculate_line_totals(
        quantity=Decimal("1"),
        unit_price=Decimal("1000.00"),
        discount_pct=Decimal("0"),
        tax_pct=Decimal("18"),
    )
    assert result["subtotal"] == Decimal("1000.00")
    assert result["tax_amount"] == Decimal("180.00")
    assert result["total"] == Decimal("1180.00")


def test_discount_then_tax():
    from app.utils.billing_calc import calculate_line_totals
    result = calculate_line_totals(
        quantity=Decimal("2"),
        unit_price=Decimal("500.00"),
        discount_pct=Decimal("10"),
        tax_pct=Decimal("18"),
    )
    # Gross = 1000, discount = 100, subtotal = 900, tax = 162, total = 1062
    assert result["gross"] == Decimal("1000.00")
    assert result["discount_amount"] == Decimal("100.00")
    assert result["subtotal"] == Decimal("900.00")
    assert result["tax_amount"] == Decimal("162.00")
    assert result["total"] == Decimal("1062.00")


# ─── 10. Discount validation ─────────────────────────────────────────────

def test_discount_validate_expired(client, db):
    _seed_base(db)
    r = client.post("/api/auth/login", json={"email": "test_admin@example.com", "password": "Admin@Test1"})
    token = json.loads(r.data)["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create an expired discount
    resp = client.post("/api/discounts", headers=headers, json={
        "name": "Expired Discount", "code": "EXPIRED99",
        "discount_type": "percentage", "value": 10,
        "start_date": "2020-01-01", "end_date": "2021-01-01",
    })
    assert resp.status_code == 201

    # Validate it
    v = client.post("/api/discounts/validate", headers=headers, json={
        "code": "EXPIRED99", "amount": 1000, "quantity": 1
    })
    vdata = json.loads(v.data)
    assert vdata["valid"] == False
    assert "expired" in vdata["reason"].lower()


def test_discount_validate_valid(client, db):
    _seed_base(db)
    r = client.post("/api/auth/login", json={"email": "test_admin@example.com", "password": "Admin@Test1"})
    token = json.loads(r.data)["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/api/discounts", headers=headers, json={
        "name": "Valid10", "code": "VALID10TEST",
        "discount_type": "percentage", "value": 10,
        "end_date": "2028-12-31", "max_usage_count": 100,
    })

    v = client.post("/api/discounts/validate", headers=headers, json={
        "code": "VALID10TEST", "amount": 1000, "quantity": 1
    })
    vdata = json.loads(v.data)
    assert vdata["valid"] == True
    assert vdata["savings"] == 100.0


# ─── 11. Overdue invoice detection ───────────────────────────────────────

def test_overdue_invoice_detection():
    from app.models.invoice import Invoice

    inv = Invoice(
        invoice_number="TEST-001",
        invoice_date=date.today() - timedelta(days=30),
        due_date=date.today() - timedelta(days=5),
        status="confirmed",
        outstanding_amount=Decimal("500.00"),
        grand_total=Decimal("500.00"),
    )
    assert inv.is_overdue


def test_paid_invoice_not_overdue():
    from app.models.invoice import Invoice
    inv = Invoice(
        invoice_number="TEST-002",
        invoice_date=date.today() - timedelta(days=30),
        due_date=date.today() - timedelta(days=5),
        status="paid",
        outstanding_amount=Decimal("0.00"),
        grand_total=Decimal("500.00"),
    )
    assert not inv.is_overdue


def test_invoice_not_yet_due_not_overdue():
    from app.models.invoice import Invoice
    inv = Invoice(
        invoice_number="TEST-003",
        invoice_date=date.today(),
        due_date=date.today() + timedelta(days=7),
        status="confirmed",
        outstanding_amount=Decimal("500.00"),
        grand_total=Decimal("500.00"),
    )
    assert not inv.is_overdue


# ─── 12. Document totals aggregation ─────────────────────────────────────

def test_document_totals():
    from app.utils.billing_calc import calculate_document_totals
    lines = [
        {"subtotal": Decimal("900"), "tax_amount": Decimal("162"), "discount_amount": Decimal("100"), "total": Decimal("1062")},
        {"subtotal": Decimal("500"), "tax_amount": Decimal("90"), "discount_amount": Decimal("0"), "total": Decimal("590")},
    ]
    totals = calculate_document_totals(lines)
    assert totals["subtotal"] == Decimal("1400.00")
    assert totals["tax_amount"] == Decimal("252.00")
    assert totals["discount_amount"] == Decimal("100.00")
    assert totals["grand_total"] == Decimal("1652.00")


# ─── 13. JWT token creation and verification ─────────────────────────────

def test_jwt_round_trip():
    from app.utils.security import create_access_token, decode_access_token
    token = create_access_token({"sub": "user-123", "role": "admin"})
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["role"] == "admin"


def test_jwt_invalid_token():
    from app.utils.security import decode_access_token
    result = decode_access_token("not-a-valid-token")
    assert result is None


# ─── 14. Sequential number generation ────────────────────────────────────

def test_invoice_numbering_sequence(db):
    from app.utils.numbering import next_invoice_number
    n1 = next_invoice_number(db)
    assert n1.startswith("INV-")
    # The prefix and padding are correct
    suffix = n1.split("-")[1]
    assert suffix.isdigit()
    assert len(suffix) == 5


def test_payment_number_prefix(db):
    from app.utils.numbering import next_payment_number
    n = next_payment_number(db)
    assert n.startswith("PAY-")


def test_subscription_number_prefix(db):
    from app.utils.numbering import next_subscription_number
    n = next_subscription_number(db)
    assert n.startswith("SUB-")


# ─── 15. Health endpoint ─────────────────────────────────────────────────

def test_health_endpoint(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data["status"] == "ok"
