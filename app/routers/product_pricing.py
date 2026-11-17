
from datetime import datetime
from decimal import Decimal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)

from sqlalchemy import (
    select,
    insert,
    update,
    and_,
    or_,
)

from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user

from app.models.resources import (
    Products,
    ProductPricing,
    ProductPriceHistory,
)

from app.schemas.product_pricing import (
    ProductPricingCreate,
    ProductPricingUpdate,
)


router = APIRouter(
    prefix="/product-pricing",
    tags=["Module 12 - Product Pricing"]
)


# =====================================================
# 1. RBAC ROLE CONFIGURATION
# =====================================================

MANAGE_PRICING_ROLES = (
    "super admin",
    "admin",
    "product manager",
)

READ_PRICE_ROLES = (
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
# 2. HELPER - GET PRODUCT
# =====================================================

def get_product_or_404(product_id, db):

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

    return product


# =====================================================
# 3. HELPER - CHECK OVERLAPPING VALIDITY PERIODS
# =====================================================

def check_overlapping_period(
    product_id,
    valid_from,
    valid_until,
    db,
    exclude_id=None
):

    conditions = [
        ProductPricing.c.product_id == product_id,
        ProductPricing.c.is_active == True,
    ]

    if exclude_id is not None:
        conditions.append(
            ProductPricing.c.id != exclude_id
        )

    # Two periods overlap if:
    # existing.valid_from < new.valid_until
    # AND existing.valid_until > new.valid_from
    #
    # NULL valid_until means no end date.

    if valid_until is None:

        end_condition = True

    else:

        end_condition = (
            ProductPricing.c.valid_from < valid_until
        )

    start_condition = or_(
        ProductPricing.c.valid_until.is_(None),
        ProductPricing.c.valid_until > valid_from
    )

    query = select(ProductPricing.c.id).where(
        and_(
            *conditions,
            start_condition,
            end_condition
        )
    )

    existing = db.execute(query).first()

    if existing:

        raise HTTPException(
            status_code=409,
            detail="This pricing validity period overlaps an existing active period"
        )


# =====================================================
# 4. CREATE PRODUCT PRICE
# POST /product-pricing/{product_id}
# =====================================================

@router.post(
    "/{product_id}",
    status_code=201,
    dependencies=[
        Depends(require_roles(*MANAGE_PRICING_ROLES))
    ]
)
def create_product_price(
    product_id: int,
    data: ProductPricingCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    product = get_product_or_404(
        product_id,
        db
    )

    now = datetime.utcnow()

    if data.valid_from < now:

        raise HTTPException(
            status_code=400,
            detail="valid_from cannot be in the past"
        )

    check_overlapping_period(
        product_id,
        data.valid_from,
        data.valid_until,
        db
    )

    old_base_price = product["base_price"]

    # Current sale price is read from the currently valid
    # pricing record, if one exists.

    current_record = db.execute(
        select(ProductPricing).where(
            and_(
                ProductPricing.c.product_id == product_id,
                ProductPricing.c.is_active == True,
                ProductPricing.c.valid_from <= now,
                or_(
                    ProductPricing.c.valid_until.is_(None),
                    ProductPricing.c.valid_until > now
                )
            )
        ).order_by(
            ProductPricing.c.valid_from.desc()
        )
    ).mappings().first()

    old_sale_price = (
        current_record["sale_price"]
        if current_record
        else None
    )

    result = db.execute(
        insert(ProductPricing).values(
            product_id=product_id,
            base_price=data.base_price,
            sale_price=data.sale_price,
            valid_from=data.valid_from,
            valid_until=data.valid_until,
            is_active=True,
            created_by=current_user.id,
            reason=data.reason,
        )
    )

    pricing_id = result.inserted_primary_key[0]

    db.execute(
        insert(ProductPriceHistory).values(
            product_id=product_id,
            old_base_price=old_base_price,
            new_base_price=data.base_price,
            old_sale_price=old_sale_price,
            new_sale_price=data.sale_price,
            valid_from=data.valid_from,
            valid_until=data.valid_until,
            changed_by=current_user.id,
            reason=data.reason,
        )
    )

    db.commit()

    return {
        "message": "Product pricing created successfully",
        "pricing_id": pricing_id,
        "product_id": product_id,
        "base_price": data.base_price,
        "sale_price": data.sale_price,
        "valid_from": data.valid_from,
        "valid_until": data.valid_until,
    }


# =====================================================
# 5. GET CURRENT PRODUCT PRICE
# GET /product-pricing/current/{product_id}
# =====================================================

@router.get(
    "/current/{product_id}",
    dependencies=[
        Depends(require_roles(*READ_PRICE_ROLES))
    ]
)
def get_current_product_price(
    product_id: int,
    db: Session = Depends(get_db)
):

    product = get_product_or_404(
        product_id,
        db
    )

    now = datetime.utcnow()

    pricing = db.execute(
        select(ProductPricing).where(
            and_(
                ProductPricing.c.product_id == product_id,
                ProductPricing.c.is_active == True,
                ProductPricing.c.valid_from <= now,
                or_(
                    ProductPricing.c.valid_until.is_(None),
                    ProductPricing.c.valid_until > now
                )
            )
        ).order_by(
            ProductPricing.c.valid_from.desc()
        )
    ).mappings().first()

    if pricing:

        base_price = pricing["base_price"]
        sale_price = pricing["sale_price"]

    else:

        base_price = product["base_price"]
        sale_price = None

    final_price = (
        sale_price
        if sale_price is not None
        else base_price
    )

    return {
        "product_id": product_id,
        "base_price": base_price,
        "sale_price": sale_price,
        "final_price": final_price,
        "discount": (
            base_price - sale_price
            if sale_price is not None
            else Decimal("0.00")
        ),
        "price_source": (
            "scheduled_pricing"
            if pricing
            else "product_base_price"
        ),
    }


# =====================================================
# 6. UPDATE PRICING
# PUT /product-pricing/{pricing_id}
# =====================================================

@router.put(
    "/{pricing_id}",
    dependencies=[
        Depends(require_roles(*MANAGE_PRICING_ROLES))
    ]
)
def update_product_price(
    pricing_id: int,
    data: ProductPricingUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    old_record = db.execute(
        select(ProductPricing).where(
            ProductPricing.c.id == pricing_id
        )
    ).mappings().first()

    if not old_record:

        raise HTTPException(
            status_code=404,
            detail="Pricing record not found"
        )

    if not old_record["is_active"]:

        raise HTTPException(
            status_code=400,
            detail="Inactive pricing record cannot be updated"
        )

    now = datetime.utcnow()

    if old_record["valid_from"] <= now:

        raise HTTPException(
            status_code=400,
            detail="An effective pricing record cannot be edited. Create a new pricing period instead."
        )

    if data.valid_from < now:

        raise HTTPException(
            status_code=400,
            detail="valid_from cannot be in the past"
        )

    check_overlapping_period(
        old_record["product_id"],
        data.valid_from,
        data.valid_until,
        db,
        exclude_id=pricing_id
    )

    db.execute(
        update(ProductPricing)
        .where(ProductPricing.c.id == pricing_id)
        .values(
            base_price=data.base_price,
            sale_price=data.sale_price,
            valid_from=data.valid_from,
            valid_until=data.valid_until,
            reason=data.reason,
        )
    )

    db.execute(
        insert(ProductPriceHistory).values(
            product_id=old_record["product_id"],
            old_base_price=old_record["base_price"],
            new_base_price=data.base_price,
            old_sale_price=old_record["sale_price"],
            new_sale_price=data.sale_price,
            valid_from=data.valid_from,
            valid_until=data.valid_until,
            changed_by=current_user.id,
            reason=data.reason,
        )
    )

    db.commit()

    return {
        "message": "Product pricing updated successfully",
        "pricing_id": pricing_id
    }


# =====================================================
# 7. GET ALL PRICING RECORDS FOR PRODUCT
# GET /product-pricing/product/{product_id}
# =====================================================

@router.get(
    "/product/{product_id}",
    dependencies=[
        Depends(require_roles(*READ_PRICE_ROLES))
    ]
)
def get_product_pricing_records(
    product_id: int,
    db: Session = Depends(get_db)
):

    get_product_or_404(
        product_id,
        db
    )

    records = db.execute(
        select(ProductPricing)
        .where(
            ProductPricing.c.product_id == product_id
        )
        .order_by(
            ProductPricing.c.valid_from.desc()
        )
    ).mappings().all()

    return [
        dict(record)
        for record in records
    ]


# =====================================================
# 8. PRICE HISTORY
# GET /product-pricing/history/{product_id}
# =====================================================

@router.get(
    "/history/{product_id}",
    dependencies=[
        Depends(
            require_roles(
                "super admin",
                "admin",
                "product manager",
                "finance manager"
            )
        )
    ]
)
def get_price_history(
    product_id: int,
    db: Session = Depends(get_db)
):

    get_product_or_404(
        product_id,
        db
    )

    history = db.execute(
        select(ProductPriceHistory)
        .where(
            ProductPriceHistory.c.product_id == product_id
        )
        .order_by(
            ProductPriceHistory.c.changed_at.desc(),
            ProductPriceHistory.c.id.desc()
        )
    ).mappings().all()

    return [
        dict(record)
        for record in history
    ]


# =====================================================
# 9. DEACTIVATE FUTURE PRICING
# DELETE /product-pricing/{pricing_id}
# =====================================================

@router.delete(
    "/{pricing_id}",
    dependencies=[
        Depends(require_roles(*MANAGE_PRICING_ROLES))
    ]
)
def deactivate_product_price(
    pricing_id: int,
    db: Session = Depends(get_db)
):

    record = db.execute(
        select(ProductPricing).where(
            ProductPricing.c.id == pricing_id
        )
    ).mappings().first()

    if not record:

        raise HTTPException(
            status_code=404,
            detail="Pricing record not found"
        )

    if record["valid_from"] <= datetime.utcnow():

        raise HTTPException(
            status_code=400,
            detail="An effective or past pricing record cannot be deactivated"
        )

    db.execute(
        update(ProductPricing)
        .where(ProductPricing.c.id == pricing_id)
        .values(is_active=False)
    )

    db.commit()

    return {
        "message": "Future pricing record deactivated successfully"
    }
