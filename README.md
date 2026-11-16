# ShopSphere Pro — Day 1 package

    This is a cumulative package: it contains modules 1–10, so use it as the project folder for this day.

    ## Modules included
    | No. | Module | Resource endpoint |
    |---:|---|---|
    | 1 | Authentication and Authorization | `/auth` |
| 2 | User Management | `/users` |
| 3 | Customer Registration | `/customer_registrations` |
| 4 | Customer Profile Management | `/customer_profiles` |
| 5 | Address Management | `/addresses` |
| 6 | Product Category Management | `/categories` |
| 7 | Brand Management | `/brands` |
| 8 | Product Management | `/products` |
| 9 | Product Variants | `/product_variants` |
| 10 | Product Images and Documents | `/product_media` |

    ## Windows / PowerShell setup
    1. Extract this ZIP.
    2. Open the extracted folder in VS Code.
    3. Create environment: `py -3.12 -m venv .venv`
    4. Activate: `.\.venv\Scripts\Activate.ps1`
    5. Install: `python -m pip install -r requirements.txt`
    6. Copy `.env.example` to `.env` and set your local MySQL password and a long random SECRET_KEY.
    7. Create database in MySQL: `CREATE DATABASE shopsphere_pro_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`
    8. Start: `uvicorn app.main:app --reload`
    9. Swagger: `http://127.0.0.1:8000/docs`

    ## Authentication test
    - `POST /api/v1/auth/register` with email and password (minimum 8 characters).
    - `POST /api/v1/auth/login` with same credentials.
    - Click Swagger **Authorize** and enter the access token as `Bearer <token>` if Swagger asks for it.
    - First registered account is a Customer. For local development only, promote your test account in MySQL:
      `UPDATE auth_users SET role='Super Admin' WHERE email='your-email@example.com';`
      Log in again after changing the role.

    ## CRUD endpoints (all listed business resources)
    - `POST /api/v1/{resource}` — create
    - `GET /api/v1/{resource}` — list (supports `skip`, `limit`)
    - `GET /api/v1/{resource}/{item_id}` — read one
    - `PUT /api/v1/{resource}/{item_id}` — update supplied fields
    - `PATCH /api/v1/{resource}/{item_id}` — partial update (body must not be empty)
    - `DELETE /api/v1/{resource}/{item_id}` — delete (Super Admin/Admin only)

    Resource names: auth, users, customer_registrations, customer_profiles, addresses, categories, brands, products, product_variants, product_media.

    ## Database migrations
    For quick local learning, `Base.metadata.create_all()` creates the tables on startup.
    To use Alembic migrations instead, remove that startup call from `app/main.py`, then run:
    `alembic revision --autogenerate -m "day 1 schema"`
    `alembic upgrade head`

    ## Important scope / production notes
    - Models are real SQLAlchemy tables with typed columns and persistent MySQL CRUD, not in-memory mock data.
    - The common CRUD router provides POST/GET/PUT/PATCH/DELETE for each resource.
    - This package is a learning foundation, not yet a production-complete implementation of every business rule in the task. Modules such as checkout, stock reservation, Stripe webhooks, refunds, return eligibility, notifications, audit immutability, and exports need dedicated service logic and workflow tests before production. Do not expose it publicly with real customer/payment data.
    - `PUT` and `PATCH` currently update supplied fields; `PATCH` allows a subset. For strict full-replacement PUT semantics and module-specific Pydantic validation, implement the per-module schemas in the next refinement.
