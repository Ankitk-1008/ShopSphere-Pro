from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.profile_history import ProfileChangeHistory
from app.models.deactivation_request import AccountDeactivationRequest
from app.schemas.customer_profile import (
    CustomerProfileUpdate,
    DeactivationRequestCreate,
    DeactivationRequestReview
)
from app.dependencies.auth import get_current_user


router = APIRouter(
    prefix="/customers/profile",
    tags=["Module 4 - Customer Profile"]
)


def is_admin(user: User):
    return user.role.lower() in ["admin", "super admin"]


def check_profile_access(user_id: int, current_user: User):
    if current_user.id != user_id and not is_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to access this profile"
        )


# -----------------------------------------
# GET - Get Own Profile
# -----------------------------------------

@router.get("/me")
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = db.query(User).filter(
        User.id == current_user.id
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="Profile not found")

    return {
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "created_at": user.created_at
    }


# -----------------------------------------
# GET - Get Customer Profile by User ID
# Admin or own profile only
# -----------------------------------------

@router.get("/{user_id}")
def get_customer_profile(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_profile_access(user_id, current_user)

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="Customer not found")

    return {
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "is_active": user.is_active,
        "is_verified": user.is_verified
    }


# -----------------------------------------
# PUT - Update Own Profile
# -----------------------------------------

@router.put("/me")
def update_my_profile(
    data: CustomerProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = db.query(User).filter(
        User.id == current_user.id
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="Profile not found")

    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Please provide at least one field to update"
        )

    # Check duplicate email
    if "email" in update_data and update_data["email"] is not None:
        new_email = str(update_data["email"])

        existing_email = db.query(User).filter(
            User.email == new_email,
            User.id != user.id
        ).first()

        if existing_email:
            raise HTTPException(
                status_code=409,
                detail="Email already registered"
            )

        update_data["email"] = new_email

    # Check duplicate phone
    if "phone" in update_data and update_data["phone"] is not None:
        existing_phone = db.query(User).filter(
            User.phone == update_data["phone"],
            User.id != user.id
        ).first()

        if existing_phone:
            raise HTTPException(
                status_code=409,
                detail="Phone number already registered"
            )

    # Save profile changes in history
    for field, new_value in update_data.items():
        old_value = getattr(user, field)

        if old_value != new_value:
            history = ProfileChangeHistory(
                user_id=user.id,
                changed_by=current_user.id,
                field_name=field,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(new_value) if new_value is not None else None
            )

            db.add(history)
            setattr(user, field, new_value)

            # New email needs verification again
            if field == "email":
                user.is_verified = False

    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Profile update failed"
        )

    return {
        "message": "Customer profile updated successfully",
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone
    }


# -----------------------------------------
# GET - Profile Change History
# -----------------------------------------

@router.get("/history/{user_id}")
def get_profile_history(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_profile_access(user_id, current_user)

    history = db.query(ProfileChangeHistory).filter(
        ProfileChangeHistory.user_id == user_id
    ).order_by(
        ProfileChangeHistory.changed_at.desc()
    ).all()

    return {
        "user_id": user_id,
        "total_changes": len(history),
        "history": [
            {
                "id": item.id,
                "field_name": item.field_name,
                "old_value": item.old_value,
                "new_value": item.new_value,
                "changed_by": item.changed_by,
                "changed_at": item.changed_at
            }
            for item in history
        ]
    }


# -----------------------------------------
# POST - Request Account Deactivation
# -----------------------------------------

@router.post("/deactivation-request")
def request_account_deactivation(
    data: DeactivationRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_active:
        raise HTTPException(
            status_code=400,
            detail="Account is already inactive"
        )

    existing_request = db.query(AccountDeactivationRequest).filter(
        AccountDeactivationRequest.user_id == current_user.id,
        AccountDeactivationRequest.status == "PENDING"
    ).first()

    if existing_request:
        raise HTTPException(
            status_code=409,
            detail="A deactivation request is already pending"
        )

    request = AccountDeactivationRequest(
        user_id=current_user.id,
        reason=data.reason,
        status="PENDING"
    )

    db.add(request)
    db.commit()
    db.refresh(request)

    return {
        "message": "Account deactivation request submitted successfully",
        "request_id": request.id,
        "status": request.status
    }


# -----------------------------------------
# GET - Admin View Pending Requests
# -----------------------------------------

@router.get("/admin/deactivation-requests")
def get_deactivation_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    requests = db.query(AccountDeactivationRequest).filter(
        AccountDeactivationRequest.status == "PENDING"
    ).order_by(
        AccountDeactivationRequest.requested_at.desc()
    ).all()

    return [
        {
            "request_id": item.id,
            "user_id": item.user_id,
            "reason": item.reason,
            "status": item.status,
            "requested_at": item.requested_at
        }
        for item in requests
    ]


# -----------------------------------------
# PUT - Admin Approve or Reject Request
# -----------------------------------------

@router.put("/admin/deactivation-requests/{request_id}")
def review_deactivation_request(
    request_id: int,
    data: DeactivationRequestReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    request = db.query(AccountDeactivationRequest).filter(
        AccountDeactivationRequest.id == request_id
    ).first()

    if not request:
        raise HTTPException(
            status_code=404,
            detail="Deactivation request not found"
        )

    if request.status != "PENDING":
        raise HTTPException(
            status_code=400,
            detail="This request has already been reviewed"
        )

    request.status = data.status
    request.reviewed_by = current_user.id
    request.reviewed_at = datetime.now(timezone.utc)

    if data.status == "APPROVED":
        user = db.query(User).filter(
            User.id == request.user_id
        ).first()

        if user:
            user.is_active = False

    db.commit()

    return {
        "message": f"Deactivation request {data.status.lower()} successfully",
        "request_id": request.id,
        "status": request.status
    }