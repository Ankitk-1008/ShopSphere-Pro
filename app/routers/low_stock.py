from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, insert, update, and_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user

from app.models.resources import (
    Warehouses,
    WarehouseInventory,
    Products,
    ProductVariants,
    LowStockThresholds,
    LowStockAlerts,
    StockThresholdHistory,
)

from app.schemas.low_stock import (
    ThresholdCreate,
    ThresholdUpdate,
)


router = APIRouter(
    prefix="/low-stock",
    tags=["Module 16 - Low Stock Management"]
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
        if normalize_role(current_user.role) not in allowed:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this resource"
            )

        return current_user

    return role_checker


STOCK_MANAGERS = [
    "super admin",
    "admin",
    "inventory manager",
]

STOCK_REPORT_READERS = [
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
                detail="Variant does not belong to this product"
            )


def get_threshold(db, threshold_id, lock=False):
    query = select(LowStockThresholds).where(
        LowStockThresholds.c.id == threshold_id
    )

    if lock:
        query = query.with_for_update()

    threshold = db.execute(query).mappings().first()

    if not threshold:
        raise HTTPException(
            status_code=404,
            detail="Stock threshold not found"
        )

    return threshold


def get_stock_quantity(db, warehouse_id, product_id, variant_id):
    query = select(WarehouseInventory.c.quantity).where(
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

    quantity = db.execute(query).scalar_one_or_none()

    return int(quantity or 0)


def get_active_alert(db, threshold_id, lock=False):
    query = select(LowStockAlerts).where(
        LowStockAlerts.c.threshold_id == threshold_id,
        LowStockAlerts.c.status == "active"
    ).order_by(
        LowStockAlerts.c.id.desc()
    ).limit(1)

    if lock:
        query = query.with_for_update()

    return db.execute(query).mappings().first()


def evaluate_threshold(db, threshold):
    """
    Create an alert if stock is at/below minimum.
    Resolve the active alert when stock rises above minimum.
    """

    quantity = get_stock_quantity(
        db,
        threshold["warehouse_id"],
        threshold["product_id"],
        threshold["variant_id"]
    )

    minimum = threshold["minimum_quantity"]

    active_alert = get_active_alert(
        db, threshold["id"], lock=True
    )

    if quantity <= minimum:
        if not active_alert:
            db.execute(
                insert(LowStockAlerts).values(
                    threshold_id=threshold["id"],
                    current_quantity=quantity,
                    minimum_quantity=minimum,
                    status="active",
                    message=(
                        f"Low stock: current quantity is {quantity}; "
                        f"minimum required quantity is {minimum}."
                    )
                )
            )
        else:
            db.execute(
                update(LowStockAlerts)
                .where(LowStockAlerts.c.id == active_alert["id"])
                .values(
                    current_quantity=quantity,
                    minimum_quantity=minimum,
                    message=(
                        f"Low stock: current quantity is {quantity}; "
                        f"minimum required quantity is {minimum}."
                    )
                )
            )

    elif active_alert:
        db.execute(
            update(LowStockAlerts)
            .where(LowStockAlerts.c.id == active_alert["id"])
            .values(
                status="resolved",
                current_quantity=quantity,
                minimum_quantity=minimum,
                resolved_at=datetime.utcnow()
            )
        )

    return {
        "threshold_id": threshold["id"],
        "current_quantity": quantity,
        "minimum_quantity": minimum,
        "is_low_stock": quantity <= minimum
    }


# ---------------- 1. Create Threshold ----------------

@router.post(
    "/thresholds",
    status_code=status.HTTP_201_CREATED
)
def create_threshold(
    data: ThresholdCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*STOCK_MANAGERS))
):
    try:
        # Lock warehouse row to serialize threshold creation
        get_warehouse(db, data.warehouse_id, lock=True)

        validate_product_variant(
            db, data.product_id, data.variant_id
        )

        existing_query = select(LowStockThresholds).where(
            LowStockThresholds.c.warehouse_id == data.warehouse_id,
            LowStockThresholds.c.product_id == data.product_id,
            LowStockThresholds.c.is_active.is_(True)
        )

        if data.variant_id is None:
            existing_query = existing_query.where(
                LowStockThresholds.c.variant_id.is_(None)
            )
        else:
            existing_query = existing_query.where(
                LowStockThresholds.c.variant_id == data.variant_id
            )

        existing = db.execute(
            existing_query.with_for_update()
        ).mappings().first()

        if existing:
            raise HTTPException(
                status_code=400,
                detail="An active threshold already exists for this warehouse and product/variant"
            )

        result = db.execute(
            insert(LowStockThresholds).values(
                warehouse_id=data.warehouse_id,
                product_id=data.product_id,
                variant_id=data.variant_id,
                minimum_quantity=data.minimum_quantity,
                is_active=True
            )
        )

        threshold_id = result.lastrowid

        db.execute(
            insert(StockThresholdHistory).values(
                threshold_id=threshold_id,
                old_minimum_quantity=None,
                new_minimum_quantity=data.minimum_quantity,
                changed_by=current_user.id,
                reason=data.reason or "Initial threshold configuration"
            )
        )

        threshold = db.execute(
            select(LowStockThresholds).where(
                LowStockThresholds.c.id == threshold_id
            )
        ).mappings().first()

        alert_result = evaluate_threshold(db, threshold)

        db.commit()

        return {
            "message": "Low-stock threshold created successfully",
            "threshold_id": threshold_id,
            **alert_result
        }

    except Exception:
        db.rollback()
        raise


# ---------------- 2. Update Threshold ----------------

@router.put("/thresholds/{threshold_id}")
def update_threshold(
    threshold_id: int,
    data: ThresholdUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*STOCK_MANAGERS))
):
    try:
        threshold = get_threshold(
            db, threshold_id, lock=True
        )

        old_minimum = threshold["minimum_quantity"]

        db.execute(
            update(LowStockThresholds)
            .where(LowStockThresholds.c.id == threshold_id)
            .values(minimum_quantity=data.minimum_quantity)
        )

        db.execute(
            insert(StockThresholdHistory).values(
                threshold_id=threshold_id,
                old_minimum_quantity=old_minimum,
                new_minimum_quantity=data.minimum_quantity,
                changed_by=current_user.id,
                reason=data.reason or "Threshold updated"
            )
        )

        updated = dict(threshold)
        updated["minimum_quantity"] = data.minimum_quantity

        alert_result = evaluate_threshold(db, updated)

        db.commit()

        return {
            "message": "Threshold updated successfully",
            "threshold_id": threshold_id,
            "old_minimum_quantity": old_minimum,
            "new_minimum_quantity": data.minimum_quantity,
            **alert_result
        }

    except Exception:
        db.rollback()
        raise


# ---------------- 3. List Thresholds ----------------

@router.get("/thresholds")
def list_thresholds(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*STOCK_REPORT_READERS))
):
    thresholds = db.execute(
        select(LowStockThresholds).order_by(
            LowStockThresholds.c.id.desc()
        )
    ).mappings().all()

    return [dict(item) for item in thresholds]


# ---------------- 4. Scan Low Stock and Generate Alerts ----------------

@router.post("/scan")
def scan_low_stock(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*STOCK_MANAGERS))
):
    try:
        thresholds = db.execute(
            select(LowStockThresholds).where(
                LowStockThresholds.c.is_active.is_(True)
            ).order_by(
                LowStockThresholds.c.id.asc()
            )
        ).mappings().all()

        results = []

        for threshold in thresholds:
            results.append(
                evaluate_threshold(db, threshold)
            )

        db.commit()

        low_stock_count = sum(
            1 for item in results if item["is_low_stock"]
        )

        return {
            "message": "Low-stock scan completed",
            "total_thresholds_checked": len(results),
            "low_stock_count": low_stock_count,
            "results": results
        }

    except Exception:
        db.rollback()
        raise


# ---------------- 5. Low-Stock Report ----------------

@router.get("/report")
def low_stock_report(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*STOCK_REPORT_READERS))
):
    thresholds = db.execute(
        select(LowStockThresholds).where(
            LowStockThresholds.c.is_active.is_(True)
        ).order_by(
            LowStockThresholds.c.warehouse_id.asc()
        )
    ).mappings().all()

    report = []

    for threshold in thresholds:
        quantity = get_stock_quantity(
            db,
            threshold["warehouse_id"],
            threshold["product_id"],
            threshold["variant_id"]
        )

        if quantity <= threshold["minimum_quantity"]:
            report.append({
                "threshold_id": threshold["id"],
                "warehouse_id": threshold["warehouse_id"],
                "product_id": threshold["product_id"],
                "variant_id": threshold["variant_id"],
                "current_quantity": quantity,
                "minimum_quantity": threshold["minimum_quantity"],
                "shortage_quantity": max(
                    threshold["minimum_quantity"] - quantity, 0
                ),
                "status": "low_stock"
            })

    return {
        "total_low_stock_items": len(report),
        "items": report
    }


# ---------------- 6. Get Alerts ----------------

@router.get("/alerts")
def list_alerts(
    alert_status: str = "active",
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*STOCK_REPORT_READERS))
):
    if alert_status not in ["active", "resolved", "all"]:
        raise HTTPException(
            status_code=400,
            detail="alert_status must be active, resolved or all"
        )

    query = select(LowStockAlerts).order_by(
        LowStockAlerts.c.id.desc()
    )

    if alert_status != "all":
        query = query.where(
            LowStockAlerts.c.status == alert_status
        )

    alerts = db.execute(query).mappings().all()

    return [dict(item) for item in alerts]


# ---------------- 7. Threshold Change History ----------------

@router.get("/thresholds/{threshold_id}/history")
def threshold_history(
    threshold_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*STOCK_REPORT_READERS))
):
    get_threshold(db, threshold_id)

    history = db.execute(
        select(StockThresholdHistory).where(
            StockThresholdHistory.c.threshold_id == threshold_id
        ).order_by(
            StockThresholdHistory.c.id.desc()
        )
    ).mappings().all()

    return [dict(item) for item in history]