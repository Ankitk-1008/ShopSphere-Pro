
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, insert, update, or_

from app.database import get_db
from app.models.resources import Brands, Products
from app.schemas.brand import BrandCreate, BrandUpdate


router = APIRouter(
    prefix="/brands",
    tags=["Module 7 - Brand Management"]
)


def get_brand_or_404(db: Session, brand_id: int):
    result = db.execute(
        select(Brands).where(Brands.c.id == brand_id)
    ).mappings().first()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Brand not found"
        )

    return dict(result)


# 1. Register Brand
@router.post("/", status_code=201)
def create_brand(
    data: BrandCreate,
    db: Session = Depends(get_db)
):
    existing = db.execute(
        select(Brands).where(Brands.c.name == data.name)
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Brand name already exists"
        )

    result = db.execute(
        insert(Brands).values(
            name=data.name,
            description=data.description,
            website=data.website,
            is_active=data.is_active
        )
    )

    db.commit()

    brand_id = result.inserted_primary_key[0]
    brand = get_brand_or_404(db, brand_id)

    return {
        "message": "Brand registered successfully",
        "brand": brand
    }


# 2. Get All Brands
@router.get("/")
def get_all_brands(
    db: Session = Depends(get_db)
):
    result = db.execute(
        select(Brands).order_by(Brands.c.id.desc())
    ).mappings().all()

    return {
        "total": len(result),
        "brands": [dict(row) for row in result]
    }


# 3. Search Brands
@router.get("/search")
def search_brands(
    keyword: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
    search_text = f"%{keyword}%"

    result = db.execute(
        select(Brands).where(
            or_(
                Brands.c.name.ilike(search_text),
                Brands.c.description.ilike(search_text)
            )
        ).order_by(Brands.c.name)
    ).mappings().all()

    return {
        "keyword": keyword,
        "total": len(result),
        "brands": [dict(row) for row in result]
    }


# 4. Get Brand by ID
@router.get("/{brand_id}")
def get_brand(
    brand_id: int,
    db: Session = Depends(get_db)
):
    return get_brand_or_404(db, brand_id)


# 5. Update Brand
@router.put("/{brand_id}")
def update_brand(
    brand_id: int,
    data: BrandUpdate,
    db: Session = Depends(get_db)
):
    get_brand_or_404(db, brand_id)

    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No update data provided"
        )

    if "name" in update_data:
        existing = db.execute(
            select(Brands).where(
                Brands.c.name == update_data["name"],
                Brands.c.id != brand_id
            )
        ).first()

        if existing:
            raise HTTPException(
                status_code=409,
                detail="Brand name already exists"
            )

    db.execute(
        update(Brands)
        .where(Brands.c.id == brand_id)
        .values(**update_data)
    )

    db.commit()

    return {
        "message": "Brand updated successfully",
        "brand": get_brand_or_404(db, brand_id)
    }


# 6. Activate / Deactivate Brand
@router.patch("/{brand_id}/status")
def update_brand_status(
    brand_id: int,
    is_active: bool,
    db: Session = Depends(get_db)
):
    get_brand_or_404(db, brand_id)

    db.execute(
        update(Brands)
        .where(Brands.c.id == brand_id)
        .values(is_active=is_active)
    )

    db.commit()

    return {
        "message": "Brand status updated successfully",
        "brand": get_brand_or_404(db, brand_id)
    }


# 7. Associate Product with Brand
@router.patch("/{brand_id}/products/{product_id}")
def assign_product_to_brand(
    brand_id: int,
    product_id: int,
    db: Session = Depends(get_db)
):
    brand = get_brand_or_404(db, brand_id)

    if not brand["is_active"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot assign products to an inactive brand"
        )

    product = db.execute(
        select(Products).where(Products.c.id == product_id)
    ).mappings().first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    db.execute(
        update(Products)
        .where(Products.c.id == product_id)
        .values(brand_id=brand_id)
    )

    db.commit()

    return {
        "message": "Product associated with brand successfully",
        "brand_id": brand_id,
        "product_id": product_id
    }


# 8. Retrieve Products by Brand
@router.get("/{brand_id}/products")
def get_products_by_brand(
    brand_id: int,
    db: Session = Depends(get_db)
):
    get_brand_or_404(db, brand_id)

    result = db.execute(
        select(Products).where(
            Products.c.brand_id == brand_id
        ).order_by(Products.c.id.desc())
    ).mappings().all()

    return {
        "brand_id": brand_id,
        "total_products": len(result),
        "products": [dict(row) for row in result]
    }
