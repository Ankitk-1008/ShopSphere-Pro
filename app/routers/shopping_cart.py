from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, insert, update, delete, func
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
)

from app.schemas.shopping_cart import (
    CartItemCreate,
    CartItemUpdate,
)


router = APIRouter(
    prefix="/shopping-cart",
    tags=["Module 17 - Shopping Cart Management"]
)


# ---------------- RBAC ----------------

def normalize_role(role):
    if hasattr(role, "value"):
        role = role.value

    if hasattr(role, "name"):
        role = role.name

    return str(role).strip().lower().replace("_", " ")


def require_customer(
    current_user=Depends(get_current_user)
):
    if normalize_role(current_user.role) != "customer":
        raise HTTPException(
            status_code=403,
            detail="Only customers can access shopping cart APIs"
        )

    return current_user


# ---------------- Helpers ----------------

def get_cart(db, cart_id, customer_id, lock=False):
    query = select(ShoppingCarts).where(
        ShoppingCarts.c.id == cart_id,
        ShoppingCarts.c.customer_id == customer_id
    )

    if lock:
        query = query.with_for_update()

    cart = db.execute(query).mappings().first()

    if not cart:
        raise HTTPException(
            status_code=404,
            detail="Shopping cart not found"
        )

    if cart["status"] != "active":
        raise HTTPException(
            status_code=400,
            detail="Shopping cart is not active"
        )

    return cart


def validate_product(db, product_id, variant_id):
    product = db.execute(
        select(Products).where(
            Products.c.id == product_id
        )
    ).mappings().first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    if not product["is_active"]:
        raise HTTPException(
            status_code=400,
            detail="Product is inactive"
        )

    if variant_id is not None:
        variant = db.execute(
            select(ProductVariants).where(
                ProductVariants.c.id == variant_id,
                ProductVariants.c.product_id == product_id
            )
        ).mappings().first()

        if not variant:
            raise HTTPException(
                status_code=404,
                detail="Variant does not belong to this product"
            )

        if not variant["is_active"]:
            raise HTTPException(
                status_code=400,
                detail="Product variant is inactive"
            )

    return product


def get_available_stock(db, product_id, variant_id):
    query = (
        select(
            func.coalesce(
                func.sum(WarehouseInventory.c.quantity), 0
            )
        )
        .select_from(
            WarehouseInventory.join(
                Warehouses,
                Warehouses.c.id == WarehouseInventory.c.warehouse_id
            )
        )
        .where(
            WarehouseInventory.c.product_id == product_id,
            Warehouses.c.status == "active"
        )
    )

    if variant_id is None:
        query = query.where(
            WarehouseInventory.c.variant_id.is_(None)
        )
    else:
        query = query.where(
            WarehouseInventory.c.variant_id == variant_id
        )

    return int(db.execute(query).scalar_one())


def get_cart_item(db, cart_id, product_id, variant_id, lock=False):
    query = select(ShoppingCartItems).where(
        ShoppingCartItems.c.cart_id == cart_id,
        ShoppingCartItems.c.product_id == product_id
    )

    if variant_id is None:
        query = query.where(
            ShoppingCartItems.c.variant_id.is_(None)
        )
    else:
        query = query.where(
            ShoppingCartItems.c.variant_id == variant_id
        )

    if lock:
        query = query.with_for_update()

    return db.execute(query).mappings().first()


def get_current_price(product):
    # Uses Products.base_price as the current catalog price.
    # Module 12 scheduled pricing can be integrated here later.
    try:
        price = Decimal(str(product["base_price"]))
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Product has an invalid base price"
        )

    if not price.is_finite() or price < 0:
        raise HTTPException(
            status_code=400,
            detail="Product price must be a valid non-negative amount"
        )

    return price


def get_cart_contents(db, cart_id):
    rows = db.execute(
        select(
            ShoppingCartItems.c.id.label("item_id"),
            ShoppingCartItems.c.product_id,
            ShoppingCartItems.c.variant_id,
            ShoppingCartItems.c.quantity,
            ShoppingCartItems.c.unit_price,
            Products.c.name.label("product_name"),
            Products.c.sku.label("product_sku"),
        )
        .select_from(
            ShoppingCartItems.join(
                Products,
                Products.c.id == ShoppingCartItems.c.product_id
            )
        )
        .where(ShoppingCartItems.c.cart_id == cart_id)
        .order_by(ShoppingCartItems.c.id.asc())
    ).mappings().all()

    items = []
    total = Decimal("0.00")

    for row in rows:
        unit_price = Decimal(str(row["unit_price"]))
        subtotal = unit_price * row["quantity"]
        total += subtotal

        items.append({
            "item_id": row["item_id"],
            "product_id": row["product_id"],
            "product_name": row["product_name"],
            "product_sku": row["product_sku"],
            "variant_id": row["variant_id"],
            "quantity": row["quantity"],
            "unit_price": str(unit_price),
            "subtotal": str(subtotal.quantize(Decimal("0.01")))
        })

    return items, total.quantize(Decimal("0.01"))


# ---------------- 1. Create Cart ----------------

@router.post(
    "/",
    status_code=status.HTTP_201_CREATED
)
def create_cart(
    db: Session = Depends(get_db),
    current_user=Depends(require_customer)
):
    try:
        result = db.execute(
            insert(ShoppingCarts).values(
                customer_id=current_user.id,
                status="active"
            )
        )

        cart_id = result.lastrowid
        db.commit()

        return {
            "message": "Shopping cart created successfully",
            "cart_id": cart_id,
            "customer_id": current_user.id,
            "status": "active"
        }

    except Exception:
        db.rollback()
        raise


# ---------------- 2. Get My Active Cart ----------------

@router.get("/my-cart")
def get_my_cart(
    db: Session = Depends(get_db),
    current_user=Depends(require_customer)
):
    cart = db.execute(
        select(ShoppingCarts)
        .where(
            ShoppingCarts.c.customer_id == current_user.id,
            ShoppingCarts.c.status == "active"
        )
        .order_by(ShoppingCarts.c.id.desc())
        .limit(1)
    ).mappings().first()

    if not cart:
        raise HTTPException(
            status_code=404,
            detail="No active cart found. Create a cart first."
        )

    items, total = get_cart_contents(db, cart["id"])

    return {
        "cart_id": cart["id"],
        "customer_id": cart["customer_id"],
        "status": cart["status"],
        "items": items,
        "total_items": sum(item["quantity"] for item in items),
        "total_amount": str(total)
    }


# ---------------- 3. Add Product to Cart ----------------

@router.post("/{cart_id}/items")
def add_cart_item(
    cart_id: int,
    data: CartItemCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_customer)
):
    try:
        get_cart(
            db, cart_id, current_user.id, lock=True
        )

        product = validate_product(
            db, data.product_id, data.variant_id
        )

        available = get_available_stock(
            db, data.product_id, data.variant_id
        )

        existing = get_cart_item(
            db,
            cart_id,
            data.product_id,
            data.variant_id,
            lock=True
        )

        existing_quantity = existing["quantity"] if existing else 0
        new_quantity = existing_quantity + data.quantity

        if new_quantity > available:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock. Available quantity: {available}"
            )

        unit_price = get_current_price(product)

        if existing:
            db.execute(
                update(ShoppingCartItems)
                .where(ShoppingCartItems.c.id == existing["id"])
                .values(
                    quantity=new_quantity,
                    unit_price=unit_price
                )
            )
        else:
            db.execute(
                insert(ShoppingCartItems).values(
                    cart_id=cart_id,
                    product_id=data.product_id,
                    variant_id=data.variant_id,
                    quantity=data.quantity,
                    unit_price=unit_price
                )
            )

        db.commit()

        return {
            "message": "Product added to cart successfully",
            "cart_id": cart_id,
            "product_id": data.product_id,
            "variant_id": data.variant_id,
            "quantity": new_quantity,
            "available_stock": available
        }

    except Exception:
        db.rollback()
        raise


# ---------------- 4. Update Cart Item Quantity ----------------

@router.patch("/{cart_id}/items/{item_id}")
def update_cart_item(
    cart_id: int,
    item_id: int,
    data: CartItemUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_customer)
):
    try:
        get_cart(
            db, cart_id, current_user.id, lock=True
        )

        item = db.execute(
            select(ShoppingCartItems).where(
                ShoppingCartItems.c.id == item_id,
                ShoppingCartItems.c.cart_id == cart_id
            ).with_for_update()
        ).mappings().first()

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Cart item not found"
            )

        available = get_available_stock(
            db, item["product_id"], item["variant_id"]
        )

        if data.quantity > available:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock. Available quantity: {available}"
            )

        product = validate_product(
            db, item["product_id"], item["variant_id"]
        )

        unit_price = get_current_price(product)

        db.execute(
            update(ShoppingCartItems)
            .where(ShoppingCartItems.c.id == item_id)
            .values(
                quantity=data.quantity,
                unit_price=unit_price
            )
        )

        db.commit()

        return {
            "message": "Cart item quantity updated successfully",
            "item_id": item_id,
            "quantity": data.quantity,
            "available_stock": available
        }

    except Exception:
        db.rollback()
        raise


# ---------------- 5. Remove Product from Cart ----------------

@router.delete("/{cart_id}/items/{item_id}")
def remove_cart_item(
    cart_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_customer)
):
    try:
        get_cart(
            db, cart_id, current_user.id, lock=True
        )

        item = db.execute(
            select(ShoppingCartItems.c.id).where(
                ShoppingCartItems.c.id == item_id,
                ShoppingCartItems.c.cart_id == cart_id
            )
        ).first()

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Cart item not found"
            )

        db.execute(
            delete(ShoppingCartItems).where(
                ShoppingCartItems.c.id == item_id
            )
        )

        db.commit()

        return {
            "message": "Product removed from cart successfully",
            "item_id": item_id
        }

    except Exception:
        db.rollback()
        raise


# ---------------- 6. Get Cart Contents and Total ----------------

@router.get("/{cart_id}")
def get_cart_details(
    cart_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_customer)
):
    cart = get_cart(
        db, cart_id, current_user.id
    )

    items, total = get_cart_contents(db, cart_id)

    return {
        "cart_id": cart_id,
        "customer_id": current_user.id,
        "status": cart["status"],
        "items": items,
        "total_items": sum(item["quantity"] for item in items),
        "total_amount": str(total)
    }


# ---------------- 7. Validate Cart Availability ----------------

@router.get("/{cart_id}/availability")
def validate_cart_availability(
    cart_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_customer)
):
    get_cart(db, cart_id, current_user.id)

    items = db.execute(
        select(ShoppingCartItems).where(
            ShoppingCartItems.c.cart_id == cart_id
        )
    ).mappings().all()

    results = []
    all_available = True

    for item in items:
        available = get_available_stock(
            db, item["product_id"], item["variant_id"]
        )

        is_available = available >= item["quantity"]

        if not is_available:
            all_available = False

        results.append({
            "item_id": item["id"],
            "product_id": item["product_id"],
            "variant_id": item["variant_id"],
            "cart_quantity": item["quantity"],
            "available_quantity": available,
            "is_available": is_available
        })

    return {
        "cart_id": cart_id,
        "all_items_available": all_available,
        "items": results
    }