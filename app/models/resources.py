
from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Numeric,
    func,
)

from app.core.database import Base


# Module 1 - Authentication resource
Auth = Table(
    "auth",
    Base.metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column(
        "updated_at",
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
    Column("email", String(500), nullable=True),
    Column("password_hash", String(500), nullable=True),
    Column("role", String(500), nullable=True),
    Column("is_active", Boolean, nullable=True),
)


# IMPORTANT:
# Do not define a generic Users table here.
# The users table is already defined in app/models/user.py
# using the User ORM model.


# Module 3 - Customer Registration



# Module 4 - Customer Profile Management
CustomerProfiles = Table(
    "customer_profiles",
    Base.metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column(
        "updated_at",
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
    Column("user_id", Integer, nullable=True),
    Column("first_name", String(500), nullable=True),
    Column("last_name", String(500), nullable=True),
    Column("phone", String(500), nullable=True),
    Column("date_of_birth", DateTime, nullable=True),
)


# Module 5 - Address Management
Addresses = Table(
    "addresses",
    Base.metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column(
        "updated_at",
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
    Column("user_id", Integer, nullable=True),
    Column("address_type", String(500), nullable=True),
    Column("line1", String(500), nullable=True),
    Column("line2", String(500), nullable=True),
    Column("city", String(500), nullable=True),
    Column("state", String(500), nullable=True),
    Column("postal_code", String(500), nullable=True),
    Column("country", String(500), nullable=True),
    Column("is_default", Boolean, nullable=True),
)


# Module 6 - Product Category Management
Categories = Table(
    "categories",
    Base.metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column(
        "updated_at",
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
    Column("name", String(500), nullable=True),
    Column("slug", String(500), nullable=True),
    Column("parent_id", Integer, nullable=True),
    Column("description", String(500), nullable=True),
    Column("is_active", Boolean, nullable=True),
)


# Module 7 - Brand Management
Brands = Table(
    "brands",
    Base.metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column(
        "updated_at",
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
    Column("name", String(500), nullable=True),
    Column("description", String(500), nullable=True),
    Column("website", String(500), nullable=True),
    Column("is_active", Boolean, nullable=True),
)


# Module 8 - Product Management
Products = Table(
    "products",
    Base.metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column(
        "updated_at",
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
    Column("name", String(500), nullable=True),
    Column("description", String(500), nullable=True),
    Column("sku", String(500), nullable=True),
    Column("category_id", Integer, nullable=True),
    Column("brand_id", Integer, nullable=True),
    Column("base_price", Numeric(12, 2), nullable=True),
    Column("is_active", Boolean, nullable=True),
)


# Module 9 - Product Variants
ProductVariants = Table(
    "product_variants",
    Base.metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column(
        "updated_at",
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
    Column("product_id", Integer, nullable=True),
    Column("sku", String(500), nullable=True),
    Column("size", String(500), nullable=True),
    Column("color", String(500), nullable=True),
    Column("price", String(500), nullable=True),
    Column("stock", Integer, nullable=True),
    Column("is_active", Boolean, nullable=True),
)


# Module 10 - Product Images and Documents
ProductMedia = Table(
    "product_media",
    Base.metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column(
        "updated_at",
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
    Column("product_id", Integer, nullable=True),
    Column("variant_id", Integer, nullable=True),
    Column("file_name", String(500), nullable=True),
    Column("file_path", String(500), nullable=True),
    Column("mime_type", String(500), nullable=True),
    Column("file_size", Integer, nullable=True),
)
