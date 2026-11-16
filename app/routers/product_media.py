
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Query
)
from fastapi.responses import FileResponse
from sqlalchemy import select, insert, delete
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.resources import Products, ProductVariants, ProductMedia


router = APIRouter(
    prefix="/product-media",
    tags=["Module 10 - Product Images and Documents"]
)


# Project root and upload directory
BASE_DIR = Path(__file__).resolve().parents[2]
UPLOAD_DIR = BASE_DIR / "uploads" / "products"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# Allowed extensions and MIME types
ALLOWED_FILES = {
    ".jpg": ["image/jpeg"],
    ".jpeg": ["image/jpeg"],
    ".png": ["image/png"],
    ".webp": ["image/webp"],
    ".gif": ["image/gif"],
    ".pdf": ["application/pdf"],
    ".txt": ["text/plain"],
    ".csv": ["text/csv", "application/vnd.ms-excel"],
    ".docx": [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ],
    ".xlsx": [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ]
}


def get_product_or_404(db: Session, product_id: int):
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


def get_media_or_404(db: Session, media_id: int):
    media = db.execute(
        select(ProductMedia).where(
            ProductMedia.c.id == media_id
        )
    ).mappings().first()

    if not media:
        raise HTTPException(
            status_code=404,
            detail="Product media not found"
        )

    return dict(media)


def validate_variant(
    db: Session,
    product_id: int,
    variant_id: int | None
):
    if variant_id is None:
        return

    variant = db.execute(
        select(ProductVariants).where(
            ProductVariants.c.id == variant_id,
            ProductVariants.c.product_id == product_id
        )
    ).mappings().first()

    if not variant:
        raise HTTPException(
            status_code=404,
            detail="Variant not found for this product"
        )


def validate_file(file: UploadFile):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="File name is required"
        )

    # Handle both Windows and Linux style paths
    original_name = file.filename.replace("\\", "/").split("/")[-1]
    extension = Path(original_name).suffix.lower()

    if extension not in ALLOWED_FILES:
        raise HTTPException(
            status_code=400,
            detail="File type is not allowed"
        )

    if file.content_type not in ALLOWED_FILES[extension]:
        raise HTTPException(
            status_code=400,
            detail="File MIME type does not match the allowed file type"
        )

    return original_name, extension


def validate_file_signature(extension: str, content: bytes):
    signatures = {
        ".jpg": lambda b: b.startswith(b"\xff\xd8\xff"),
        ".jpeg": lambda b: b.startswith(b"\xff\xd8\xff"),
        ".png": lambda b: b.startswith(b"\x89PNG\r\n\x1a\n"),
        ".gif": lambda b: b.startswith((b"GIF87a", b"GIF89a")),
        ".webp": lambda b: (
            len(b) >= 12 and b[:4] == b"RIFF" and b[8:12] == b"WEBP"
        ),
        ".pdf": lambda b: b.startswith(b"%PDF-"),
    }

    # Validate file signatures for formats with known signatures.
    # Office documents, CSV and TXT use extension/MIME validation here.
    check = signatures.get(extension)

    if check and not check(content):
        raise HTTPException(
            status_code=400,
            detail="File content does not match its extension"
        )


def get_safe_file_path(stored_path: str):
    file_path = (BASE_DIR / stored_path).resolve()

    try:
        file_path.relative_to(UPLOAD_DIR.resolve())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid file path"
        )

    return file_path


# 1. Upload Product Image or Document
@router.post("/products/{product_id}", status_code=201)
async def upload_product_media(
    product_id: int,
    file: UploadFile = File(...),
    variant_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    get_product_or_404(db, product_id)

    validate_variant(db, product_id, variant_id)

    original_name, extension = validate_file(file)

    content = await file.read(MAX_FILE_SIZE + 1)

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Empty files are not allowed"
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Maximum file size allowed is 10 MB"
        )

    validate_file_signature(extension, content)

    # Generate a unique stored filename
    stored_name = f"{uuid.uuid4().hex}{extension}"
    destination = UPLOAD_DIR / stored_name

    relative_path = (
        Path("uploads") / "products" / stored_name
    ).as_posix()

    try:
        destination.write_bytes(content)

        result = db.execute(
            insert(ProductMedia).values(
                product_id=product_id,
                variant_id=variant_id,
                file_name=original_name,
                file_path=relative_path,
                mime_type=file.content_type,
                file_size=len(content)
            )
        )

        db.commit()

        media_id = result.inserted_primary_key[0]
        media = get_media_or_404(db, media_id)

        return {
            "message": "File uploaded successfully",
            "media": media
        }

    except Exception:
        db.rollback()

        if destination.exists():
            destination.unlink()

        raise

    finally:
        await file.close()


# 2. Get All Files for a Product
@router.get("/products/{product_id}")
def get_product_media(
    product_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    get_product_or_404(db, product_id)

    result = db.execute(
        select(ProductMedia)
        .where(ProductMedia.c.product_id == product_id)
        .order_by(ProductMedia.c.id.desc())
    ).mappings().all()

    return {
        "product_id": product_id,
        "total_files": len(result),
        "files": [dict(row) for row in result]
    }


# 3. Get Individual File Metadata
@router.get("/{media_id}")
def get_media_details(
    media_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_media_or_404(db, media_id)


# 4. Download Authorized File
@router.get("/{media_id}/download")
def download_media(
    media_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    media = get_media_or_404(db, media_id)

    file_path = get_safe_file_path(media["file_path"])

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="File not found on server"
        )

    return FileResponse(
        path=file_path,
        media_type=media["mime_type"],
        filename=media["file_name"]
    )


# 5. Delete Product Image or Document
@router.delete("/{media_id}")
def delete_media(
    media_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    media = get_media_or_404(db, media_id)

    file_path = get_safe_file_path(media["file_path"])

    # Delete database metadata first
    db.execute(
        delete(ProductMedia).where(
            ProductMedia.c.id == media_id
        )
    )

    db.commit()

    # Remove physical file if it exists
    if file_path.is_file():
        file_path.unlink()

    return {
        "message": "File deleted successfully",
        "media_id": media_id
    }
