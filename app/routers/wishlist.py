
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, insert, delete, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user

from app.models.resources import (
    WishlistItems,
    Products,
    Warehouses,
    WarehouseInventory,
)

from app.schemas.wishlist import WishlistCreate


router = APIRouter(
    prefix="/wishlist",
    tags=["Module 19 - Wishlist Management"],
)


# -----------------------------------
# RBAC
# -----------------------------------

def get_role(user):
    role = getattr(user, "role", "")
    return (
        str(role)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def allow_roles(*roles):
    def checker(current_user=Depends(get_current_user)):
        if get_role(current_user) not in roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this resource",
            )
        return current_user

    return checker


CUSTOMER_ROLES = ("customer",)

WISHLIST_VIEW_ROLES = (
    "super_admin",
    "admin",
    "support_agent",
)


# -----------------------------------
# Product availability helper
# -----------------------------------

def get_available_stock(db, product_id):
    query = (
        select(
            func.coalesce(
                func.sum(WarehouseInventory.c.quantity),
                0,
            )
        )
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

    return int(db.execute(query).scalar() or 0)


def get_product(db, product_id):
    product = db.execute(
        select(Products).where(
            Products.c.id == product_id,
            Products.c.is_active == True,
        )
    ).mappings().first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found or inactive",
        )

    return product


# -----------------------------------
# Add product to wishlist
# -----------------------------------

@router.post(
    "/",
    status_code=201,
    dependencies=[Depends(allow_roles(*CUSTOMER_ROLES))],
)
def add_to_wishlist(
    payload: WishlistCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    product = get_product(db, payload.product_id)

    available_stock = get_available_stock(
        db,
        payload.product_id,
    )

    if available_stock <= 0:
        raise HTTPException(
            status_code=400,
            detail="Product is currently out of stock",
        )

    existing = db.execute(
        select(WishlistItems).where(
            WishlistItems.c.customer_id == current_user.id,
            WishlistItems.c.product_id == payload.product_id,
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Product already exists in your wishlist",
        )

    try:
        result = db.execute(
            insert(WishlistItems).values(
                customer_id=current_user.id,
                product_id=payload.product_id,
            )
        )
        db.commit()

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Product already exists in your wishlist",
        )

    return {
        "message": "Product added to wishlist successfully",
        "wishlist_item_id": result.inserted_primary_key[0],
        "product_id": product["id"],
        "product_name": product["name"],
        "available_stock": available_stock,
    }


# -----------------------------------
# Get my wishlist
# -----------------------------------

@router.get(
    "/my-wishlist",
    dependencies=[Depends(allow_roles(*CUSTOMER_ROLES))],
)
def get_my_wishlist(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rows = db.execute(
        select(
            WishlistItems.c.id.label("wishlist_item_id"),
            WishlistItems.c.product_id,
            WishlistItems.c.created_at,
            Products.c.name.label("product_name"),
            Products.c.sku,
            Products.c.description,
            Products.c.base_price,
            Products.c.is_active,
        )
        .select_from(
            WishlistItems.join(
                Products,
                WishlistItems.c.product_id == Products.c.id,
            )
        )
        .where(
            WishlistItems.c.customer_id == current_user.id
        )
        .order_by(WishlistItems.c.created_at.desc())
    ).mappings().all()

    result = []

    for row in rows:
        available_stock = get_available_stock(
            db,
            row["product_id"],
        )

        result.append({
            "wishlist_item_id": row["wishlist_item_id"],
            "product_id": row["product_id"],
            "product_name": row["product_name"],
            "sku": row["sku"],
            "description": row["description"],
            "current_base_price": (
                str(row["base_price"])
                if row["base_price"] is not None
                else None
            ),
            "is_active": row["is_active"],
            "available_stock": available_stock,
            "availability": (
                "available"
                if row["is_active"] and available_stock > 0
                else "unavailable"
            ),
            "saved_at": row["created_at"],
        })

    return {
        "customer_id": current_user.id,
        "total_items": len(result),
        "wishlist": result,
    }


# -----------------------------------
# Remove wishlist item
# -----------------------------------

@router.delete(
    "/{product_id}",
    dependencies=[Depends(allow_roles(*CUSTOMER_ROLES))],
)
def remove_from_wishlist(
    product_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = db.execute(
        delete(WishlistItems).where(
            WishlistItems.c.customer_id == current_user.id,
            WishlistItems.c.product_id == product_id,
        )
    )

    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail="Product not found in your wishlist",
        )

    db.commit()

    return {
        "message": "Product removed from wishlist successfully",
        "product_id": product_id,
    }


# -----------------------------------
# Admin / Support: view wishlists
# -----------------------------------

@router.get(
    "/all",
    dependencies=[Depends(allow_roles(*WISHLIST_VIEW_ROLES))],
)
def get_all_wishlists(
    customer_id: int = None,
    db: Session = Depends(get_db),
):
    query = (
        select(
            WishlistItems.c.id.label("wishlist_item_id"),
            WishlistItems.c.customer_id,
            WishlistItems.c.product_id,
            WishlistItems.c.created_at,
            Products.c.name.label("product_name"),
            Products.c.sku,
            Products.c.is_active,
        )
        .select_from(
            WishlistItems.join(
                Products,
                WishlistItems.c.product_id == Products.c.id,
            )
        )
    )

    if customer_id is not None:
        query = query.where(
            WishlistItems.c.customer_id == customer_id
        )

    rows = db.execute(
        query.order_by(WishlistItems.c.created_at.desc())
    ).mappings().all()

    result = []

    for row in rows:
        stock = get_available_stock(db, row["product_id"])

        result.append({
            "wishlist_item_id": row["wishlist_item_id"],
            "customer_id": row["customer_id"],
            "product_id": row["product_id"],
            "product_name": row["product_name"],
            "sku": row["sku"],
            "is_active": row["is_active"],
            "available_stock": stock,
            "availability": (
                "available"
                if row["is_active"] and stock > 0
                else "unavailable"
            ),
            "saved_at": row["created_at"],
        })

    return {
        "total_items": len(result),
        "wishlist_items": result,
    }


# -----------------------------------
# Check one saved product availability
# -----------------------------------

@router.get(
    "/availability/{product_id}",
    dependencies=[Depends(allow_roles(*CUSTOMER_ROLES))],
)
def check_wishlist_product_availability(
    product_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    saved_item = db.execute(
        select(WishlistItems).where(
            WishlistItems.c.customer_id == current_user.id,
            WishlistItems.c.product_id == product_id,
        )
    ).first()

    if not saved_item:
        raise HTTPException(
            status_code=404,
            detail="Product is not in your wishlist",
        )

    product = db.execute(
        select(Products).where(
            Products.c.id == product_id
        )
    ).mappings().first()

    if not product:
        return {
            "product_id": product_id,
            "availability": "unavailable",
            "reason": "Product no longer exists",
        }

    stock = get_available_stock(db, product_id)

    available = bool(product["is_active"]) and stock > 0

    return {
        "product_id": product_id,
        "product_name": product["name"],
        "is_active": product["is_active"],
        "available_stock": stock,
        "availability": "available" if available else "unavailable",
    }
