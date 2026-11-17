
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, insert, update, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user

from app.models.resources import (
    ShoppingCarts,
    ShoppingCartItems,
    Products,
    ProductVariants,
    Warehouses,
    WarehouseInventory,
    DiscountCodes,
    CheckoutSettings,
)

from app.schemas.cart_pricing import (
    CheckoutCalculate,
    DiscountCreate,
    CheckoutSettingsUpdate,
)


router = APIRouter(
    prefix="/cart-pricing",
    tags=["Module 18 - Cart Price Calculation"],
)


# -------------------------------
# RBAC
# -------------------------------

def get_role(user):
    role = getattr(user, "role", "")
    return str(role).strip().lower().replace(" ", "_").replace("-", "_")


def allow_roles(*roles):
    def checker(current_user=Depends(get_current_user)):
        if get_role(current_user) not in roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to perform this action",
            )
        return current_user
    return checker


CUSTOMER_ROLES = ("customer",)

DISCOUNT_MANAGERS = (
    "super_admin",
    "admin",
    "product_manager",
    "finance_manager",
)

SETTINGS_MANAGERS = (
    "super_admin",
    "admin",
    "finance_manager",
)

SUMMARY_READERS = (
    "customer",
    "super_admin",
    "admin",
    "order_manager",
)


# -------------------------------
# Helpers
# -------------------------------

def money(value):
    return Decimal(str(value or 0)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def now_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_owned_cart(db, cart_id, user_id):
    cart = db.execute(
        select(ShoppingCarts).where(
            ShoppingCarts.c.id == cart_id,
            ShoppingCarts.c.customer_id == user_id,
            ShoppingCarts.c.status == "active",
        )
    ).mappings().first()

    if not cart:
        raise HTTPException(
            status_code=404,
            detail="Active cart not found",
        )

    return cart


def get_current_product_price(db, product, variant_id):
    """
    Server-side price source.

    This implementation uses Products.base_price.
    If Module 12 ProductPricing is your active pricing source,
    replace this helper with its current-price lookup.
    """

    if variant_id:
        variant = db.execute(
            select(ProductVariants).where(
                ProductVariants.c.id == variant_id,
                ProductVariants.c.product_id == product["id"],
                ProductVariants.c.is_active == True,
            )
        ).mappings().first()

        if not variant:
            raise HTTPException(
                status_code=400,
                detail=f"Variant {variant_id} is unavailable",
            )

        # This project stores variant price as String.
        # Use variant price when it contains a valid positive amount.
        if variant.get("price"):
            try:
                variant_price = Decimal(str(variant["price"]))
                if variant_price >= 0:
                    return money(variant_price)
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid price configured for variant {variant_id}",
                )

    return money(product["base_price"])


def get_available_stock(db, product_id, variant_id):
    query = (
        select(func.coalesce(func.sum(WarehouseInventory.c.quantity), 0))
        .select_from(
            WarehouseInventory.join(
                Warehouses,
                WarehouseInventory.c.warehouse_id == Warehouses.c.id,
            )
        )
        .where(
            WarehouseInventory.c.product_id == product_id,
            Warehouses.c.status == "active",
        )
    )

    if variant_id is None:
        query = query.where(WarehouseInventory.c.variant_id.is_(None))
    else:
        query = query.where(
            WarehouseInventory.c.variant_id == variant_id
        )

    return int(db.execute(query).scalar() or 0)


def get_discount(db, discount_code, subtotal):
    if not discount_code:
        return Decimal("0.00"), None

    code = discount_code.strip().upper()

    discount = db.execute(
        select(DiscountCodes).where(
            func.upper(DiscountCodes.c.code) == code,
            DiscountCodes.c.is_active == True,
        )
    ).mappings().first()

    if not discount:
        raise HTTPException(
            status_code=400,
            detail="Invalid or inactive discount code",
        )

    current_time = now_utc()

    if discount["starts_at"] and current_time < discount["starts_at"]:
        raise HTTPException(
            status_code=400,
            detail="Discount code is not active yet",
        )

    if discount["ends_at"] and current_time > discount["ends_at"]:
        raise HTTPException(
            status_code=400,
            detail="Discount code has expired",
        )

    if subtotal < money(discount["min_order_amount"]):
        raise HTTPException(
            status_code=400,
            detail="Minimum order amount not reached for this discount",
        )

    discount_value = money(discount["discount_value"])

    if discount["discount_type"] == "percentage":
        if discount_value > 100:
            raise HTTPException(
                status_code=400,
                detail="Percentage discount cannot exceed 100",
            )

        amount = money(subtotal * discount_value / Decimal("100"))

        if discount["max_discount"] is not None:
            amount = min(amount, money(discount["max_discount"]))

    else:
        amount = discount_value

    amount = min(amount, subtotal)

    return money(amount), discount["code"]


def get_checkout_settings(db):
    settings = db.execute(
        select(CheckoutSettings).where(
            CheckoutSettings.c.id == 1
        )
    ).mappings().first()

    if not settings:
        db.execute(
            insert(CheckoutSettings).values(
                id=1,
                shipping_charge=Decimal("50.00"),
                free_shipping_threshold=Decimal("1000.00"),
                tax_percentage=Decimal("18.00"),
            )
        )
        db.commit()

        settings = db.execute(
            select(CheckoutSettings).where(
                CheckoutSettings.c.id == 1
            )
        ).mappings().first()

    return settings


# -------------------------------
# Customer checkout summary
# -------------------------------

@router.post(
    "/{cart_id}/summary",
    dependencies=[Depends(allow_roles(*SUMMARY_READERS))],
)
def calculate_checkout_summary(
    cart_id: int,
    payload: CheckoutCalculate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Customers can only access their own cart.
    if get_role(current_user) == "customer":
        cart = get_owned_cart(db, cart_id, current_user.id)
    else:
        cart = db.execute(
            select(ShoppingCarts).where(
                ShoppingCarts.c.id == cart_id,
                ShoppingCarts.c.status == "active",
            )
        ).mappings().first()

        if not cart:
            raise HTTPException(status_code=404, detail="Cart not found")

    items = db.execute(
        select(ShoppingCartItems).where(
            ShoppingCartItems.c.cart_id == cart_id
        )
    ).mappings().all()

    if not items:
        raise HTTPException(
            status_code=400,
            detail="Shopping cart is empty",
        )

    item_details = []
    subtotal = Decimal("0.00")

    for item in items:
        product = db.execute(
            select(Products).where(
                Products.c.id == item["product_id"],
                Products.c.is_active == True,
            )
        ).mappings().first()

        if not product:
            raise HTTPException(
                status_code=400,
                detail=f"Product {item['product_id']} is unavailable",
            )

        current_price = get_current_product_price(
            db,
            product,
            item["variant_id"],
        )

        available_stock = get_available_stock(
            db,
            item["product_id"],
            item["variant_id"],
        )

        if item["quantity"] > available_stock:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Insufficient stock for product {product['name']}. "
                    f"Available: {available_stock}"
                ),
            )

        item_subtotal = money(current_price * item["quantity"])
        subtotal += item_subtotal

        item_details.append({
            "cart_item_id": item["id"],
            "product_id": product["id"],
            "product_name": product["name"],
            "variant_id": item["variant_id"],
            "quantity": item["quantity"],
            "current_unit_price": str(current_price),
            "item_subtotal": str(item_subtotal),
            "available_stock": available_stock,
        })

    subtotal = money(subtotal)

    discount_amount, applied_code = get_discount(
        db,
        payload.discount_code,
        subtotal,
    )

    discounted_subtotal = money(subtotal - discount_amount)

    settings = get_checkout_settings(db)

    shipping_charge = money(settings["shipping_charge"])
    free_shipping_threshold = money(
        settings["free_shipping_threshold"]
    )

    if discounted_subtotal >= free_shipping_threshold:
        shipping_charge = Decimal("0.00")

    tax_percentage = Decimal(str(settings["tax_percentage"]))

    # Tax is calculated on discounted item subtotal.
    # Shipping is excluded from the tax base in this example.
    tax_amount = money(
        discounted_subtotal * tax_percentage / Decimal("100")
    )

    grand_total = money(
        discounted_subtotal + shipping_charge + tax_amount
    )

    return {
        "cart_id": cart_id,
        "currency": "INR",
        "items": item_details,
        "price_summary": {
            "subtotal": str(subtotal),
            "discount_code": applied_code,
            "discount_amount": str(discount_amount),
            "discounted_subtotal": str(discounted_subtotal),
            "shipping_charge": str(shipping_charge),
            "tax_percentage": str(tax_percentage),
            "tax_amount": str(tax_amount),
            "grand_total": str(grand_total),
        },
        "message": "Checkout summary calculated successfully",
        "note": (
            "This is a price estimate. Stock is not reserved and "
            "payment has not been processed."
        ),
    }


# -------------------------------
# Admin: create discount
# -------------------------------

@router.post(
    "/discounts",
    dependencies=[Depends(allow_roles(*DISCOUNT_MANAGERS))],
)
def create_discount(
    payload: DiscountCreate,
    db: Session = Depends(get_db),
):
    code = payload.code.strip().upper()
    discount_type = payload.discount_type.strip().lower()

    if discount_type not in ("percentage", "fixed"):
        raise HTTPException(
            status_code=400,
            detail="discount_type must be percentage or fixed",
        )

    if discount_type == "percentage" and payload.discount_value > 100:
        raise HTTPException(
            status_code=400,
            detail="Percentage discount cannot exceed 100",
        )

    existing = db.execute(
        select(DiscountCodes).where(
            func.upper(DiscountCodes.c.code) == code
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Discount code already exists",
        )

    result = db.execute(
        insert(DiscountCodes).values(
            code=code,
            discount_type=discount_type,
            discount_value=payload.discount_value,
            min_order_amount=payload.min_order_amount,
            max_discount=payload.max_discount,
            is_active=True,
        )
    )

    db.commit()

    return {
        "message": "Discount created successfully",
        "discount_id": result.inserted_primary_key[0],
        "code": code,
    }


# -------------------------------
# Admin: list discounts
# -------------------------------

@router.get(
    "/discounts",
    dependencies=[Depends(allow_roles(*DISCOUNT_MANAGERS))],
)
def list_discounts(db: Session = Depends(get_db)):
    rows = db.execute(
        select(DiscountCodes).order_by(DiscountCodes.c.id.desc())
    ).mappings().all()

    return [dict(row) for row in rows]


# -------------------------------
# Admin: deactivate discount
# -------------------------------

@router.patch(
    "/discounts/{discount_id}/deactivate",
    dependencies=[Depends(allow_roles(*DISCOUNT_MANAGERS))],
)
def deactivate_discount(
    discount_id: int,
    db: Session = Depends(get_db),
):
    result = db.execute(
        update(DiscountCodes)
        .where(DiscountCodes.c.id == discount_id)
        .values(is_active=False)
    )

    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail="Discount not found",
        )

    db.commit()

    return {"message": "Discount deactivated successfully"}


# -------------------------------
# Finance/Admin: update checkout settings
# -------------------------------

@router.put(
    "/settings",
    dependencies=[Depends(allow_roles(*SETTINGS_MANAGERS))],
)
def update_checkout_settings(
    payload: CheckoutSettingsUpdate,
    db: Session = Depends(get_db),
):
    get_checkout_settings(db)

    db.execute(
        update(CheckoutSettings)
        .where(CheckoutSettings.c.id == 1)
        .values(
            shipping_charge=payload.shipping_charge,
            free_shipping_threshold=payload.free_shipping_threshold,
            tax_percentage=payload.tax_percentage,
            updated_at=now_utc(),
        )
    )

    db.commit()

    return {
        "message": "Checkout settings updated successfully",
        "shipping_charge": str(payload.shipping_charge),
        "free_shipping_threshold": str(payload.free_shipping_threshold),
        "tax_percentage": str(payload.tax_percentage),
    }


@router.get(
    "/settings",
    dependencies=[Depends(allow_roles(*SETTINGS_MANAGERS))],
)
def read_checkout_settings(db: Session = Depends(get_db)):
    settings = get_checkout_settings(db)
    return dict(settings)
