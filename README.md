# ShopStack — Flask e-commerce practice project

A responsive demo e-commerce website built with Python, Flask, Flask-SQLAlchemy, and SQLite. It is intended for local development and DevOps practice.

## Features

- Responsive product listing, category filters, and search
- Product data stored in a database (seeded on first start)
- Session-based shopping cart
- Quantity updates and item removal
- Demo checkout that saves orders and order items in the database
- Stock reduction when an order is placed
- `/health` application health endpoint
- `/ready` readiness endpoint that checks database connectivity
- `/instance` endpoint to see which server handled a request
- `/admin/orders` development view for recent orders (not protected; do not expose publicly as-is)

## Run locally in WSL Ubuntu

From this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

Test endpoints in another terminal:

```bash
curl http://127.0.0.1:5000/health
curl http://127.0.0.1:5000/ready
curl http://127.0.0.1:5000/instance
```

The SQLite database is created under `instance/shopstack.db` at first startup. Product records are seeded only when the product table is empty.

## Database configuration

By default the app uses SQLite for local practice:

```text
sqlite:///shopstack.db
```

To use PostgreSQL later, install a PostgreSQL driver and set `DATABASE_URL` to a PostgreSQL SQLAlchemy connection string. Keep credentials in environment variables or a secret manager, never in source control. For example, use a value shaped like:

```text
postgresql+psycopg://USERNAME:PASSWORD@HOST:5432/DATABASE_NAME
```

Install the optional driver when you are ready for PostgreSQL:

```bash
pip install "psycopg[binary]>=3.2,<4.0"
```

Then set `DATABASE_URL` in your environment before starting the app. Do not commit `.env` files or credentials.

## Notes for DevOps practice

- This project intentionally does not include a Dockerfile, Terraform, or AWS resources; build those yourself as practice.
- For AWS Auto Scaling, use a shared PostgreSQL database such as Amazon RDS rather than a local SQLite file on each EC2 instance.
- Use `/ready` for a database-aware readiness check and `/health` for a lightweight application liveness check.
- Before any public deployment, add authentication and authorization to `/admin/orders`, use a strong `SECRET_KEY`, configure HTTPS, validate inputs, and add database migrations/backups.
- Checkout is a demo flow only: it does not collect payments or arrange shipping.
