import os
import socket
from decimal import Decimal

from flask import Flask, render_template, redirect, url_for, session, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "local-development-key-change-before-deploying")

# Local development uses SQLite. Set DATABASE_URL to use PostgreSQL later on AWS RDS.
database_url = os.environ.get("DATABASE_URL", "sqlite:///shopstack.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(60), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    emoji = db.Column(db.String(12), default="🛍️")
    description = db.Column(db.Text, nullable=False)
    badge = db.Column(db.String(40), default="")
    stock = db.Column(db.Integer, nullable=False, default=25)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="placed")
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    product_name = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)


SEED_PRODUCTS = [
    {"id": 1, "name": "Everyday Backpack", "category": "Accessories", "price": "39.99", "emoji": "🎒", "description": "A lightweight backpack for work, travel, and everyday use.", "badge": "Bestseller", "stock": 30},
    {"id": 2, "name": "Wireless Headphones", "category": "Electronics", "price": "79.00", "emoji": "🎧", "description": "Comfortable over-ear sound for your daily playlist.", "badge": "Popular", "stock": 25},
    {"id": 3, "name": "Classic Sneakers", "category": "Fashion", "price": "64.50", "emoji": "👟", "description": "Clean, versatile sneakers designed for all-day comfort.", "badge": "New", "stock": 20},
    {"id": 4, "name": "Smart Watch", "category": "Electronics", "price": "99.00", "emoji": "⌚", "description": "Track your day and keep useful notifications close.", "badge": "", "stock": 18},
    {"id": 5, "name": "Ceramic Coffee Mug", "category": "Home", "price": "18.00", "emoji": "☕", "description": "A minimal ceramic mug for your morning coffee.", "badge": "", "stock": 40},
    {"id": 6, "name": "Desk Plant", "category": "Home", "price": "22.00", "emoji": "🪴", "description": "A little greenery to brighten up your workspace.", "badge": "Eco pick", "stock": 35},
    {"id": 7, "name": "Travel Bottle", "category": "Accessories", "price": "24.00", "emoji": "🧴", "description": "A reusable bottle made for busy days and weekend trips.", "badge": "", "stock": 28},
    {"id": 8, "name": "Minimal Notebook", "category": "Stationery", "price": "12.50", "emoji": "📓", "description": "A simple notebook for plans, ideas, and notes.", "badge": "", "stock": 50},
]


def initialize_database():
    """Create tables and seed sample products on the first startup."""
    with app.app_context():
        db.create_all()
        if Product.query.count() == 0:
            for item in SEED_PRODUCTS:
                db.session.add(Product(
                    id=item["id"],
                    name=item["name"],
                    category=item["category"],
                    price=Decimal(item["price"]),
                    emoji=item["emoji"],
                    description=item["description"],
                    badge=item["badge"],
                    stock=item["stock"],
                ))
            db.session.commit()


def cart_items():
    cart = session.get("cart", {})
    items = []
    for product_id, quantity in cart.items():
        product = db.session.get(Product, int(product_id))
        if product and quantity > 0:
            items.append({
                "product": product,
                "quantity": int(quantity),
                "line_total": product.price * int(quantity),
            })
    return items


def cart_total(items=None):
    items = cart_items() if items is None else items
    return sum((item["line_total"] for item in items), Decimal("0.00"))


@app.context_processor
def inject_cart_count():
    return {"cart_count": sum(int(q) for q in session.get("cart", {}).values())}


@app.route("/")
def index():
    category = request.args.get("category", "All")
    query = request.args.get("q", "").strip()
    categories = ["All"] + [
        row[0] for row in db.session.query(Product.category).distinct().order_by(Product.category).all()
    ]
    products_query = Product.query
    if category != "All":
        products_query = products_query.filter_by(category=category)
    if query:
        search = f"%{query}%"
        products_query = products_query.filter(
            db.or_(Product.name.ilike(search), Product.description.ilike(search), Product.category.ilike(search))
        )
    products = products_query.order_by(Product.id).all()
    return render_template(
        "index.html", products=products, categories=categories,
        selected_category=category, query=query
    )


@app.post("/cart/add/<int:product_id>")
def add_to_cart(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("index"))
    cart = session.get("cart", {})
    key = str(product_id)
    current_quantity = int(cart.get(key, 0))
    if current_quantity >= product.stock:
        flash("Sorry, no more stock is available for this item.", "error")
    else:
        cart[key] = current_quantity + 1
        session["cart"] = cart
        flash(f"{product.name} added to your cart.", "success")
    return redirect(request.referrer or url_for("index"))


@app.route("/cart")
def cart():
    items = cart_items()
    return render_template("cart.html", items=items, total=cart_total(items))


@app.post("/cart/update/<int:product_id>")
def update_cart(product_id):
    product = db.session.get(Product, product_id)
    cart = session.get("cart", {})
    key = str(product_id)
    try:
        quantity = int(request.form.get("quantity", "1"))
    except ValueError:
        quantity = 1

    if not product or quantity <= 0:
        cart.pop(key, None)
    else:
        cart[key] = min(quantity, product.stock)
    session["cart"] = cart
    return redirect(url_for("cart"))


@app.post("/cart/remove/<int:product_id>")
def remove_from_cart(product_id):
    cart = session.get("cart", {})
    cart.pop(str(product_id), None)
    session["cart"] = cart
    flash("Item removed from your cart.", "info")
    return redirect(url_for("cart"))


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    items = cart_items()
    if not items:
        flash("Your cart is empty.", "info")
        return redirect(url_for("index"))

    total = cart_total(items)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        if not name or not email or "@" not in email:
            flash("Please enter a valid name and email address.", "error")
            return render_template("checkout.html", items=items, total=total)

        # Recheck stock before creating an order.
        for item in items:
            if item["quantity"] > item["product"].stock:
                flash(f"Not enough stock for {item['product'].name}. Please update your cart.", "error")
                return redirect(url_for("cart"))

        order = Order(
            customer_name=name,
            email=email,
            total_amount=total,
            status="placed",
        )
        db.session.add(order)

        for item in items:
            product = item["product"]
            product.stock -= item["quantity"]
            db.session.add(OrderItem(
                order=order,
                product_id=product.id,
                product_name=product.name,
                quantity=item["quantity"],
                unit_price=product.price,
            ))

        db.session.commit()
        session["cart"] = {}
        return render_template("success.html", order=order)

    return render_template("checkout.html", items=items, total=total)


@app.get("/health")
def health():
    # Application-only health check; does not require database connectivity.
    return jsonify(status="ok"), 200


@app.get("/ready")
def ready():
    # Readiness check verifies the database can answer a simple query.
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify(status="ready", database="ok"), 200
    except Exception:
        db.session.rollback()
        return jsonify(status="not_ready", database="error"), 503


@app.get("/instance")
def instance_info():
    # Useful for observing which EC2 instance handles a request behind an ALB.
    return jsonify(hostname=socket.gethostname(), app="shopstack", status="ok"), 200


@app.get("/admin/orders")
def list_orders():
    # Practice endpoint only. Add real authentication before exposing this publicly.
    orders = Order.query.order_by(Order.id.desc()).limit(100).all()
    return render_template("orders.html", orders=orders)


if __name__ == "__main__":
    initialize_database()
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        debug=False,
    )
