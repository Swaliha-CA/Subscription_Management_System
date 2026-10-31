"""Flask application factory."""
from flask import Flask
from flask_cors import CORS

from app.config import config
from app.database import init_db


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.SECRET_KEY

    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    # Initialise DB (create tables if they don't exist)
    init_db()

    # Register all blueprints
    from app.routes.auth import auth_bp
    from app.routes.customers import customers_bp
    from app.routes.products import products_bp
    from app.routes.plans import plans_bp
    from app.routes.quotations import quotations_bp
    from app.routes.subscriptions import subscriptions_bp
    from app.routes.billing import billing_bp
    from app.routes.invoices import invoices_bp
    from app.routes.payments import payments_bp
    from app.routes.discounts import discounts_bp
    from app.routes.taxes import taxes_bp
    from app.routes.reports import reports_bp
    from app.routes.staff import staff_bp

    for bp in (auth_bp, customers_bp, products_bp, plans_bp,
               quotations_bp, subscriptions_bp, billing_bp,
               invoices_bp, payments_bp, discounts_bp, taxes_bp,
               reports_bp, staff_bp):
        app.register_blueprint(bp)

    @app.route("/api/health")
    def health():
        return {"status": "ok", "app": "SubscriptIQ"}

    return app
