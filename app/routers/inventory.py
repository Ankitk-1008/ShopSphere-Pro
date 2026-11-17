
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy import (
    select,
    insert,
    update,
    and_,
)

from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user

from app.models.resources import (
    Products,
    ProductVariants,
    ProductInventory,
    InventoryMovements,
)

from app.schemas.inventory import StockAction


router = APIRouter(
    prefix="/inventory",
    tags=["Module 13 - Inventory Management"]
)


# =====================================================
# 1. RBAC
# =====================================================

STOCK_VIEW_ROLES = (
    "super admin",
    "admin",
    "product manager",
    "inventory manager",
    "order manager",
    "support agent",
    "delivery manager",
    "finance manager",
    "customer",
)

STOCK_MANAGEMENT_ROLES = (
    "super admin",
    "admin",
    "inventory manager",
)

STOCK_RESERVATION_ROLES = (
    "super admin",
    "admin",
    "inventory manager",
    "order manager",
)

STOCK_HISTORY_ROLES = (
    "super admin",
    "admin",
    "inventory manager",
    "order manager",
    "finance manager",
)


def normalize_role(role):

    if isinstance(role, str):

        return (
            role.strip()
            .replace("_", " ")
            .replace("-", " ")
            .casefold()
        )

    return (
        str(getattr(role, "name", ""))
        .strip()
        .replace("_", " ")
        .replace("-", " ")
        .casefold()
    )


def require_roles(*allowed_roles):

    def role_checker(
        current_user=Depends(get_current_user)
    ):

        user_role = normalize_role(
            getattr(current_user, "role", None)
        )

        permitted_roles = [
            normalize_role(role)
            for role in allowed_roles
        ]

        if user_role not in permitted_roles:

            raise HTTPException(
                status_code=403,
                detail="You do not have permission to perform this action"
            )

        return current_user

    return role_checker


# =====================================================
# 2. VALIDATE PRODUCT AND VARIANT
# =====================================================

def validate_product_variant(
    product_id,
    variant_id,
    db
):

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

    if variant_id is not None:

        variant = db.execute(
            select(ProductVariants).where(
                and_(
                    ProductVariants.c.id == variant_id,
                    ProductVariants.c.product_id == product_id
                )
            )
        ).mappings().first()

        if not variant:

            raise HTTPException(
                status_code=404,
                detail="Product variant not found for this product"
            )

        return product, variant

    return product, None


# =====================================================
# 3. GET INVENTORY RECORD WITH LOCK
# =====================================================

def get_inventory_record(
    product_id,
    variant_id,
    db
):

    query = select(ProductInventory).where(
        ProductInventory.c.product_id == product_id
    )

    if variant_id is None:

        query = query.where(
            ProductInventory.c.variant_id.is_(None)
        )

    else:

        query = query.where(
            ProductInventory.c.variant_id == variant_id
        )

    # Lock row during stock changes to prevent
    # concurrent transactions from using the same stock.

    query = query.with_for_update()

    return db.execute(
        query
    ).mappings().first()


# =====================================================
# 4. CREATE INVENTORY RECORD IF NEEDED
# =====================================================

def create_inventory_if_missing(
    product_id,
    variant_id,
    db
):

    inventory = get_inventory_record(
        product_id,
        variant_id,
        db
    )

    if inventory:

        return inventory

    result = db.execute(
        insert(ProductInventory).values(
            product_id=product_id,
            variant_id=variant_id,
            available_quantity=0,
            reserved_quantity=0,
            is_active=True
        )
    )

    inventory_id = result.inserted_primary_key[0]

    return db.execute(
        select(ProductInventory)
        .where(ProductInventory.c.id == inventory_id)
        .with_for_update()
    ).mappings().first()


# =====================================================
# 5. RECORD INVENTORY MOVEMENT
# =====================================================

def record_movement(
    product_id,
    variant_id,
    movement_type,
    quantity,
    previous_available,
    new_available,
    previous_reserved,
    new_reserved,
    current_user,
    reason,
    reference,
    db
):

    db.execute(
        insert(InventoryMovements).values(
            product_id=product_id,
            variant_id=variant_id,
            movement_type=movement_type,
            quantity=quantity,
            previous_available=previous_available,
            new_available=new_available,
            previous_reserved=previous_reserved,
            new_reserved=new_reserved,
            created_by=current_user.id,
            reason=reason,
            reference=reference
        )
    )


# =====================================================
# 6. SYNC VARIANT STOCK
# =====================================================

def sync_variant_stock(
    variant_id,
    available,
    reserved,
    db
):

    if variant_id is None:
        return

    db.execute(
        update(ProductVariants)
        .where(ProductVariants.c.id == variant_id)
        .values(
            stock=available + reserved
        )
    )


# =====================================================
# 7. ADD STOCK
# POST /inventory/add
# =====================================================

@router.post(
    "/add",
    status_code=201,
    dependencies=[
        Depends(require_roles(*STOCK_MANAGEMENT_ROLES))
    ]
)
def add_stock(
    data: StockAction,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    try:

        validate_product_variant(
            data.product_id,
            data.variant_id,
            db
        )

        inventory = create_inventory_if_missing(
            data.product_id,
            data.variant_id,
            db
        )

        if not inventory["is_active"]:

            raise HTTPException(
                status_code=400,
                detail="Inventory record is inactive"
            )

        old_available = inventory["available_quantity"]
        old_reserved = inventory["reserved_quantity"]

        new_available = old_available + data.quantity

        db.execute(
            update(ProductInventory)
            .where(
                ProductInventory.c.id == inventory["id"]
            )
            .values(
                available_quantity=new_available
            )
        )

        sync_variant_stock(
            data.variant_id,
            new_available,
            old_reserved,
            db
        )

        record_movement(
            data.product_id,
            data.variant_id,
            "stock_added",
            data.quantity,
            old_available,
            new_available,
            old_reserved,
            old_reserved,
            current_user,
            data.reason,
            data.reference,
            db
        )

        db.commit()

        return {
            "message": "Stock added successfully",
            "product_id": data.product_id,
            "variant_id": data.variant_id,
            "added_quantity": data.quantity,
            "available_quantity": new_available,
            "reserved_quantity": old_reserved
        }

    except Exception:
        db.rollback()
        raise


# =====================================================
# 8. REDUCE STOCK
# POST /inventory/reduce
# =====================================================

@router.post(
    "/reduce",
    dependencies=[
        Depends(require_roles(*STOCK_MANAGEMENT_ROLES))
    ]
)
def reduce_stock(
    data: StockAction,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    try:

        validate_product_variant(
            data.product_id,
            data.variant_id,
            db
        )

        inventory = get_inventory_record(
            data.product_id,
            data.variant_id,
            db
        )

        if not inventory:

            raise HTTPException(
                status_code=404,
                detail="Inventory record not found"
            )

        if not inventory["is_active"]:

            raise HTTPException(
                status_code=400,
                detail="Inventory record is inactive"
            )

        old_available = inventory["available_quantity"]
        old_reserved = inventory["reserved_quantity"]

        if old_available < data.quantity:

            raise HTTPException(
                status_code=400,
                detail="Insufficient available stock. Negative inventory is not allowed."
            )

        new_available = old_available - data.quantity

        db.execute(
            update(ProductInventory)
            .where(
                ProductInventory.c.id == inventory["id"]
            )
            .values(
                available_quantity=new_available
            )
        )

        sync_variant_stock(
            data.variant_id,
            new_available,
            old_reserved,
            db
        )

        record_movement(
            data.product_id,
            data.variant_id,
            "stock_reduced",
            data.quantity,
            old_available,
            new_available,
            old_reserved,
            old_reserved,
            current_user,
            data.reason,
            data.reference,
            db
        )

        db.commit()

        return {
            "message": "Stock reduced successfully",
            "product_id": data.product_id,
            "variant_id": data.variant_id,
            "reduced_quantity": data.quantity,
            "available_quantity": new_available,
            "reserved_quantity": old_reserved
        }

    except Exception:
        db.rollback()
        raise


# =====================================================
# 9. RESERVE STOCK
# POST /inventory/reserve
# =====================================================

@router.post(
    "/reserve",
    dependencies=[
        Depends(require_roles(*STOCK_RESERVATION_ROLES))
    ]
)
def reserve_stock(
    data: StockAction,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    try:

        validate_product_variant(
            data.product_id,
            data.variant_id,
            db
        )

        inventory = get_inventory_record(
            data.product_id,
            data.variant_id,
            db
        )

        if not inventory:

            raise HTTPException(
                status_code=404,
                detail="Inventory record not found"
            )

        if not inventory["is_active"]:

            raise HTTPException(
                status_code=400,
                detail="Inventory record is inactive"
            )

        old_available = inventory["available_quantity"]
        old_reserved = inventory["reserved_quantity"]

        if old_available < data.quantity:

            raise HTTPException(
                status_code=400,
                detail="Insufficient available stock to reserve"
            )

        new_available = old_available - data.quantity
        new_reserved = old_reserved + data.quantity

        db.execute(
            update(ProductInventory)
            .where(
                ProductInventory.c.id == inventory["id"]
            )
            .values(
                available_quantity=new_available,
                reserved_quantity=new_reserved
            )
        )

        sync_variant_stock(
            data.variant_id,
            new_available,
            new_reserved,
            db
        )

        record_movement(
            data.product_id,
            data.variant_id,
            "stock_reserved",
            data.quantity,
            old_available,
            new_available,
            old_reserved,
            new_reserved,
            current_user,
            data.reason,
            data.reference,
            db
        )

        db.commit()

        return {
            "message": "Stock reserved successfully",
            "available_quantity": new_available,
            "reserved_quantity": new_reserved
        }

    except Exception:
        db.rollback()
        raise


# =====================================================
# 10. RELEASE RESERVED STOCK
# POST /inventory/release
# =====================================================

@router.post(
    "/release",
    dependencies=[
        Depends(require_roles(*STOCK_RESERVATION_ROLES))
    ]
)
def release_reserved_stock(
    data: StockAction,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    try:

        validate_product_variant(
            data.product_id,
            data.variant_id,
            db
        )

        inventory = get_inventory_record(
            data.product_id,
            data.variant_id,
            db
        )

        if not inventory:

            raise HTTPException(
                status_code=404,
                detail="Inventory record not found"
            )

        old_available = inventory["available_quantity"]
        old_reserved = inventory["reserved_quantity"]

        if old_reserved < data.quantity:

            raise HTTPException(
                status_code=400,
                detail="Insufficient reserved stock"
            )

        new_available = old_available + data.quantity
        new_reserved = old_reserved - data.quantity

        db.execute(
            update(ProductInventory)
            .where(
                ProductInventory.c.id == inventory["id"]
            )
            .values(
                available_quantity=new_available,
                reserved_quantity=new_reserved
            )
        )

        sync_variant_stock(
            data.variant_id,
            new_available,
            new_reserved,
            db
        )

        record_movement(
            data.product_id,
            data.variant_id,
            "stock_released",
            data.quantity,
            old_available,
            new_available,
            old_reserved,
            new_reserved,
            current_user,
            data.reason,
            data.reference,
            db
        )

        db.commit()

        return {
            "message": "Reserved stock released successfully",
            "available_quantity": new_available,
            "reserved_quantity": new_reserved
        }

    except Exception:
        db.rollback()
        raise


# =====================================================
# 11. CONSUME RESERVED STOCK
# POST /inventory/consume-reserved
# =====================================================

@router.post(
    "/consume-reserved",
    dependencies=[
        Depends(require_roles(*STOCK_RESERVATION_ROLES))
    ]
)
def consume_reserved_stock(
    data: StockAction,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    try:

        validate_product_variant(
            data.product_id,
            data.variant_id,
            db
        )

        inventory = get_inventory_record(
            data.product_id,
            data.variant_id,
            db
        )

        if not inventory:

            raise HTTPException(
                status_code=404,
                detail="Inventory record not found"
            )

        old_available = inventory["available_quantity"]
        old_reserved = inventory["reserved_quantity"]

        if old_reserved < data.quantity:

            raise HTTPException(
                status_code=400,
                detail="Insufficient reserved stock to fulfill order"
            )

        new_available = old_available
        new_reserved = old_reserved - data.quantity

        db.execute(
            update(ProductInventory)
            .where(
                ProductInventory.c.id == inventory["id"]
            )
            .values(
                reserved_quantity=new_reserved
            )
        )

        sync_variant_stock(
            data.variant_id,
            new_available,
            new_reserved,
            db
        )

        record_movement(
            data.product_id,
            data.variant_id,
            "reserved_stock_consumed",
            data.quantity,
            old_available,
            new_available,
            old_reserved,
            new_reserved,
            current_user,
            data.reason,
            data.reference,
            db
        )

        db.commit()

        return {
            "message": "Reserved stock consumed successfully",
            "available_quantity": new_available,
            "reserved_quantity": new_reserved
        }

    except Exception:
        db.rollback()
        raise


# =====================================================
# 12. GET PRODUCT STOCK
# GET /inventory/product/{product_id}
# =====================================================

@router.get(
    "/product/{product_id}",
    dependencies=[
        Depends(require_roles(*STOCK_VIEW_ROLES))
    ]
)
def get_product_stock(
    product_id: int,
    db: Session = Depends(get_db)
):

    validate_product_variant(
        product_id,
        None,
        db
    )

    inventory = get_inventory_record(
        product_id,
        None,
        db
    )

    if not inventory:

        return {
            "product_id": product_id,
            "variant_id": None,
            "available_quantity": 0,
            "reserved_quantity": 0,
            "total_quantity": 0
        }

    available = inventory["available_quantity"]
    reserved = inventory["reserved_quantity"]

    return {
        "product_id": product_id,
        "variant_id": None,
        "available_quantity": available,
        "reserved_quantity": reserved,
        "total_quantity": available + reserved
    }


# =====================================================
# 13. GET VARIANT STOCK
# GET /inventory/variant/{variant_id}
# =====================================================

@router.get(
    "/variant/{variant_id}",
    dependencies=[
        Depends(require_roles(*STOCK_VIEW_ROLES))
    ]
)
def get_variant_stock(
    variant_id: int,
    db: Session = Depends(get_db)
):

    variant = db.execute(
        select(ProductVariants).where(
            ProductVariants.c.id == variant_id
        )
    ).mappings().first()

    if not variant:

        raise HTTPException(
            status_code=404,
            detail="Product variant not found"
        )

    inventory = get_inventory_record(
        variant["product_id"],
        variant_id,
        db
    )

    if not inventory:

        return {
            "product_id": variant["product_id"],
            "variant_id": variant_id,
            "available_quantity": 0,
            "reserved_quantity": 0,
            "total_quantity": 0
        }

    available = inventory["available_quantity"]
    reserved = inventory["reserved_quantity"]

    return {
        "product_id": variant["product_id"],
        "variant_id": variant_id,
        "available_quantity": available,
        "reserved_quantity": reserved,
        "total_quantity": available + reserved
    }


# =====================================================
# 14. GET PRODUCT INVENTORY HISTORY
# GET /inventory/history/product/{product_id}
# =====================================================

@router.get(
    "/history/product/{product_id}",
    dependencies=[
        Depends(require_roles(*STOCK_HISTORY_ROLES))
    ]
)
def get_product_inventory_history(
    product_id: int,
    db: Session = Depends(get_db)
):

    validate_product_variant(
        product_id,
        None,
        db
    )

    history = db.execute(
        select(InventoryMovements)
        .where(
            and_(
                InventoryMovements.c.product_id == product_id,
                InventoryMovements.c.variant_id.is_(None)
            )
        )
        .order_by(
            InventoryMovements.c.id.desc()
        )
    ).mappings().all()

    return [
        dict(row)
        for row in history
    ]


# =====================================================
# 15. GET VARIANT INVENTORY HISTORY
# GET /inventory/history/variant/{variant_id}
# =====================================================

@router.get(
    "/history/variant/{variant_id}",
    dependencies=[
        Depends(require_roles(*STOCK_HISTORY_ROLES))
    ]
)
def get_variant_inventory_history(
    variant_id: int,
    db: Session = Depends(get_db)
):

    variant = db.execute(
        select(ProductVariants).where(
            ProductVariants.c.id == variant_id
        )
    ).mappings().first()

    if not variant:

        raise HTTPException(
            status_code=404,
            detail="Product variant not found"
        )

    history = db.execute(
        select(InventoryMovements)
        .where(
            InventoryMovements.c.variant_id == variant_id
        )
        .order_by(
            InventoryMovements.c.id.desc()
        )
    ).mappings().all()

    return [
        dict(row)
        for row in history
    ]
