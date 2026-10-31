"""Product and ProductVariant routes."""
from flask import Blueprint, request, jsonify, g
from app.database import SessionLocal
from app.models.product import Product, ProductVariant
from app.models.tax import Tax
from app.utils.auth_middleware import require_auth, require_admin_or_staff, require_admin, audit

products_bp = Blueprint("products", __name__, url_prefix="/api/products")


def _variant_dict(v: ProductVariant) -> dict:
    return {
        "id": v.id,
        "product_id": v.product_id,
        "name": v.name,
        "sku": v.sku,
        "price_modifier": float(v.price_modifier or 0),
        "effective_price": float(v.effective_price),
        "description": v.description,
        "is_active": v.is_active,
        "created_at": v.created_at.isoformat() if v.created_at else None,
    }


def _product_dict(p: Product, include_variants=True) -> dict:
    d = {
        "id": p.id,
        "name": p.name,
        "product_type": p.product_type,
        "description": p.description,
        "notes": p.notes,
        "sales_price": float(p.sales_price or 0),
        "cost_price": float(p.cost_price or 0),
        "image_url": p.image_url,
        "is_active": p.is_active,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "taxes": [{"id": t.id, "name": t.name, "percentage": float(t.percentage)} for t in (p.taxes or [])],
    }
    if include_variants:
        d["variants"] = [_variant_dict(v) for v in p.variants if v.is_active]
    return d


@products_bp.route("", methods=["GET"])
@require_auth
def list_products():
    db = SessionLocal()
    try:
        q = db.query(Product)
        search = request.args.get("search", "").strip()
        if search:
            q = q.filter(Product.name.ilike(f"%{search}%"))
        is_active = request.args.get("is_active")
        if is_active is not None:
            q = q.filter(Product.is_active == (is_active.lower() != "false"))

        total = q.count()
        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(int(request.args.get("per_page", 20)), 100)
        items = q.order_by(Product.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        return jsonify({
            "items": [_product_dict(p) for p in items],
            "total": total, "page": page, "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        })
    finally:
        db.close()


@products_bp.route("/<product_id>", methods=["GET"])
@require_auth
def get_product(product_id):
    db = SessionLocal()
    try:
        p = db.query(Product).filter(Product.id == product_id).first()
        if not p:
            return jsonify({"error": "Product not found"}), 404
        return jsonify(_product_dict(p))
    finally:
        db.close()


@products_bp.route("", methods=["POST"])
@require_admin_or_staff
def create_product():
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "Product name is required."}), 400

    db = SessionLocal()
    try:
        from decimal import Decimal
        p = Product(
            name=data["name"].strip(),
            product_type=data.get("product_type", "software"),
            description=data.get("description"),
            notes=data.get("notes"),
            sales_price=Decimal(str(data.get("sales_price", 0))),
            cost_price=Decimal(str(data.get("cost_price", 0))),
            image_url=data.get("image_url"),
        )
        # Attach taxes
        for tax_id in data.get("tax_ids", []):
            tax = db.query(Tax).filter(Tax.id == tax_id).first()
            if tax:
                p.taxes.append(tax)

        db.add(p)
        db.flush()

        for vd in data.get("variants", []):
            v = ProductVariant(
                product_id=p.id,
                name=vd.get("name", ""),
                sku=vd.get("sku"),
                price_modifier=Decimal(str(vd.get("price_modifier", 0))),
                description=vd.get("description"),
            )
            db.add(v)

        audit(db, g.current_user, "product.created", "product", p.id, notes=p.name)
        db.commit()
        db.refresh(p)
        return jsonify(_product_dict(p)), 201
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@products_bp.route("/<product_id>", methods=["PUT"])
@require_admin_or_staff
def update_product(product_id):
    db = SessionLocal()
    try:
        p = db.query(Product).filter(Product.id == product_id).first()
        if not p:
            return jsonify({"error": "Product not found"}), 404
        data = request.get_json(silent=True) or {}
        from decimal import Decimal
        for field in ("name", "product_type", "description", "notes", "image_url"):
            if field in data:
                setattr(p, field, data[field])
        for field in ("sales_price", "cost_price"):
            if field in data:
                setattr(p, field, Decimal(str(data[field])))
        if "is_active" in data:
            p.is_active = bool(data["is_active"])
        if "tax_ids" in data:
            p.taxes = []
            for tax_id in data["tax_ids"]:
                tax = db.query(Tax).filter(Tax.id == tax_id).first()
                if tax:
                    p.taxes.append(tax)

        audit(db, g.current_user, "product.updated", "product", product_id)
        db.commit()
        db.refresh(p)
        return jsonify(_product_dict(p))
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


# ── Variant sub-routes ──────────────────────────────────────────────────────

@products_bp.route("/<product_id>/variants", methods=["POST"])
@require_admin_or_staff
def add_variant(product_id):
    db = SessionLocal()
    try:
        p = db.query(Product).filter(Product.id == product_id).first()
        if not p:
            return jsonify({"error": "Product not found"}), 404
        data = request.get_json(silent=True) or {}
        from decimal import Decimal
        v = ProductVariant(
            product_id=p.id,
            name=data.get("name", ""),
            sku=data.get("sku"),
            price_modifier=Decimal(str(data.get("price_modifier", 0))),
            description=data.get("description"),
        )
        db.add(v)
        audit(db, g.current_user, "variant.created", "product_variant", v.id, notes=p.name)
        db.commit()
        db.refresh(v)
        return jsonify(_variant_dict(v)), 201
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@products_bp.route("/<product_id>/variants/<variant_id>", methods=["PUT"])
@require_admin_or_staff
def update_variant(product_id, variant_id):
    db = SessionLocal()
    try:
        v = db.query(ProductVariant).filter(
            ProductVariant.id == variant_id,
            ProductVariant.product_id == product_id
        ).first()
        if not v:
            return jsonify({"error": "Variant not found"}), 404
        data = request.get_json(silent=True) or {}
        from decimal import Decimal
        for field in ("name", "sku", "description"):
            if field in data:
                setattr(v, field, data[field])
        if "price_modifier" in data:
            v.price_modifier = Decimal(str(data["price_modifier"]))
        if "is_active" in data:
            v.is_active = bool(data["is_active"])

        audit(db, g.current_user, "variant.updated", "product_variant", variant_id)
        db.commit()
        db.refresh(v)
        return jsonify(_variant_dict(v))
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()
