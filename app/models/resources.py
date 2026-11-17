
from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Numeric,
    JSON,
    UniqueConstraint,
    func,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,

)
from app.core.database import Base
from sqlalchemy import CheckConstraint

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


# =====================================================
# MODULE 11 - PRODUCT ATTRIBUTES
# =====================================================

ProductAttributes = Table(
    "product_attributes",
    Base.metadata,

    Column("id", Integer, primary_key=True, index=True),

    Column(
        "created_at",
        DateTime,
        nullable=False,
        server_default=func.now()
    ),

    Column(
        "updated_at",
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    ),

    Column("category_id", Integer, nullable=True),

    Column("name", String(100), nullable=False),

    Column("code", String(100), nullable=False),

    Column(
        "data_type",
        String(20),
        nullable=False,
        default="text"
    ),

    Column("allowed_values", JSON, nullable=True),

    Column(
        "is_required",
        Boolean,
        nullable=False,
        default=False
    ),

    Column(
        "is_active",
        Boolean,
        nullable=False,
        default=True
    ),
)


ProductAttributeValues = Table(
    "product_attribute_values",
    Base.metadata,

    Column("id", Integer, primary_key=True, index=True),

    Column(
        "created_at",
        DateTime,
        nullable=False,
        server_default=func.now()
    ),

    Column(
        "updated_at",
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    ),

    Column("product_id", Integer, nullable=False),

    Column("attribute_id", Integer, nullable=False),

    Column("value", String(500), nullable=False),

    UniqueConstraint(
        "product_id",
        "attribute_id",
        name="uq_product_attribute_value"
    ),
)



# =====================================================
# MODULE 12 - PRODUCT PRICING
# =====================================================

ProductPricing = Table(
    "product_pricing",
    Base.metadata,

    Column("id", Integer, primary_key=True, index=True),

    Column(
        "created_at",
        DateTime,
        nullable=False,
        server_default=func.now()
    ),

    Column(
        "updated_at",
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    ),

    Column("product_id", Integer, nullable=False),

    Column("base_price", Numeric(12, 2), nullable=False),

    Column("sale_price", Numeric(12, 2), nullable=True),

    Column("valid_from", DateTime, nullable=False),

    Column("valid_until", DateTime, nullable=True),

    Column("is_active", Boolean, nullable=False, default=True),

    Column("created_by", Integer, nullable=False),

    Column("reason", String(500), nullable=True),
)


ProductPriceHistory = Table(
    "product_price_history",
    Base.metadata,

    Column("id", Integer, primary_key=True, index=True),

    Column(
        "changed_at",
        DateTime,
        nullable=False,
        server_default=func.now()
    ),

    Column("product_id", Integer, nullable=False),

    Column("old_base_price", Numeric(12, 2), nullable=True),

    Column("new_base_price", Numeric(12, 2), nullable=False),

    Column("old_sale_price", Numeric(12, 2), nullable=True),

    Column("new_sale_price", Numeric(12, 2), nullable=True),

    Column("valid_from", DateTime, nullable=False),

    Column("valid_until", DateTime, nullable=True),

    Column("changed_by", Integer, nullable=False),

    Column("reason", String(500), nullable=True),
)



# =====================================================
# MODULE 13 - INVENTORY MANAGEMENT
# =====================================================

ProductInventory = Table(
    "product_inventory",
    Base.metadata,

    Column("id", Integer, primary_key=True, index=True),

    Column(
        "created_at",
        DateTime,
        nullable=False,
        server_default=func.now()
    ),

    Column(
        "updated_at",
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    ),

    Column(
        "product_id",
        Integer,
        ForeignKey("products.id"),
        nullable=False
    ),

    Column(
        "variant_id",
        Integer,
        ForeignKey("product_variants.id"),
        nullable=True
    ),

    Column(
        "available_quantity",
        Integer,
        nullable=False,
        default=0
    ),

    Column(
        "reserved_quantity",
        Integer,
        nullable=False,
        default=0
    ),

    Column(
        "is_active",
        Boolean,
        nullable=False,
        default=True
    ),

    UniqueConstraint(
        "product_id",
        "variant_id",
        name="uq_inventory_product_variant"
    ),

    CheckConstraint(
        "available_quantity >= 0",
        name="ck_inventory_available_nonnegative"
    ),

    CheckConstraint(
        "reserved_quantity >= 0",
        name="ck_inventory_reserved_nonnegative"
    ),
)


InventoryMovements = Table(
    "inventory_movements",
    Base.metadata,

    Column("id", Integer, primary_key=True, index=True),

    Column(
        "created_at",
        DateTime,
        nullable=False,
        server_default=func.now()
    ),

    Column(
        "product_id",
        Integer,
        ForeignKey("products.id"),
        nullable=False
    ),

    Column(
        "variant_id",
        Integer,
        ForeignKey("product_variants.id"),
        nullable=True
    ),

    Column(
        "movement_type",
        String(30),
        nullable=False
    ),

    Column(
        "quantity",
        Integer,
        nullable=False
    ),

    Column(
        "previous_available",
        Integer,
        nullable=False
    ),

    Column(
        "new_available",
        Integer,
        nullable=False
    ),

    Column(
        "previous_reserved",
        Integer,
        nullable=False
    ),

    Column(
        "new_reserved",
        Integer,
        nullable=False
    ),

    Column(
        "reference",
        String(100),
        nullable=True
    ),

    Column(
        "reason",
        String(500),
        nullable=True
    ),

    Column(
        "created_by",
        Integer,
        nullable=False
    ),

    CheckConstraint(
        "quantity > 0",
        name="ck_inventory_movement_quantity_positive"
    ),
)

# Module 14 - Warehouse Management

Warehouses = Table(
    "warehouses",
    Base.metadata,

    Column("id", Integer, primary_key=True, index=True),
    Column("name", String(150), nullable=False),
    Column("code", String(50), nullable=False, unique=True, index=True),
    Column("location", String(255), nullable=False),

    # Maximum number of stock units this warehouse can hold
    Column("capacity", Integer, nullable=False),

    Column("status", String(30), nullable=False, default="active"),

    Column(
        "created_at",
        DateTime,
        nullable=False,
        server_default=func.now()
    ),
    Column(
        "updated_at",
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    ),

    CheckConstraint("capacity >= 0", name="ck_warehouse_capacity"),
)


WarehouseInventory = Table(
    "warehouse_inventory",
    Base.metadata,

    Column("id", Integer, primary_key=True, index=True),

    Column(
        "warehouse_id",
        Integer,
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    ),

    Column(
        "product_id",
        Integer,
        ForeignKey("products.id"),
        nullable=False,
        index=True
    ),

    Column(
        "variant_id",
        Integer,
        ForeignKey("product_variants.id"),
        nullable=True,
        index=True
    ),

    Column("quantity", Integer, nullable=False, default=0),

    Column(
        "created_at",
        DateTime,
        nullable=False,
        server_default=func.now()
    ),
    Column(
        "updated_at",
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    ),

    CheckConstraint("quantity >= 0", name="ck_warehouse_stock_quantity"),
)

# Module 15 - Inventory Transfers

InventoryTransfers = Table(
    "inventory_transfers",
    Base.metadata,

    Column("id", Integer, primary_key=True, index=True),

    Column(
        "source_warehouse_id",
        Integer,
        ForeignKey("warehouses.id"),
        nullable=False
    ),

    Column(
        "destination_warehouse_id",
        Integer,
        ForeignKey("warehouses.id"),
        nullable=False
    ),

    Column(
        "product_id",
        Integer,
        ForeignKey("products.id"),
        nullable=False
    ),

    Column(
        "variant_id",
        Integer,
        ForeignKey("product_variants.id"),
        nullable=True
    ),

    Column("requested_quantity", Integer, nullable=False),
    Column("dispatched_quantity", Integer, nullable=False, default=0),
    Column("received_quantity", Integer, nullable=False, default=0),

    Column("status", String(30), nullable=False, default="requested"),

    Column("notes", String(500), nullable=True),

    Column("requested_by", Integer, nullable=False),
    Column("dispatched_by", Integer, nullable=True),
    Column("received_by", Integer, nullable=True),

    Column("requested_at", DateTime, nullable=False, server_default=func.now()),
    Column("dispatched_at", DateTime, nullable=True),
    Column("received_at", DateTime, nullable=True),

    CheckConstraint(
        "requested_quantity > 0",
        name="ck_transfer_requested_positive"
    ),
    CheckConstraint(
        "dispatched_quantity >= 0",
        name="ck_transfer_dispatched_nonnegative"
    ),
    CheckConstraint(
        "received_quantity >= 0",
        name="ck_transfer_received_nonnegative"
    ),
)


WarehouseTransferMovements = Table(
    "warehouse_transfer_movements",
    Base.metadata,

    Column("id", Integer, primary_key=True, index=True),

    Column(
        "transfer_id",
        Integer,
        ForeignKey("inventory_transfers.id"),
        nullable=False,
        index=True
    ),

    Column("action", String(30), nullable=False),
    Column("quantity", Integer, nullable=False),

    Column(
        "source_warehouse_id",
        Integer,
        ForeignKey("warehouses.id"),
        nullable=False
    ),

    Column(
        "destination_warehouse_id",
        Integer,
        ForeignKey("warehouses.id"),
        nullable=False
    ),

    Column("created_by", Integer, nullable=False),
    Column("notes", String(500), nullable=True),

    Column(
        "created_at",
        DateTime,
        nullable=False,
        server_default=func.now()
    ),

    CheckConstraint(
        "quantity > 0",
        name="ck_transfer_movement_quantity_positive"
    ),
)

# Module 16 - Low Stock Thresholds

LowStockThresholds = Table(
    "low_stock_thresholds",
    Base.metadata,

    Column("id", Integer, primary_key=True, index=True),

    Column(
        "warehouse_id",
        Integer,
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    ),

    Column(
        "product_id",
        Integer,
        ForeignKey("products.id"),
        nullable=False,
        index=True
    ),

    Column(
        "variant_id",
        Integer,
        ForeignKey("product_variants.id"),
        nullable=True,
        index=True
    ),

    Column("minimum_quantity", Integer, nullable=False),
    Column("is_active", Boolean, nullable=False, default=True),

    Column(
        "created_at",
        DateTime,
        nullable=False,
        server_default=func.now()
    ),

    Column(
        "updated_at",
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    ),

    CheckConstraint(
        "minimum_quantity >= 0",
        name="ck_low_stock_minimum_quantity"
    ),
)


LowStockAlerts = Table(
    "low_stock_alerts",
    Base.metadata,

    Column("id", Integer, primary_key=True, index=True),

    Column(
        "threshold_id",
        Integer,
        ForeignKey("low_stock_thresholds.id"),
        nullable=False,
        index=True
    ),

    Column("current_quantity", Integer, nullable=False),
    Column("minimum_quantity", Integer, nullable=False),

    Column("status", String(30), nullable=False, default="active"),
    Column("message", String(500), nullable=False),

    Column(
        "created_at",
        DateTime,
        nullable=False,
        server_default=func.now()
    ),

    Column("resolved_at", DateTime, nullable=True),
)


StockThresholdHistory = Table(
    "stock_threshold_history",
    Base.metadata,

    Column("id", Integer, primary_key=True, index=True),

    Column(
        "threshold_id",
        Integer,
        ForeignKey("low_stock_thresholds.id"),
        nullable=False,
        index=True
    ),

    Column("old_minimum_quantity", Integer, nullable=True),
    Column("new_minimum_quantity", Integer, nullable=False),

    Column("changed_by", Integer, nullable=False),
    Column("reason", String(500), nullable=True),

    Column(
        "created_at",
        DateTime,
        nullable=False,
        server_default=func.now()
    ),
)


# Module 17 - Shopping Cart Management

ShoppingCarts = Table(
    "shopping_carts",
    Base.metadata,

    Column("id", Integer, primary_key=True, index=True),

    Column(
        "customer_id",
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    ),

    Column(
        "status",
        String(30),
        nullable=False,
        default="active"
    ),

    Column(
        "created_at",
        DateTime,
        nullable=False,
        server_default=func.now()
    ),

    Column(
        "updated_at",
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    ),
)


ShoppingCartItems = Table(
    "shopping_cart_items",
    Base.metadata,

    Column("id", Integer, primary_key=True, index=True),

    Column(
        "cart_id",
        Integer,
        ForeignKey("shopping_carts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    ),

    Column(
        "product_id",
        Integer,
        ForeignKey("products.id"),
        nullable=False,
        index=True
    ),

    Column(
        "variant_id",
        Integer,
        ForeignKey("product_variants.id"),
        nullable=True,
        index=True
    ),

    Column("quantity", Integer, nullable=False, default=1),

    # Price snapshot when the item is added or updated
    Column("unit_price", Numeric(12, 2), nullable=False),

    Column(
        "created_at",
        DateTime,
        nullable=False,
        server_default=func.now()
    ),

    Column(
        "updated_at",
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    ),

    CheckConstraint(
        "quantity > 0",
        name="ck_cart_item_quantity_positive"
    ),

    CheckConstraint(
        "unit_price >= 0",
        name="ck_cart_item_unit_price_nonnegative"
    ),
)


# Module 18 - Cart Price Calculation

DiscountCodes = Table(
    "discount_codes",
    Base.metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("code", String(50), nullable=False, unique=True, index=True),
    Column("discount_type", String(20), nullable=False),
    Column("discount_value", Numeric(12, 2), nullable=False),
    Column("min_order_amount", Numeric(12, 2), nullable=False, server_default="0"),
    Column("max_discount", Numeric(12, 2), nullable=True),
    Column("is_active", Boolean, nullable=False, server_default="1"),
    Column("starts_at", DateTime, nullable=True),
    Column("ends_at", DateTime, nullable=True),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    CheckConstraint(
        "discount_type IN ('percentage', 'fixed')",
        name="ck_discount_type"
    ),
    CheckConstraint("discount_value > 0", name="ck_discount_value_positive"),
    CheckConstraint("min_order_amount >= 0", name="ck_discount_min_order"),
)

CheckoutSettings = Table(
    "checkout_settings",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("shipping_charge", Numeric(12, 2), nullable=False, server_default="50.00"),
    Column("free_shipping_threshold", Numeric(12, 2), nullable=False, server_default="1000.00"),
    Column("tax_percentage", Numeric(5, 2), nullable=False, server_default="18.00"),
    Column("updated_at", DateTime, nullable=False, server_default=func.now()),
    CheckConstraint("shipping_charge >= 0", name="ck_shipping_charge"),
    CheckConstraint("free_shipping_threshold >= 0", name="ck_free_shipping_threshold"),
    CheckConstraint("tax_percentage >= 0 AND tax_percentage <= 100", name="ck_tax_percentage"),
)



# Module 19 - Wishlist Management

WishlistItems = Table(
    "wishlist_items",
    Base.metadata,

    Column("id", Integer, primary_key=True, index=True),

    Column(
        "customer_id",
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),

    Column(
        "product_id",
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    ),

    Column(
        "created_at",
        DateTime,
        nullable=False,
        server_default=func.now(),
    ),

    UniqueConstraint(
        "customer_id",
        "product_id",
        name="uq_wishlist_customer_product",
    ),
)
