
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, insert, update, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user

from app.models.resources import DiscountCodes

from app.schemas.coupon import (
    CouponCreate,
    CouponUpdate,
)


router = APIRouter(
    prefix="/coupons",
    tags=["Module 20 - Coupon Management"],
)


# ----------------------------------
# RBAC
# ----------------------------------

def normalize_role(user):
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
        if normalize_role(current_user) not in roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission",
            )
        return current_user

    return checker


COUPON_MANAGERS = (
    "super_admin",
    "admin",
    "finance_manager",
)

COUPON_READERS = (
    "super_admin",
    "admin",
    "finance_manager",
    "product_manager",
    "order_manager",
    "support_agent",
    "customer",
)


# ----------------------------------
# Helper functions
# ----------------------------------

def current_time():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def validate_coupon_dates(starts_at, ends_at):
    if starts_at and ends_at and starts_at >= ends_at:
        raise HTTPException(
            status_code=400,
            detail="Coupon end date must be after start date",
        )


def validate_discount(discount_type, discount_value):
    if discount_value <= 0:
        raise HTTPException(
            status_code=400,
            detail="Discount value must be greater than zero",
        )

    if discount_type == "percentage" and discount_value > 100:
        raise HTTPException(
            status_code=400,
            detail="Percentage discount cannot exceed 100",
        )


def get_coupon_or_404(db, coupon_id):
    coupon = db.execute(
        select(DiscountCodes).where(
            DiscountCodes.c.id == coupon_id
        )
    ).mappings().first()

    if not coupon:
        raise HTTPException(
            status_code=404,
            detail="Coupon not found",
        )

    return coupon


# ----------------------------------
# 1. Create coupon
# ----------------------------------

@router.post(
    "/",
    dependencies=[Depends(allow_roles(*COUPON_MANAGERS))],
)
def create_coupon(
    payload: CouponCreate,
    db: Session = Depends(get_db),
):
    code = payload.code.strip().upper()

    if not code:
        raise HTTPException(
            status_code=400,
            detail="Coupon code cannot be empty",
        )

    validate_discount(
        payload.discount_type,
        payload.discount_value,
    )

    validate_coupon_dates(
        payload.starts_at,
        payload.ends_at,
    )

    existing = db.execute(
        select(DiscountCodes).where(
            func.upper(DiscountCodes.c.code) == code
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Coupon code already exists",
        )

    result = db.execute(
        insert(DiscountCodes).values(
            code=code,
            discount_type=payload.discount_type,
            discount_value=payload.discount_value,
            min_order_amount=payload.min_order_amount,
            max_discount=payload.max_discount,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            is_active=True,
        )
    )

    db.commit()

    return {
        "message": "Coupon created successfully",
        "coupon_id": result.inserted_primary_key[0],
        "coupon_code": code,
    }


# ----------------------------------
# 2. Get all coupons
# ----------------------------------

@router.get(
    "/",
    dependencies=[Depends(allow_roles(*COUPON_READERS))],
)
def get_all_coupons(db: Session = Depends(get_db)):
    coupons = db.execute(
        select(DiscountCodes).order_by(
            DiscountCodes.c.id.desc()
        )
    ).mappings().all()

    return [dict(coupon) for coupon in coupons]


# ----------------------------------
# 3. Get coupon by ID
# ----------------------------------

@router.get(
    "/{coupon_id}",
    dependencies=[Depends(allow_roles(*COUPON_READERS))],
)
def get_coupon(
    coupon_id: int,
    db: Session = Depends(get_db),
):
    coupon = get_coupon_or_404(db, coupon_id)
    return dict(coupon)


# ----------------------------------
# 4. Update coupon
# ----------------------------------

@router.put(
    "/{coupon_id}",
    dependencies=[Depends(allow_roles(*COUPON_MANAGERS))],
)
def update_coupon(
    coupon_id: int,
    payload: CouponUpdate,
    db: Session = Depends(get_db),
):
    coupon = get_coupon_or_404(db, coupon_id)

    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update",
        )

    discount_type = changes.get(
        "discount_type",
        coupon["discount_type"],
    )

    discount_value = changes.get(
        "discount_value",
        coupon["discount_value"],
    )

    starts_at = changes.get(
        "starts_at",
        coupon["starts_at"],
    )

    ends_at = changes.get(
        "ends_at",
        coupon["ends_at"],
    )

    validate_discount(discount_type, Decimal(str(discount_value)))

    validate_coupon_dates(starts_at, ends_at)

    db.execute(
        update(DiscountCodes)
        .where(DiscountCodes.c.id == coupon_id)
        .values(**changes)
    )

    db.commit()

    return {
        "message": "Coupon updated successfully",
        "coupon_id": coupon_id,
    }


# ----------------------------------
# 5. Activate coupon
# ----------------------------------

@router.patch(
    "/{coupon_id}/activate",
    dependencies=[Depends(allow_roles(*COUPON_MANAGERS))],
)
def activate_coupon(
    coupon_id: int,
    db: Session = Depends(get_db),
):
    get_coupon_or_404(db, coupon_id)

    db.execute(
        update(DiscountCodes)
        .where(DiscountCodes.c.id == coupon_id)
        .values(is_active=True)
    )

    db.commit()

    return {
        "message": "Coupon activated successfully",
        "coupon_id": coupon_id,
        "is_active": True,
    }


# ----------------------------------
# 6. Deactivate coupon
# ----------------------------------

@router.patch(
    "/{coupon_id}/deactivate",
    dependencies=[Depends(allow_roles(*COUPON_MANAGERS))],
)
def deactivate_coupon(
    coupon_id: int,
    db: Session = Depends(get_db),
):
    get_coupon_or_404(db, coupon_id)

    db.execute(
        update(DiscountCodes)
        .where(DiscountCodes.c.id == coupon_id)
        .values(is_active=False)
    )

    db.commit()

    return {
        "message": "Coupon deactivated successfully",
        "coupon_id": coupon_id,
        "is_active": False,
    }


# ----------------------------------
# 7. Validate coupon
# ----------------------------------

@router.post(
    "/validate",
    dependencies=[Depends(allow_roles(*COUPON_READERS))],
)
def validate_coupon(
    code: str,
    purchase_amount: Decimal,
    db: Session = Depends(get_db),
):
    if purchase_amount < 0:
        raise HTTPException(
            status_code=400,
            detail="Purchase amount cannot be negative",
        )

    coupon = db.execute(
        select(DiscountCodes).where(
            func.upper(DiscountCodes.c.code)
            == code.strip().upper(),
            DiscountCodes.c.is_active == True,
        )
    ).mappings().first()

    if not coupon:
        raise HTTPException(
            status_code=404,
            detail="Invalid or inactive coupon",
        )

    now = current_time()

    if coupon["starts_at"] and now < coupon["starts_at"]:
        raise HTTPException(
            status_code=400,
            detail="Coupon is not active yet",
        )

    if coupon["ends_at"] and now > coupon["ends_at"]:
        raise HTTPException(
            status_code=400,
            detail="Coupon has expired",
        )

    minimum = Decimal(str(coupon["min_order_amount"]))

    if purchase_amount < minimum:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum purchase amount is {minimum}",
        )

    discount_value = Decimal(str(coupon["discount_value"]))

    if coupon["discount_type"] == "percentage":
        validate_discount("percentage", discount_value)

        discount_amount = (
            purchase_amount * discount_value / Decimal("100")
        )

        if coupon["max_discount"] is not None:
            discount_amount = min(
                discount_amount,
                Decimal(str(coupon["max_discount"])),
            )
    else:
        discount_amount = discount_value

    discount_amount = min(discount_amount, purchase_amount)

    final_amount = purchase_amount - discount_amount

    return {
        "valid": True,
        "coupon_code": coupon["code"],
        "discount_type": coupon["discount_type"],
        "discount_value": str(discount_value),
        "purchase_amount": str(purchase_amount),
        "discount_amount": str(discount_amount.quantize(Decimal("0.01"))),
        "final_amount": str(final_amount.quantize(Decimal("0.01"))),
        "message": "Coupon applied successfully",
    }
