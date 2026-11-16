from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user

from app.models.user import User
from app.models.address import Address

from app.schemas.address import (
    AddressCreate,
    AddressUpdate,
    DefaultAddressUpdate
)


router = APIRouter(
    prefix="/customers/addresses",
    tags=["Module 5 - Address Management"]
)


# -----------------------------------------
# POST - Add New Address
# -----------------------------------------


@router.post("/")
def create_address(
    data: AddressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    address_data = data.model_dump()

    if address_data["is_default"]:
        db.query(Address).filter(
            Address.user_id == current_user.id,
            Address.address_type == address_data["address_type"]
        ).update(
            {"is_default": False},
            synchronize_session=False
        )

    address = Address(
        user_id=current_user.id,
        **address_data
    )

    db.add(address)
    db.commit()
    db.refresh(address)

    return {
        "message": "Address added successfully",
        "address_id": address.id,
        "address_type": address.address_type,
        "is_default": address.is_default
    }


# -----------------------------------------
# GET - Get All My Addresses
# -----------------------------------------

@router.get("/me")
def get_my_addresses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    addresses = db.query(Address).filter(
        Address.user_id == current_user.id
    ).order_by(Address.id.desc()).all()

    return {
        "total_addresses": len(addresses),
        "addresses": addresses
    }


# -----------------------------------------
# GET - Get Address by ID
# -----------------------------------------

@router.get("/{address_id}")
def get_address(
    address_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    address = db.query(Address).filter(
        Address.id == address_id,
        Address.user_id == current_user.id
    ).first()

    if not address:
        raise HTTPException(
            status_code=404,
            detail="Address not found"
        )

    return address


# -----------------------------------------
# PUT - Update Address
# -----------------------------------------


@router.put("/{address_id}")
def update_address(
    address_id: int,
    data: AddressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    address = db.query(Address).filter(
        Address.id == address_id,
        Address.user_id == current_user.id
    ).first()

    if not address:
        raise HTTPException(
            status_code=404,
            detail="Address not found"
        )

    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Please provide fields to update"
        )

    if (
        update_data.get("is_default") is True
    ):
        db.query(Address).filter(
            Address.user_id == current_user.id,
            Address.address_type == address.address_type
        ).update(
            {"is_default": False},
            synchronize_session=False
        )

    for field, value in update_data.items():
        setattr(address, field, value)

    db.commit()
    db.refresh(address)

    return {
        "message": "Address updated successfully",
        "address_id": address.id,
        "address_type": address.address_type
    }


# -----------------------------------------
# DELETE - Delete Address
# -----------------------------------------

@router.delete("/{address_id}")
def delete_address(
    address_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    address = db.query(Address).filter(
        Address.id == address_id,
        Address.user_id == current_user.id
    ).first()

    if not address:
        raise HTTPException(
            status_code=404,
            detail="Address not found"
        )

    db.delete(address)
    db.commit()

    return {
        "message": "Address deleted successfully",
        "address_id": address_id
    }


# -----------------------------------------
# PATCH - Set Default Address
# -----------------------------------------

@router.patch("/{address_id}/default")
def set_default_address(
    address_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    address = db.query(Address).filter(
        Address.id == address_id,
        Address.user_id == current_user.id
    ).first()

    if not address:
        raise HTTPException(
            status_code=404,
            detail="Address not found"
        )

    # Remove existing default for this address type
    db.query(Address).filter(
        Address.user_id == current_user.id,
        Address.address_type == address.address_type
    ).update(
        {"is_default": False},
        synchronize_session=False
    )

    address.is_default = True

    db.commit()
    db.refresh(address)

    return {
        "message": "Default address updated successfully",
        "address_id": address.id,
        "address_type": address.address_type,
        "is_default": address.is_default
    }