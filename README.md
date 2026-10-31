# SubscriptIQ — Intelligent Subscription & Revenue Management Platform

**Odoo × Make-A-Ton 9.0 Kochi Hackathon 2026**  
Client: **Brightloop Software**

---

## Overview

SubscriptIQ is a full-stack, production-quality subscription management platform built for software companies that sell recurring plans. It handles the complete subscription lifecycle from quotation through automated billing, payment reconciliation, and financial analytics.

## Tech Stack

| Layer      | Technology                              |
|------------|-----------------------------------------|
| Backend    | Python 3.13 · Flask 3.1 · SQLAlchemy 2.0 |
| Database   | SQLite (WAL mode) — drop-in PostgreSQL upgrade path |
| Auth       | bcrypt + PyJWT (HS256)                  |
| Scheduler  | APScheduler (daily billing at 00:05 IST) |
| Frontend   | React 18 · TypeScript · Vite 6          |
| Styling    | Tailwind CSS 3                          |
| Charts     | Recharts                                |
| HTTP Client| Axios + TanStack Query                  |

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+

### Backend

```bash
cd backend
# Copy environment config
copy .env.example .env

# Install dependencies
pip install flask flask-cors passlib[bcrypt] PyJWT APScheduler \
            Flask-Mail python-dotenv SQLAlchemy reportlab bcrypt \
            pydantic uvicorn httpx Pillow alembic

# Seed the database with demo data
py seed.py

# Start the API server
py run.py
# → runs at http://localhost:5000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# → runs at http://localhost:5173
```

---

## Demo Credentials

| Role     | Email                       | Password        |
|----------|-----------------------------|-----------------|
| Admin    | admin@brightloop.in         | Admin@12345     |
| Staff    | staff1@brightloop.in        | Staff@12345     |
| Customer | alice@techvision.in         | Customer@123    |

---

## Key Features

### 1. Subscription Lifecycle Engine
Draft → Quotation → Confirmed → Active → Paused/Closed/Expired  
Every transition is validated, logged, and can be triggered via the UI.

### 2. Automated Recurring Billing
- Runs daily at 00:05 IST via APScheduler
- Manual "Run Billing Now" button for demos
- Idempotent: BillingCycle unique constraint prevents duplicate invoices at the database level
- Supports nested savepoints — one failure never corrupts the entire run
- Detailed billing execution logs

### 3. Financial Dashboard
- Live MRR & ARR (normalized across billing frequencies)
- Revenue trend charts (6 months)
- Revenue by product
- Subscription status distribution (Pie chart)
- Upcoming renewals (30 days)
- Overdue invoice summary

### 4. Invoice & Payment System
- Auto-generated invoices with correct line items, taxes, and discounts
- Multiple payments per invoice (partial payment supported)
- PaymentAllocation model prevents overpayment
- Invoice reconciliation updates outstanding balance automatically

### 5. Customer Portal
- Isolated per-customer: server-side ownership check on every request
- Subscriptions, invoices, payment history, profile management

### 6. Smart Discounts (Admin-only)
- Fixed and percentage types
- Date-range enforcement
- Usage count limits
- Per-product scope

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    React SPA                         │
│  TanStack Query · Axios · Tailwind · Recharts        │
│  http://localhost:5173                               │
└───────────────────────┬─────────────────────────────┘
                        │ /api/* (Vite proxy)
┌───────────────────────▼─────────────────────────────┐
│               Flask REST API                         │
│  http://localhost:5000                               │
│                                                      │
│  /api/auth        /api/customers   /api/products     │
│  /api/plans       /api/quotations  /api/subscriptions│
│  /api/billing     /api/invoices    /api/payments     │
│  /api/discounts   /api/taxes       /api/reports      │
│  /api/staff                                          │
│                                                      │
│  APScheduler (daily billing 00:05 IST)               │
└───────────────────────┬─────────────────────────────┘
                        │ SQLAlchemy ORM
┌───────────────────────▼─────────────────────────────┐
│             SQLite (subscriptiq.db)                  │
│             WAL mode · FK constraints                │
└─────────────────────────────────────────────────────┘
```

---

## Database Schema (23 entities)

- **users** + **roles** — Authentication and RBAC
- **customers** — Extended customer profiles linked to users
- **products** + **product_variants** — Product catalog
- **taxes** + **product_taxes** — Tax configuration (many-to-many)
- **subscription_plans** + **plan_pricing** — Plan definitions
- **quotation_templates** + **quotations** + **quotation_lines** — Quote workflow
- **subscriptions** + **subscription_lines** + **billing_cycles** — Lifecycle engine
- **invoices** + **invoice_lines** — Auto-generated billing documents
- **discounts** + **discount_products** + **discount_applications** — Promotion engine
- **payments** + **payment_allocations** — Cash reconciliation
- **notifications** — Customer communication log
- **audit_logs** — Immutable change history
- **billing_execution_logs** — Billing run tracking

---

## Hackathon Demo Script

1. **Login as Admin** → `admin@brightloop.in / Admin@12345`
2. **Dashboard** — Show MRR, ARR, active subs, overdue invoices, charts
3. **Products** → Add "Brightloop ERP Suite" with "Odoo Edition" variant (+₹560)
4. **Plans** → Create monthly and yearly plans
5. **Customers** → View Alice Thomas (TechVision)
6. **Quotations** → Create a new quotation, confirm it, convert to subscription
7. **Subscriptions** → Activate the subscription
8. **Billing Engine** → Click "Run Billing Now" → shows generated invoices
9. **Invoices** → Open the generated invoice, show tax breakdown
10. **Payments** → Record a UPI payment, show outstanding → ₹0
11. **Overdue** → Reports → Overdue tab: show overdue invoices with days count
12. **Customer Portal** → Log in as alice@techvision.in → show subscriptions, invoices
13. **Dashboard** → Return to admin, show updated revenue figures

---

## API Reference (abbreviated)

### Authentication
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/auth/login | Login |
| POST | /api/auth/register | Register (customer) |
| GET  | /api/auth/me | Current user |
| POST | /api/auth/forgot-password | Request reset |
| POST | /api/auth/reset-password | Set new password |

### Subscriptions
| Method | Path | Description |
|--------|------|-------------|
| GET  | /api/subscriptions | List with filters |
| POST | /api/subscriptions | Create |
| POST | /api/subscriptions/:id/activate | Activate |
| POST | /api/subscriptions/:id/pause | Pause |
| POST | /api/subscriptions/:id/resume | Resume |
| POST | /api/subscriptions/:id/renew | Renew |
| POST | /api/subscriptions/:id/cancel | Cancel |

### Billing
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/billing/run | Run billing engine |
| GET  | /api/billing/due-count | Subscriptions due |
| GET  | /api/billing/logs | Execution history |

### Reports
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/reports/dashboard | All KPIs and charts |
| GET | /api/reports/mrr-arr | MRR/ARR breakdown |
| GET | /api/reports/overdue | Overdue invoices |
| GET | /api/reports/revenue | Revenue report |
| GET | /api/reports/forecast | 12-month forecast |
| GET | /api/reports/audit-logs | Audit trail |

---

## Team

Developed for **Odoo × Make-A-Ton 9.0 Kochi Hackathon 2026**

| Module | Ownership |
|--------|-----------|
| Auth, Users, Customers | Member 1 |
| Products, Variants, Plans, Quotations | Member 2 |
| Subscriptions, Billing Engine, Invoices | Member 3 |
| Payments, Discounts, Reports, Tests | Member 4 |

---

## Security Notes

- Passwords: bcrypt with SHA-256 pre-hash (handles passwords > 72 bytes)
- JWT: HS256, configurable expiry
- All financial operations: server-side only, never in frontend
- Customer data isolation: every API endpoint enforces ownership
- No plain-text secrets committed (use .env, never .env in git)

## License

MIT — Built for demonstration purposes at Odoo × Make-A-Ton 9.0
