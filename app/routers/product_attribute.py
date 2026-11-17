
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)

from sqlalchemy.orm import Session

from sqlalchemy import (
    select,
    insert,
    update,
    delete,
    and_,
)

from app.database import get_db

from app.dependencies.auth import get_current_user

from app.models.resources import (
    ProductAttributes,
    ProductAttributeValues,
    Products,
    Categories,
)

from app.schemas.product_attribute import (
    ProductAttributeCreate,
    ProductAttributeUpdate,
    ProductAttributeValueCreate,
)


router = APIRouter(
    prefix="/product-attributes",
    tags=["Module 11 - Product Attributes"]
)


# =====================================================
# 1. RBAC - ROLE PERMISSIONS
# =====================================================

MANAGEMENT_ROLES = (
    "super admin",
    "admin",
    "product manager",
)

READ_ROLES = (
    "super admin",
    "admin",
    "product manager",
    "customer",
)


def normalize_role(role):
    if isinstance(role, str):
        return role.strip().replace("_", " ").replace("-", " ").casefold()

    # Supports role relationship objects if your User model uses one
    return str(
        getattr(role, "name", "")
    ).strip().replace("_", " ").replace("-", " ").casefold()


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
# 2. ATTRIBUTE VALUE VALIDATION
# =====================================================

def validate_value(attribute, value):

    data_type = attribute["data_type"]

    if data_type == "number":

        try:
            float(value)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400,
                detail="Attribute value must be a valid number"
            )

    elif data_type == "boolean":

        if value.casefold() not in ("true", "false"):
            raise HTTPException(
                status_code=400,
                detail="Boolean value must be true or false"
            )

    allowed_values = attribute["allowed_values"]

    if allowed_values:

        if value not in allowed_values:
            raise HTTPException(
                status_code=400,
                detail=f"Allowed values are: {allowed_values}"
            )


# =====================================================
# 3. CHECK ATTRIBUTE CATEGORY
# =====================================================

def validate_product_category(
    attribute,
    product
):

    attribute_category = attribute["category_id"]

    product_category = product["category_id"]

    # NULL category means global attribute

    if (
        attribute_category is not None
        and attribute_category != product_category
    ):

        raise HTTPException(
            status_code=400,
            detail="This attribute does not belong to the product category"
        )


# =====================================================
# 4. CREATE ATTRIBUTE
# POST /product-attributes/
# =====================================================

@router.post(
    "/",
    status_code=201,
    dependencies=[
        Depends(require_roles(*MANAGEMENT_ROLES))
    ]
)
def create_attribute(
    data: ProductAttributeCreate,
    db: Session = Depends(get_db)
):

    if data.category_id is not None:

        category = db.execute(
            select(Categories).where(
                Categories.c.id == data.category_id
            )
        ).mappings().first()

        if not category:
            raise HTTPException(
                status_code=404,
                detail="Category not found"
            )

    existing = db.execute(
        select(ProductAttributes).where(
            and_(
                ProductAttributes.c.code == data.code,
                ProductAttributes.c.category_id == data.category_id
            )
        )
    ).mappings().first()

    if existing:

        raise HTTPException(
            status_code=409,
            detail="Attribute code already exists for this category"
        )

    if data.allowed_values is not None and data.data_type != "text":

        raise HTTPException(
            status_code=400,
            detail="allowed_values is supported only for text attributes"
        )

    result = db.execute(
        insert(ProductAttributes).values(
            category_id=data.category_id,
            name=data.name,
            code=data.code,
            data_type=data.data_type,
            allowed_values=data.allowed_values,
            is_required=data.is_required,
            is_active=data.is_active,
        )
    )

    db.commit()

    return {
        "message": "Product attribute created successfully",
        "attribute_id": result.inserted_primary_key[0]
    }


# =====================================================
# 5. LIST ATTRIBUTES
# GET /product-attributes/
# =====================================================

@router.get(
    "/",
    dependencies=[
        Depends(require_roles(*READ_ROLES))
    ]
)
def list_attributes(
    category_id: int | None = Query(default=None),
    db: Session = Depends(get_db)
):

    query = select(ProductAttributes)

    if category_id is not None:

        query = query.where(
            ProductAttributes.c.is_active == True
        ).where(
            ProductAttributes.c.category_id.in_(
                [category_id]
            ) |
            ProductAttributes.c.category_id.is_(None)
        )

    result = db.execute(
        query.order_by(ProductAttributes.c.id.desc())
    ).mappings().all()

    return [
        dict(row)
        for row in result
    ]


# =====================================================
# 6. GET SINGLE ATTRIBUTE
# GET /product-attributes/{attribute_id}
# =====================================================

@router.get(
    "/{attribute_id}",
    dependencies=[
        Depends(require_roles(*READ_ROLES))
    ]
)
def get_attribute(
    attribute_id: int,
    db: Session = Depends(get_db)
):

    attribute = db.execute(
        select(ProductAttributes).where(
            ProductAttributes.c.id == attribute_id
        )
    ).mappings().first()

    if not attribute:

        raise HTTPException(
            status_code=404,
            detail="Attribute not found"
        )

    return dict(attribute)


# =====================================================
# 7. UPDATE ATTRIBUTE
# PUT /product-attributes/{attribute_id}
# =====================================================

@router.put(
    "/{attribute_id}",
    dependencies=[
        Depends(require_roles(*MANAGEMENT_ROLES))
    ]
)
def update_attribute(
    attribute_id: int,
    data: ProductAttributeUpdate,
    db: Session = Depends(get_db)
):

    attribute = db.execute(
        select(ProductAttributes).where(
            ProductAttributes.c.id == attribute_id
        )
    ).mappings().first()

    if not attribute:

        raise HTTPException(
            status_code=404,
            detail="Attribute not found"
        )

    update_data = data.model_dump(exclude_unset=True)

    if "name" in update_data and update_data["name"] is None:
        raise HTTPException(
            status_code=400,
            detail="Attribute name cannot be null"
        )

    if "allowed_values" in update_data:

        if (
            update_data["allowed_values"] is not None
            and attribute["data_type"] != "text"
        ):
            raise HTTPException(
                status_code=400,
                detail="allowed_values is supported only for text attributes"
            )

        if update_data["allowed_values"] is not None:

            existing_values = db.execute(
                select(ProductAttributeValues.c.value).where(
                    ProductAttributeValues.c.attribute_id == attribute_id
                )
            ).scalars().all()

            invalid_values = [
                value
                for value in existing_values
                if value not in update_data["allowed_values"]
            ]

            if invalid_values:
                raise HTTPException(
                    status_code=400,
                    detail="New allowed_values would invalidate existing product values"
                )

    if not update_data:

        raise HTTPException(
            status_code=400,
            detail="No update data provided"
        )

    db.execute(
        update(ProductAttributes)
        .where(ProductAttributes.c.id == attribute_id)
        .values(**update_data)
    )

    db.commit()

    return {
        "message": "Product attribute updated successfully"
    }


# =====================================================
# 8. DELETE ATTRIBUTE
# DELETE /product-attributes/{attribute_id}
# =====================================================

@router.delete(
    "/{attribute_id}",
    dependencies=[
        Depends(require_roles(*MANAGEMENT_ROLES))
    ]
)
def delete_attribute(
    attribute_id: int,
    db: Session = Depends(get_db)
):

    attribute = db.execute(
        select(ProductAttributes).where(
            ProductAttributes.c.id == attribute_id
        )
    ).mappings().first()

    if not attribute:

        raise HTTPException(
            status_code=404,
            detail="Attribute not found"
        )

    db.execute(
        delete(ProductAttributeValues).where(
            ProductAttributeValues.c.attribute_id == attribute_id
        )
    )

    db.execute(
        delete(ProductAttributes).where(
            ProductAttributes.c.id == attribute_id
        )
    )

    db.commit()

    return {
        "message": "Product attribute and its assigned values deleted successfully"
    }


# =====================================================
# 9. ASSIGN ATTRIBUTE TO PRODUCT
# POST /product-attributes/products/{product_id}
# =====================================================

@router.post(
    "/products/{product_id}",
    status_code=201,
    dependencies=[
        Depends(require_roles(*MANAGEMENT_ROLES))
    ]
)
def assign_attribute_to_product(
    product_id: int,
    data: ProductAttributeValueCreate,
    db: Session = Depends(get_db)
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

    attribute = db.execute(
        select(ProductAttributes).where(
            ProductAttributes.c.id == data.attribute_id
        )
    ).mappings().first()

    if not attribute:

        raise HTTPException(
            status_code=404,
            detail="Attribute not found"
        )

    if not attribute["is_active"]:

        raise HTTPException(
            status_code=400,
            detail="Attribute is inactive"
        )

    validate_product_category(
        attribute,
        product
    )

    validate_value(
        attribute,
        data.value
    )

    existing = db.execute(
        select(ProductAttributeValues).where(
            and_(
                ProductAttributeValues.c.product_id == product_id,
                ProductAttributeValues.c.attribute_id == data.attribute_id
            )
        )
    ).mappings().first()

    if existing:

        raise HTTPException(
            status_code=409,
            detail="This attribute is already assigned to the product"
        )

    result = db.execute(
        insert(ProductAttributeValues).values(
            product_id=product_id,
            attribute_id=data.attribute_id,
            value=data.value
        )
    )

    db.commit()

    return {
        "message": "Attribute assigned to product successfully",
        "assignment_id": result.inserted_primary_key[0]
    }


# =====================================================
# 10. UPDATE PRODUCT ATTRIBUTE VALUE
# PUT /product-attributes/products/{product_id}/{attribute_id}
# =====================================================

@router.put(
    "/products/{product_id}/{attribute_id}",
    dependencies=[
        Depends(require_roles(*MANAGEMENT_ROLES))
    ]
)
def update_product_attribute(
    product_id: int,
    attribute_id: int,
    data: ProductAttributeValueCreate,
    db: Session = Depends(get_db)
):

    if data.attribute_id != attribute_id:

        raise HTTPException(
            status_code=400,
            detail="Request attribute_id does not match URL attribute_id"
        )

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

    attribute = db.execute(
        select(ProductAttributes).where(
            ProductAttributes.c.id == attribute_id
        )
    ).mappings().first()

    if not attribute:

        raise HTTPException(
            status_code=404,
            detail="Attribute not found"
        )

    if not attribute["is_active"]:

        raise HTTPException(
            status_code=400,
            detail="Attribute is inactive"
        )

    validate_product_category(
        attribute,
        product
    )

    validate_value(
        attribute,
        data.value
    )

    existing = db.execute(
        select(ProductAttributeValues).where(
            and_(
                ProductAttributeValues.c.product_id == product_id,
                ProductAttributeValues.c.attribute_id == attribute_id
            )
        )
    ).mappings().first()

    if not existing:

        raise HTTPException(
            status_code=404,
            detail="Product attribute assignment not found"
        )

    db.execute(
        update(ProductAttributeValues)
        .where(
            and_(
                ProductAttributeValues.c.product_id == product_id,
                ProductAttributeValues.c.attribute_id == attribute_id
            )
        )
        .values(value=data.value)
    )

    db.commit()

    return {
        "message": "Product attribute value updated successfully"
    }


# =====================================================
# 11. GET PRODUCT ATTRIBUTES
# GET /product-attributes/products/{product_id}
# =====================================================

@router.get(
    "/products/{product_id}",
    dependencies=[
        Depends(require_roles(*READ_ROLES))
    ]
)
def get_product_attributes(
    product_id: int,
    db: Session = Depends(get_db)
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

    query = (
        select(
            ProductAttributeValues.c.id,
            ProductAttributeValues.c.product_id,
            ProductAttributeValues.c.attribute_id,
            ProductAttributeValues.c.value,
            ProductAttributes.c.name,
            ProductAttributes.c.code,
            ProductAttributes.c.data_type,
            ProductAttributes.c.category_id,
            ProductAttributes.c.is_required,
        )
        .select_from(
            ProductAttributeValues.join(
                ProductAttributes,
                ProductAttributeValues.c.attribute_id
                == ProductAttributes.c.id
            )
        )
        .where(
            ProductAttributeValues.c.product_id == product_id
        )
    )

    result = db.execute(query).mappings().all()

    return [
        dict(row)
        for row in result
    ]


# =====================================================
# 12. FILTER PRODUCTS BY ATTRIBUTE
# GET /product-attributes/filter/products
# =====================================================

@router.get(
    "/filter/products",
    dependencies=[
        Depends(require_roles(*READ_ROLES))
    ]
)
def filter_products_by_attribute(
    attribute_code: str = Query(min_length=2),
    value: str = Query(min_length=1),
    category_id: int | None = Query(default=None),
    db: Session = Depends(get_db)
):

    query = (
        select(Products)
        .select_from(
            Products.join(
                ProductAttributeValues,
                Products.c.id == ProductAttributeValues.c.product_id
            ).join(
                ProductAttributes,
                ProductAttributeValues.c.attribute_id
                == ProductAttributes.c.id
            )
        )
        .where(
            and_(
                ProductAttributes.c.code == attribute_code,
                ProductAttributes.c.is_active == True,
                ProductAttributeValues.c.value == value,
                Products.c.is_active == True,
            )
        )
    )

    if category_id is not None:

        query = query.where(
            Products.c.category_id == category_id
        )

    products = db.execute(query).mappings().all()

    return {
        "attribute_code": attribute_code,
        "value": value,
        "total_products": len(products),
        "products": [
            dict(product)
            for product in products
        ]
    }
