
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.category import Category
from app.models.resources import Products
from app.schemas.category import CategoryCreate, CategoryUpdate


router = APIRouter(
    prefix="/categories",
    tags=["Module 6 - Product Category Management"]
)


def get_category_or_404(db: Session, category_id: int):
    category = db.query(Category).filter(
        Category.id == category_id
    ).first()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    return category


def check_parent(db: Session, parent_id: int | None, current_id: int | None = None):
    if parent_id is None:
        return

    if current_id == parent_id:
        raise HTTPException(
            status_code=400,
            detail="Category cannot be its own parent"
        )

    parent = db.query(Category).filter(
        Category.id == parent_id
    ).first()

    if not parent:
        raise HTTPException(status_code=404, detail="Parent category not found")

    if not parent.is_active:
        raise HTTPException(
            status_code=400,
            detail="Cannot use an inactive parent category"
        )

    # Prevent circular hierarchy (A -> B -> A)
    ancestor_id = parent.parent_id
    while ancestor_id is not None:
        if ancestor_id == current_id:
            raise HTTPException(
                status_code=400,
                detail="Circular category hierarchy is not allowed"
            )

        ancestor = db.query(Category).filter(
            Category.id == ancestor_id
        ).first()

        if not ancestor:
            break

        ancestor_id = ancestor.parent_id


def category_data(category):
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "parent_id": category.parent_id,
        "description": category.description,
        "is_active": category.is_active,
        "created_at": category.created_at,
        "updated_at": category.updated_at
    }


@router.post("/", status_code=201)
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db)
):
    check_parent(db, data.parent_id)

    existing = db.query(Category).filter(
        (Category.name == data.name) |
        (Category.slug == data.slug)
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Category name or slug already exists"
        )

    category = Category(
        name=data.name,
        slug=data.slug,
        parent_id=data.parent_id,
        description=data.description,
        is_active=data.is_active
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    return {
        "message": "Category created successfully",
        "category": category_data(category)
    }


@router.get("/")
def get_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).order_by(Category.id).all()

    return [
        category_data(category)
        for category in categories
    ]


@router.get("/hierarchy")
def get_category_hierarchy(db: Session = Depends(get_db)):
    categories = db.query(Category).order_by(Category.id).all()

    def build_tree(parent_id=None):
        result = []

        for category in categories:
            if category.parent_id == parent_id:
                item = category_data(category)
                item["subcategories"] = build_tree(category.id)
                result.append(item)

        return result

    return build_tree()


@router.get("/{category_id}")
def get_category(
    category_id: int,
    db: Session = Depends(get_db)
):
    category = get_category_or_404(db, category_id)
    return category_data(category)


@router.put("/{category_id}")
def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: Session = Depends(get_db)
):
    category = get_category_or_404(db, category_id)

    update_data = data.model_dump(exclude_unset=True)

    if "parent_id" in update_data:
        check_parent(
            db,
            update_data["parent_id"],
            current_id=category_id
        )

    new_name = update_data.get("name", category.name)
    new_slug = update_data.get("slug", category.slug)

    duplicate = db.query(Category).filter(
        Category.id != category_id,
        (Category.name == new_name) |
        (Category.slug == new_slug)
    ).first()

    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="Category name or slug already exists"
        )

    for key, value in update_data.items():
        setattr(category, key, value)

    db.commit()
    db.refresh(category)

    return {
        "message": "Category updated successfully",
        "category": category_data(category)
    }


@router.patch("/{category_id}/status")
def update_category_status(
    category_id: int,
    is_active: bool,
    db: Session = Depends(get_db)
):
    category = get_category_or_404(db, category_id)

    # Do not activate a child if its parent is inactive
    if is_active and category.parent_id is not None:
        parent = get_category_or_404(db, category.parent_id)

        if not parent.is_active:
            raise HTTPException(
                status_code=400,
                detail="Activate the parent category first"
            )

    category.is_active = is_active
    db.commit()
    db.refresh(category)

    return {
        "message": "Category status updated successfully",
        "category": category_data(category)
    }


@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db)
):
    category = get_category_or_404(db, category_id)

    # Prevent deleting a category that has subcategories
    child = db.query(Category).filter(
        Category.parent_id == category_id
    ).first()

    if child:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete category. It has subcategories."
        )

    # Prevent deletion if products table has a category_id column
    if "category_id" in Products.c:
        product_exists = db.query(Products).filter(
            Products.c.category_id == category_id
        ).first()

        if product_exists:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete category. Products are linked to it."
            )

    db.delete(category)
    db.commit()

    return {"message": "Category deleted successfully"}
