from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, insert, update, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user

from app.models.resources import (
    Warehouses,
    WarehouseInventory,
    Products,
    ProductVariants,
)

from app.schemas.warehouse import (
    WarehouseCreate,
    WarehouseUpdate,
    WarehouseStockAction,
)


router = APIRouter(
    prefix="/warehouses",
    tags=["Module 14 - Warehouse Management"]
)


# ---------------- RBAC ----------------

def normalize_role(role):
    if hasattr(role, "value"):
        role = role.value

    if hasattr(role, "name"):
        role = role.name

    return str(role).strip().lower().replace("_", " ")


def require_roles(*allowed_roles):
    allowed = {normalize_role(role) for role in allowed_roles}

    def role_checker(
        current_user=Depends(get_current_user)
    ):
        user_role = normalize_role(current_user.role)

        if user_role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource"
            )

        return current_user

    return role_checker


WAREHOUSE_MANAGERS = [
    "super admin",
    "admin",
    "inventory manager",
]

WAREHOUSE_READERS = [
    "super admin",
    "admin",
    "inventory manager",
    "order manager",
    "product manager",
    "finance manager",
    "support agent",
    "delivery manager",
]


# ---------------- Helper functions ----------------

def get_warehouse_or_404(db, warehouse_id):
    warehouse = db.execute(
        select(Warehouses).where(
            Warehouses.c.id == warehouse_id
        )
    ).mappings().first()

    if not warehouse:
        raise HTTPException(
            status_code=404,
            detail="Warehouse not found"
        )

    return warehouse


def validate_product_variant(db, product_id, variant_id):
    product = db.execute(
        select(Products.c.id).where(
            Products.c.id == product_id
        )
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    if variant_id is not None:
        variant = db.execute(
            select(ProductVariants.c.id).where(
                ProductVariants.c.id == variant_id,
                ProductVariants.c.product_id == product_id
            )
        ).first()

        if not variant:
            raise HTTPException(
                status_code=404,
                detail="Variant not found for this product"
            )


def get_stock_record(db, warehouse_id, product_id, variant_id):
    query = select(WarehouseInventory).where(
        WarehouseInventory.c.warehouse_id == warehouse_id,
        WarehouseInventory.c.product_id == product_id,
    )

    if variant_id is None:
        query = query.where(
            WarehouseInventory.c.variant_id.is_(None)
        )
    else:
        query = query.where(
            WarehouseInventory.c.variant_id == variant_id
        )

    return db.execute(query).mappings().first()


def get_warehouse_total_stock(db, warehouse_id):
    result = db.execute(
        select(
            func.coalesce(
                func.sum(WarehouseInventory.c.quantity), 0
            )
        ).where(
            WarehouseInventory.c.warehouse_id == warehouse_id
        )
    ).scalar_one()

    return int(result)


# ---------------- 1. Create Warehouse ----------------

@router.post(
    "/",
    status_code=status.HTTP_201_CREATED
)
def create_warehouse(
    data: WarehouseCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*WAREHOUSE_MANAGERS))
):
    try:
        existing = db.execute(
            select(Warehouses.c.id).where(
                Warehouses.c.code == data.code
            )
        ).first()

        if existing:
            raise HTTPException(
                status_code=400,
                detail="Warehouse code already exists"
            )

        result = db.execute(
            insert(Warehouses).values(**data.model_dump())
        )

        db.commit()

        return {
            "message": "Warehouse created successfully",
            "warehouse_id": result.lastrowid
        }

    except Exception:
        db.rollback()
        raise


# ---------------- 2. List Warehouses ----------------

@router.get("/")
def list_warehouses(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*WAREHOUSE_READERS))
):
    warehouses = db.execute(
        select(Warehouses).order_by(Warehouses.c.id.desc())
    ).mappings().all()

    return [dict(item) for item in warehouses]


# ---------------- 3. Get Warehouse ----------------

@router.get("/{warehouse_id}")
def get_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*WAREHOUSE_READERS))
):
    warehouse = get_warehouse_or_404(db, warehouse_id)

    return dict(warehouse)


# ---------------- 4. Update Warehouse ----------------

@router.put("/{warehouse_id}")
def update_warehouse(
    warehouse_id: int,
    data: WarehouseUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*WAREHOUSE_MANAGERS))
):
    try:
        warehouse = db.execute(
            select(Warehouses).where(
                Warehouses.c.id == warehouse_id
            ).with_for_update()
        ).mappings().first()

        if not warehouse:
            raise HTTPException(
                status_code=404,
                detail="Warehouse not found"
            )

        changes = data.model_dump(exclude_unset=True)

        if "capacity" in changes:
            current_stock = get_warehouse_total_stock(
                db, warehouse_id
            )

            if changes["capacity"] < current_stock:
                raise HTTPException(
                    status_code=400,
                    detail=f"Capacity cannot be less than current stock ({current_stock})"
                )

        if changes:
            db.execute(
                update(Warehouses)
                .where(Warehouses.c.id == warehouse_id)
                .values(**changes)
            )

        db.commit()

        return {
            "message": "Warehouse updated successfully"
        }

    except Exception:
        db.rollback()
        raise


# ---------------- 5. Add Stock to Warehouse ----------------

@router.post("/{warehouse_id}/stock/add")
def add_warehouse_stock(
    warehouse_id: int,
    data: WarehouseStockAction,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*WAREHOUSE_MANAGERS))
):
    try:
        # Lock the warehouse row to serialize stock changes
        warehouse = db.execute(
            select(Warehouses).where(
                Warehouses.c.id == warehouse_id
            ).with_for_update()
        ).mappings().first()

        if not warehouse:
            raise HTTPException(
                status_code=404,
                detail="Warehouse not found"
            )

        if warehouse["status"] != "active":
            raise HTTPException(
                status_code=400,
                detail="Cannot add stock to an inactive or maintenance warehouse"
            )

        validate_product_variant(
            db, data.product_id, data.variant_id
        )

        current_total = get_warehouse_total_stock(
            db, warehouse_id
        )

        if current_total + data.quantity > warehouse["capacity"]:
            raise HTTPException(
                status_code=400,
                detail="Warehouse capacity exceeded"
            )

        stock = get_stock_record(
            db,
            warehouse_id,
            data.product_id,
            data.variant_id
        )

        if stock:
            db.execute(
                update(WarehouseInventory)
                .where(WarehouseInventory.c.id == stock["id"])
                .values(
                    quantity=stock["quantity"] + data.quantity
                )
            )
        else:
            db.execute(
                insert(WarehouseInventory).values(
                    warehouse_id=warehouse_id,
                    product_id=data.product_id,
                    variant_id=data.variant_id,
                    quantity=data.quantity
                )
            )

        db.commit()

        return {
            "message": "Warehouse stock added successfully",
            "warehouse_id": warehouse_id,
            "product_id": data.product_id,
            "variant_id": data.variant_id,
            "added_quantity": data.quantity
        }

    except Exception:
        db.rollback()
        raise


# ---------------- 6. Reduce Stock ----------------

@router.post("/{warehouse_id}/stock/reduce")
def reduce_warehouse_stock(
    warehouse_id: int,
    data: WarehouseStockAction,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*WAREHOUSE_MANAGERS))
):
    try:
        warehouse = db.execute(
            select(Warehouses).where(
                Warehouses.c.id == warehouse_id
            ).with_for_update()
        ).mappings().first()

        if not warehouse:
            raise HTTPException(
                status_code=404,
                detail="Warehouse not found"
            )

        if warehouse["status"] != "active":
            raise HTTPException(
                status_code=400,
                detail="Cannot reduce stock from an inactive or maintenance warehouse"
            )

        validate_product_variant(
            db, data.product_id, data.variant_id
        )

        stock = get_stock_record(
            db,
            warehouse_id,
            data.product_id,
            data.variant_id
        )

        if not stock or stock["quantity"] < data.quantity:
            raise HTTPException(
                status_code=400,
                detail="Insufficient warehouse stock"
            )

        new_quantity = stock["quantity"] - data.quantity

        db.execute(
            update(WarehouseInventory)
            .where(WarehouseInventory.c.id == stock["id"])
            .values(quantity=new_quantity)
        )

        db.commit()

        return {
            "message": "Warehouse stock reduced successfully",
            "warehouse_id": warehouse_id,
            "product_id": data.product_id,
            "remaining_quantity": new_quantity
        }

    except Exception:
        db.rollback()
        raise


# ---------------- 7. Warehouse-Level Stock ----------------

@router.get("/{warehouse_id}/stock")
def get_warehouse_stock(
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*WAREHOUSE_READERS))
):
    get_warehouse_or_404(db, warehouse_id)

    stock = db.execute(
        select(WarehouseInventory).where(
            WarehouseInventory.c.warehouse_id == warehouse_id
        )
    ).mappings().all()

    return {
        "warehouse_id": warehouse_id,
        "total_stock": get_warehouse_total_stock(db, warehouse_id),
        "items": [dict(item) for item in stock]
    }


# ---------------- 8. Product Stock Across Warehouses ----------------

@router.get("/product/{product_id}/stock")
def get_product_stock_across_warehouses(
    product_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*WAREHOUSE_READERS))
):
    validate_product_variant(db, product_id, None)

    stock = db.execute(
        select(
            WarehouseInventory,
            Warehouses.c.name.label("warehouse_name"),
            Warehouses.c.code.label("warehouse_code"),
        )
        .join(
            Warehouses,
            Warehouses.c.id == WarehouseInventory.c.warehouse_id
        )
        .where(WarehouseInventory.c.product_id == product_id)
    ).mappings().all()

    return [dict(item) for item in stock]