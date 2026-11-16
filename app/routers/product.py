
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, insert, update, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.resources import Products, Categories, Brands
from app.schemas.product import ProductCreate, ProductUpdate


router = APIRouter(
    prefix="/products",
    tags=["Module 8 - Product Management"]
)


def get_product_or_404(db: Session, product_id: int):
    product = db.execute(
        select(Products).where(Products.c.id == product_id)
    ).mappings().first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return dict(product)


def validate_category(db: Session, category_id: int | None):
    if category_id is None:
        return

    category = db.execute(
        select(Categories).where(Categories.c.id == category_id)
    ).mappings().first()

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found"
        )

    if not category["is_active"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot assign product to an inactive category"
        )


def validate_brand(db: Session, brand_id: int | None):
    if brand_id is None:
        return

    brand = db.execute(
        select(Brands).where(Brands.c.id == brand_id)
    ).mappings().first()

    if not brand:
        raise HTTPException(
            status_code=404,
            detail="Brand not found"
        )

    if not brand["is_active"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot assign product to an inactive brand"
        )


# 1. Create Product
@router.post("/", status_code=201)
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db)
):
    existing = db.execute(
        select(Products).where(Products.c.sku == data.sku)
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Product SKU already exists"
        )

    validate_category(db, data.category_id)
    validate_brand(db, data.brand_id)

    result = db.execute(
        insert(Products).values(
            name=data.name,
            description=data.description,
            sku=data.sku,
            category_id=data.category_id,
            brand_id=data.brand_id,
            base_price=data.base_price,
            is_active=data.is_active
        )
    )

    db.commit()

    product_id = result.inserted_primary_key[0]

    return {
        "message": "Product created successfully",
        "product": get_product_or_404(db, product_id)
    }


# 2. Get All Products with Filters
@router.get("/")
def get_all_products(
    category_id: int | None = Query(default=None, gt=0),
    brand_id: int | None = Query(default=None, gt=0),
    is_active: bool | None = None,
    min_price: Decimal | None = Query(default=None, gt=0),
    max_price: Decimal | None = Query(default=None, gt=0),
    db: Session = Depends(get_db)
):
    query = select(Products)

    if category_id is not None:
        query = query.where(Products.c.category_id == category_id)

    if brand_id is not None:
        query = query.where(Products.c.brand_id == brand_id)

    if is_active is not None:
        query = query.where(Products.c.is_active == is_active)

    if min_price is not None:
        query = query.where(Products.c.base_price >= min_price)

    if max_price is not None:
        query = query.where(Products.c.base_price <= max_price)

    if min_price is not None and max_price is not None:
        if min_price > max_price:
            raise HTTPException(
                status_code=400,
                detail="min_price cannot be greater than max_price"
            )

    result = db.execute(
        query.order_by(Products.c.id.desc())
    ).mappings().all()

    return {
        "total": len(result),
        "products": [dict(row) for row in result]
    }


# 3. Search Products
@router.get("/search")
def search_products(
    keyword: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
    search_text = f"%{keyword}%"

    result = db.execute(
        select(Products).where(
            or_(
                Products.c.name.ilike(search_text),
                Products.c.description.ilike(search_text),
                Products.c.sku.ilike(search_text)
            )
        ).order_by(Products.c.name)
    ).mappings().all()

    return {
        "keyword": keyword,
        "total": len(result),
        "products": [dict(row) for row in result]
    }


# 4. Get Product Details
@router.get("/{product_id}")
def get_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    return get_product_or_404(db, product_id)


# 5. Update Product
@router.put("/{product_id}")
def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db)
):
    get_product_or_404(db, product_id)

    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No update data provided"
        )

    if "sku" in update_data:
        existing = db.execute(
            select(Products).where(
                Products.c.sku == update_data["sku"],
                Products.c.id != product_id
            )
        ).first()

        if existing:
            raise HTTPException(
                status_code=409,
                detail="Product SKU already exists"
            )

    if "category_id" in update_data:
        validate_category(db, update_data["category_id"])

    if "brand_id" in update_data:
        validate_brand(db, update_data["brand_id"])

    db.execute(
        update(Products)
        .where(Products.c.id == product_id)
        .values(**update_data)
    )

    db.commit()

    return {
        "message": "Product updated successfully",
        "product": get_product_or_404(db, product_id)
    }


# 6. Activate / Deactivate Product
@router.patch("/{product_id}/status")
def update_product_status(
    product_id: int,
    is_active: bool,
    db: Session = Depends(get_db)
):
    get_product_or_404(db, product_id)

    db.execute(
        update(Products)
        .where(Products.c.id == product_id)
        .values(is_active=is_active)
    )

    db.commit()

    return {
        "message": "Product status updated successfully",
        "product": get_product_or_404(db, product_id)
    }
