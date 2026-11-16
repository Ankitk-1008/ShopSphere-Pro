
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe


from app.dependencies.auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.customer_registration import CustomerRegistration
from app.schemas.customer_registration import (
    CustomerRegisterSchema,
    EmailVerificationSchema,
    CustomerRegistrationUpdateSchema
)

from app.core.security import hash_password

router = APIRouter(
    prefix="/customers",
    tags=["Module 3 - Customer Registration"]
)


@router.post("/register")
def register_customer(
    data: CustomerRegisterSchema,
    db: Session = Depends(get_db)
):
    # Check duplicate email
    existing_email = db.query(User).filter(
        User.email == data.email
    ).first()

    if existing_email:
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    # Check duplicate phone
    existing_phone = db.query(User).filter(
        User.phone == data.phone
    ).first()

    if existing_phone:
        raise HTTPException(
            status_code=409,
            detail="Phone number already registered"
        )

    try:
        # Create customer user
        user = User(
            full_name=data.full_name,
            email=data.email,
            phone=data.phone,
            hashed_password=hash_password(data.password),
            role="Customer",
            is_active=True,
            is_verified=False
        )

        db.add(user)
        db.flush()

        # Generate email verification token
        verification_token = token_urlsafe(32)

        registration = CustomerRegistration(
            user_id=user.id,
            registration_status="PENDING",
            email_verified=False,
            verification_token=verification_token,
            verification_expires_at=(
                datetime.now(timezone.utc) + timedelta(hours=24)
            )
        )

        db.add(registration)
        db.commit()
        db.refresh(user)

        return {
            "message": "Customer registered successfully. Verify your email.",
            "user_id": user.id,
            "email": user.email,
            "registration_status": "PENDING",
            "email_verified": False,

            # Development testing only.
            # In production, send this token by email.
            "verification_token": verification_token
        }

    except Exception:
        db.rollback()
        raise


@router.post("/verify-email")
def verify_customer_email(
    data: EmailVerificationSchema,
    db: Session = Depends(get_db)
):
    registration = db.query(CustomerRegistration).filter(
        CustomerRegistration.verification_token == data.token
    ).first()

    if not registration:
        raise HTTPException(
            status_code=400,
            detail="Invalid verification token"
        )

    if registration.email_verified:
        raise HTTPException(
            status_code=400,
            detail="Email already verified"
        )

    expires_at = registration.verification_expires_at

    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if not expires_at or expires_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Verification token expired"
        )

    user = db.query(User).filter(
        User.id == registration.user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    registration.email_verified = True
    registration.registration_status = "VERIFIED"
    registration.verification_token = None
    registration.verification_expires_at = None

    user.is_verified = True

    db.commit()

    return {
        "message": "Email verified successfully",
        "user_id": user.id,
        "email": user.email,
        "registration_status": "VERIFIED",
        "email_verified": True
    }


@router.get("/{user_id}/registration-status")
def get_registration_status(
    user_id: int,
    db: Session = Depends(get_db)
):
    registration = db.query(CustomerRegistration).filter(
        CustomerRegistration.user_id == user_id
    ).first()

    if not registration:
        raise HTTPException(
            status_code=404,
            detail="Customer registration not found"
        )

    return {
        "user_id": registration.user_id,
        "registration_status": registration.registration_status,
        "email_verified": registration.email_verified
    }




# -----------------------------------------
# PUT - Update Customer Registration
# -----------------------------------------

@router.put("/{user_id}/registration")
def update_customer_registration(
    user_id: int,
    data: CustomerRegistrationUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Customer can update only own account.
    # Admin can update any customer.
    is_admin = current_user.role.lower() in ["admin", "super admin"]

    if current_user.id != user_id and not is_admin:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to update this customer"
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    registration = db.query(CustomerRegistration).filter(
        CustomerRegistration.user_id == user_id
    ).first()

    if not registration:
        raise HTTPException(
            status_code=404,
            detail="Customer registration not found"
        )

    update_data = data.model_dump(exclude_unset=True)

    # Check duplicate email
    if "email" in update_data and update_data["email"]:
        existing_email = db.query(User).filter(
            User.email == str(update_data["email"]),
            User.id != user_id
        ).first()

        if existing_email:
            raise HTTPException(
                status_code=409,
                detail="Email already registered"
            )

    # Check duplicate phone
    if "phone" in update_data and update_data["phone"]:
        existing_phone = db.query(User).filter(
            User.phone == update_data["phone"],
            User.id != user_id
        ).first()

        if existing_phone:
            raise HTTPException(
                status_code=409,
                detail="Phone number already registered"
            )

    # Update name
    if "full_name" in update_data:
        user.full_name = update_data["full_name"]

    # Update email and reset verification
    if "email" in update_data:
        new_email = str(update_data["email"])

        if new_email != user.email:
            user.email = new_email
            user.is_verified = False

            registration.email_verified = False
            registration.registration_status = "PENDING"

            # Generate new verification token
            registration.verification_token = secrets.token_urlsafe(32)
            registration.verification_expires_at = (
                datetime.now(timezone.utc) + timedelta(hours=24)
            )

    # Update phone in both tables
    if "phone" in update_data:
        user.phone = update_data["phone"]
        registration.phone = update_data["phone"]

    db.commit()
    db.refresh(user)
    db.refresh(registration)

    return {
        "message": "Customer registration updated successfully",
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "registration_status": registration.registration_status,
        "email_verified": registration.email_verified,
        "verification_token": registration.verification_token
    }


# -----------------------------------------
# DELETE - Delete Customer Registration
# -----------------------------------------

@router.delete("/{user_id}/registration")
def delete_customer_registration(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    is_admin = current_user.role.lower() in ["admin", "super admin"]

    if current_user.id != user_id and not is_admin:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to delete this customer"
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    registration = db.query(CustomerRegistration).filter(
        CustomerRegistration.user_id == user_id
    ).first()

    if not registration:
        raise HTTPException(
            status_code=404,
            detail="Customer registration not found"
        )

    # Delete registration first, then user account
    db.delete(registration)
    db.delete(user)

    db.commit()

    return {
        "message": "Customer registration and account deleted successfully",
        "user_id": user_id
    }
