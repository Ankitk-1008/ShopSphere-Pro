
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, insert, update
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.resources import Products, ProductVariants
from app.schemas.product_variant import (
    ProductVariantCreate,
    ProductVariantUpdate
)


router = APIRouter(
    prefix="/product-variants",
    tags=["Module 9 - Product Variants"]
)


def get_variant_or_404(db: Session, variant_id: int):
    result = db.execute(
        select(ProductVariants).where(
            ProductVariants.c.id == variant_id
        )
    ).mappings().first()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Product variant not found"
        )

    return dict(result)


def validate_product(db: Session, product_id: int):
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
            detail="Cannot create variant for an inactive product"
        )


def check_duplicate_sku(
    db: Session,
    sku: str,
    exclude_variant_id: int | None = None
):
    query = select(ProductVariants).where(
        ProductVariants.c.sku == sku
    )

    if exclude_variant_id is not None:
        query = query.where(
            ProductVariants.c.id != exclude_variant_id
        )

    existing = db.execute(query).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Variant SKU already exists"
        )


def variant_response(variant):
    result = dict(variant)
    stock = result.get("stock") or 0

    result["availability"] = (
        "IN_STOCK" if stock > 0 else "OUT_OF_STOCK"
    )

    return result


# 1. Create Product Variant
@router.post("/", status_code=201)
def create_variant(
    data: ProductVariantCreate,
    db: Session = Depends(get_db)
):
    validate_product(db, data.product_id)
    check_duplicate_sku(db, data.sku)

    result = db.execute(
        insert(ProductVariants).values(
            product_id=data.product_id,
            sku=data.sku,
            size=data.size,
            color=data.color,
            price=str(data.price),
            stock=data.stock,
            is_active=data.is_active
        )
    )

    db.commit()

    variant_id = result.inserted_primary_key[0]
    variant = get_variant_or_404(db, variant_id)

    return {
        "message": "Product variant created successfully",
        "variant": variant_response(variant)
    }


# 2. Get All Variants for a Product
@router.get("/product/{product_id}")
def get_variants_by_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    validate_product(db, product_id)

    result = db.execute(
        select(ProductVariants)
        .where(ProductVariants.c.product_id == product_id)
        .order_by(ProductVariants.c.id.desc())
    ).mappings().all()

    return {
        "product_id": product_id,
        "total_variants": len(result),
        "variants": [
            variant_response(row) for row in result
        ]
    }


# 3. Get Variant Details
@router.get("/{variant_id}")
def get_variant(
    variant_id: int,
    db: Session = Depends(get_db)
):
    variant = get_variant_or_404(db, variant_id)
    return variant_response(variant)


# 4. Update Variant Details
@router.put("/{variant_id}")
def update_variant(
    variant_id: int,
    data: ProductVariantUpdate,
    db: Session = Depends(get_db)
):
    get_variant_or_404(db, variant_id)

    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No update data provided"
        )

    if "sku" in update_data:
        check_duplicate_sku(
            db,
            update_data["sku"],
            exclude_variant_id=variant_id
        )

    # Database price column is String
    if "price" in update_data and update_data["price"] is not None:
        update_data["price"] = str(update_data["price"])

    db.execute(
        update(ProductVariants)
        .where(ProductVariants.c.id == variant_id)
        .values(**update_data)
    )

    db.commit()

    return {
        "message": "Product variant updated successfully",
        "variant": variant_response(
            get_variant_or_404(db, variant_id)
        )
    }


# 5. Update Variant Stock / Availability
@router.patch("/{variant_id}/availability")
def update_variant_stock(
    variant_id: int,
    stock: int = Query(..., ge=0),
    db: Session = Depends(get_db)
):
    get_variant_or_404(db, variant_id)

    db.execute(
        update(ProductVariants)
        .where(ProductVariants.c.id == variant_id)
        .values(stock=stock)
    )

    db.commit()

    variant = get_variant_or_404(db, variant_id)

    return {
        "message": "Variant stock updated successfully",
        "variant": variant_response(variant)
    }


# 6. Activate / Deactivate Variant
@router.patch("/{variant_id}/status")
def update_variant_status(
    variant_id: int,
    is_active: bool,
    db: Session = Depends(get_db)
):
    get_variant_or_404(db, variant_id)

    db.execute(
        update(ProductVariants)
        .where(ProductVariants.c.id == variant_id)
        .values(is_active=is_active)
    )

    db.commit()

    return {
        "message": "Variant status updated successfully",
        "variant": variant_response(
            get_variant_or_404(db, variant_id)
        )
    }



@router.delete("/{variant_id}")
def delete_variant(
    variant_id: int,
    db: Session = Depends(get_db)
):
    get_variant_or_404(db, variant_id)

    db.execute(
        ProductVariants.delete().where(
            ProductVariants.c.id == variant_id
        )
    )

    db.commit()

    return {
        "message": "Product variant deleted successfully"
    }
