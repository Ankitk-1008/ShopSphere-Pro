from fastapi import FastAPI

from app.routers import auth, users

from app.routers import customer_registration
from app.routers import customer_profile
from app.routers import address
from app.routers import category
from app.routers import brand
from app.routers import product
from app.routers import product_variant
from app.routers import product_media


app = FastAPI(
    title="ShopSphere Pro E-Commerce API",
    description="E-Commerce Backend - Modules 1 to 10",
    version="1.0.0"
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(
    customer_registration.router,
    prefix="/api/v1"
)
app.include_router(customer_profile.router, prefix="/api/v1")
app.include_router(address.router, prefix="/api/v1")
app.include_router(category.router, prefix="/api/v1")
app.include_router(brand.router, prefix="/api/v1")
app.include_router(product.router, prefix="/api/v1")
app.include_router(
    product_variant.router,
    prefix="/api/v1"
)
app.include_router(
    product_media.router,
    prefix="/api/v1"
)

@app.get("/")
def home():
    return {
        "message": "Welcome to ShopSphere Pro API",
        "modules": [
            "Authentication and Authorization",
            "User Management"
        ]
    }