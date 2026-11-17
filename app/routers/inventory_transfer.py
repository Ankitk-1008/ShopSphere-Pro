from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, insert, update, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user

from app.models.resources import (
    Warehouses,
    WarehouseInventory,
    InventoryTransfers,
    WarehouseTransferMovements,
    Products,
    ProductVariants,
)

from app.schemas.inventory_transfer import (
    TransferCreate,
    TransferDispatch,
    TransferReceipt,
)


router = APIRouter(
    prefix="/inventory-transfers",
    tags=["Module 15 - Inventory Transfers"]
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
                status_code=403,
                detail="You do not have permission to access this resource"
            )

        return current_user

    return role_checker


TRANSFER_MANAGERS = [
    "super admin",
    "admin",
    "inventory manager",
]

TRANSFER_READERS = [
    "super admin",
    "admin",
    "inventory manager",
    "order manager",
    "product manager",
    "finance manager",
    "support agent",
    "delivery manager",
]


# ---------------- Helpers ----------------

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
                detail="Variant does not belong to this product"
            )


def get_warehouse(db, warehouse_id, lock=False):
    query = select(Warehouses).where(
        Warehouses.c.id == warehouse_id
    )

    if lock:
        query = query.with_for_update()

    warehouse = db.execute(query).mappings().first()

    if not warehouse:
        raise HTTPException(
            status_code=404,
            detail=f"Warehouse {warehouse_id} not found"
        )

    return warehouse


def get_transfer(db, transfer_id, lock=False):
    query = select(InventoryTransfers).where(
        InventoryTransfers.c.id == transfer_id
    )

    if lock:
        query = query.with_for_update()

    transfer = db.execute(query).mappings().first()

    if not transfer:
        raise HTTPException(
            status_code=404,
            detail="Transfer request not found"
        )

    return transfer


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


def get_total_stock(db, warehouse_id):
    total = db.execute(
        select(
            func.coalesce(
                func.sum(WarehouseInventory.c.quantity), 0
            )
        ).where(
            WarehouseInventory.c.warehouse_id == warehouse_id
        )
    ).scalar_one()

    return int(total)


def calculate_status(requested, dispatched, received):
    if received == requested:
        return "received"

    if received > 0:
        return "partially_received"

    if dispatched == requested:
        return "dispatched"

    if dispatched > 0:
        return "partially_dispatched"

    return "requested"


def record_movement(
    db,
    transfer,
    action,
    quantity,
    current_user_id,
    notes=None
):
    db.execute(
        insert(WarehouseTransferMovements).values(
            transfer_id=transfer["id"],
            action=action,
            quantity=quantity,
            source_warehouse_id=transfer["source_warehouse_id"],
            destination_warehouse_id=transfer["destination_warehouse_id"],
            created_by=current_user_id,
            notes=notes,
        )
    )


# ---------------- 1. Create Transfer Request ----------------

@router.post(
    "/",
    status_code=status.HTTP_201_CREATED
)
def create_transfer_request(
    data: TransferCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*TRANSFER_MANAGERS))
):
    try:
        if data.source_warehouse_id == data.destination_warehouse_id:
            raise HTTPException(
                status_code=400,
                detail="Source and destination warehouses must be different"
            )

        source = get_warehouse(db, data.source_warehouse_id)
        destination = get_warehouse(db, data.destination_warehouse_id)

        if source["status"] != "active":
            raise HTTPException(
                status_code=400,
                detail="Source warehouse is not active"
            )

        if destination["status"] != "active":
            raise HTTPException(
                status_code=400,
                detail="Destination warehouse is not active"
            )

        validate_product_variant(
            db, data.product_id, data.variant_id
        )

        stock = get_stock_record(
            db,
            data.source_warehouse_id,
            data.product_id,
            data.variant_id
        )

        if not stock or stock["quantity"] < data.requested_quantity:
            raise HTTPException(
                status_code=400,
                detail="Insufficient stock in source warehouse"
            )

        result = db.execute(
            insert(InventoryTransfers).values(
                source_warehouse_id=data.source_warehouse_id,
                destination_warehouse_id=data.destination_warehouse_id,
                product_id=data.product_id,
                variant_id=data.variant_id,
                requested_quantity=data.requested_quantity,
                dispatched_quantity=0,
                received_quantity=0,
                status="requested",
                notes=data.notes,
                requested_by=current_user.id,
            )
        )

        transfer_id = result.lastrowid
        db.commit()

        return {
            "message": "Transfer request created successfully",
            "transfer_id": transfer_id,
            "status": "requested"
        }

    except Exception:
        db.rollback()
        raise


# ---------------- 2. Dispatch Stock ----------------

@router.post("/{transfer_id}/dispatch")
def dispatch_transfer(
    transfer_id: int,
    data: TransferDispatch,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*TRANSFER_MANAGERS))
):
    try:
        transfer = get_transfer(db, transfer_id, lock=True)

        if transfer["status"] == "received":
            raise HTTPException(
                status_code=400,
                detail="Transfer is already fully received"
            )

        remaining = (
            transfer["requested_quantity"]
            - transfer["dispatched_quantity"]
        )

        if data.quantity > remaining:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot dispatch more than remaining requested quantity ({remaining})"
            )

        source = get_warehouse(
            db, transfer["source_warehouse_id"], lock=True
        )

        if source["status"] != "active":
            raise HTTPException(
                status_code=400,
                detail="Source warehouse is not active"
            )

        stock = get_stock_record(
            db,
            transfer["source_warehouse_id"],
            transfer["product_id"],
            transfer["variant_id"]
        )

        if not stock or stock["quantity"] < data.quantity:
            raise HTTPException(
                status_code=400,
                detail="Insufficient source warehouse stock"
            )

        new_stock = stock["quantity"] - data.quantity
        new_dispatched = transfer["dispatched_quantity"] + data.quantity

        db.execute(
            update(WarehouseInventory)
            .where(WarehouseInventory.c.id == stock["id"])
            .values(quantity=new_stock)
        )

        updated_transfer = dict(transfer)
        updated_transfer["dispatched_quantity"] = new_dispatched

        new_status = calculate_status(
            transfer["requested_quantity"],
            new_dispatched,
            transfer["received_quantity"]
        )

        db.execute(
            update(InventoryTransfers)
            .where(InventoryTransfers.c.id == transfer_id)
            .values(
                dispatched_quantity=new_dispatched,
                status=new_status,
                dispatched_by=current_user.id,
                dispatched_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )

        record_movement(
            db,
            updated_transfer,
            "dispatch",
            data.quantity,
            current_user.id,
            data.notes
        )

        db.commit()

        return {
            "message": "Stock dispatched successfully",
            "transfer_id": transfer_id,
            "dispatched_now": data.quantity,
            "total_dispatched": new_dispatched,
            "source_remaining_stock": new_stock,
            "status": new_status
        }

    except Exception:
        db.rollback()
        raise



# ---------------- 3. Receive Stock ----------------

@router.post("/{transfer_id}/receive")
def receive_transfer(
    transfer_id: int,
    data: TransferReceipt,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*TRANSFER_MANAGERS))
):
    try:
        transfer = get_transfer(db, transfer_id, lock=True)

        if transfer["status"] == "received":
            raise HTTPException(
                status_code=400,
                detail="Transfer is already fully received"
            )

        pending_receipt = (
            transfer["dispatched_quantity"]
            - transfer["received_quantity"]
        )

        if data.quantity > pending_receipt:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot receive more than dispatched pending quantity ({pending_receipt})"
            )

        destination = get_warehouse(
            db, transfer["destination_warehouse_id"], lock=True
        )

        if destination["status"] != "active":
            raise HTTPException(
                status_code=400,
                detail="Destination warehouse is not active"
            )

        current_total = get_total_stock(
            db, transfer["destination_warehouse_id"]
        )

        if current_total + data.quantity > destination["capacity"]:
            raise HTTPException(
                status_code=400,
                detail="Destination warehouse capacity exceeded"
            )

        stock = get_stock_record(
            db,
            transfer["destination_warehouse_id"],
            transfer["product_id"],
            transfer["variant_id"]
        )

        if stock:
            new_stock = stock["quantity"] + data.quantity

            db.execute(
                update(WarehouseInventory)
                .where(WarehouseInventory.c.id == stock["id"])
                .values(quantity=new_stock)
            )
        else:
            new_stock = data.quantity

            db.execute(
                insert(WarehouseInventory).values(
                    warehouse_id=transfer["destination_warehouse_id"],
                    product_id=transfer["product_id"],
                    variant_id=transfer["variant_id"],
                    quantity=new_stock
                )
            )

        new_received = transfer["received_quantity"] + data.quantity

        new_status = calculate_status(
            transfer["requested_quantity"],
            transfer["dispatched_quantity"],
            new_received
        )

        db.execute(
            update(InventoryTransfers)
            .where(InventoryTransfers.c.id == transfer_id)
            .values(
                received_quantity=new_received,
                status=new_status,
                received_by=current_user.id,
                received_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )

        record_movement(
            db,
            transfer,
            "receipt",
            data.quantity,
            current_user.id,
            data.notes
        )

        db.commit()

        return {
            "message": "Stock received successfully",
            "transfer_id": transfer_id,
            "received_now": data.quantity,
            "total_received": new_received,
            "destination_stock": new_stock,
            "status": new_status
        }

    except Exception:
        db.rollback()
        raise


# ---------------- 4. Get All Transfer Requests ----------------

@router.get("/")
def list_transfers(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*TRANSFER_READERS))
):
    transfers = db.execute(
        select(InventoryTransfers).order_by(
            InventoryTransfers.c.id.desc()
        )
    ).mappings().all()

    return [dict(item) for item in transfers]


# ---------------- 5. Get One Transfer ----------------

@router.get("/{transfer_id}")
def get_transfer_details(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*TRANSFER_READERS))
):
    transfer = get_transfer(db, transfer_id)

    return dict(transfer)


# ---------------- 6. Transfer Movement History ----------------

@router.get("/{transfer_id}/history")
def get_transfer_history(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*TRANSFER_READERS))
):
    get_transfer(db, transfer_id)

    movements = db.execute(
        select(WarehouseTransferMovements).where(
            WarehouseTransferMovements.c.transfer_id == transfer_id
        ).order_by(
            WarehouseTransferMovements.c.id.asc()
        )
    ).mappings().all()

    return [dict(item) for item in movements]