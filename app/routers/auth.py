
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import get_db
from app.models.user import User, TokenSession, UserActivity
from app.schemas.auth import (
    RegisterSchema, LoginSchema, RefreshSchema
)
from app.core.security import (
    hash_password, verify_password,
    create_token, decode_token
)
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["Module 1 - Authentication"])


def save_token(db, user_id, token_data, token_type):
    token, jti, expires = token_data

    db.add(TokenSession(
        user_id=user_id,
        jti=jti,
        token_type=token_type,
        expires_at=expires,
        revoked=False
    ))

    return token


def log_activity(db, user_id, action, details=None):
    db.add(UserActivity(
        user_id=user_id,
        action=action,
        details=details
    ))


@router.post("/register")
def register(data: RegisterSchema, db: Session = Depends(get_db)):
    existing = db.query(User).filter(
        User.email == data.email
    ).first()

    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    if data.phone:
        phone_exists = db.query(User).filter(
            User.phone == data.phone
        ).first()

        if phone_exists:
            raise HTTPException(status_code=409, detail="Phone already registered")

    user = User(
        full_name=data.full_name,
        email=data.email,
        phone=data.phone,
        hashed_password=hash_password(data.password),
        role="Customer"
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    log_activity(db, user.id, "REGISTER", "Customer registered")
    db.commit()

    return {
        "message": "Registration successful",
        "user_id": user.id,
        "email": user.email,
        "role": user.role
    }


@router.post("/login")
def login(data: LoginSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    access = create_token(user.id, "access")
    refresh = create_token(user.id, "refresh")

    access_token = save_token(db, user.id, access, "access")
    refresh_token = save_token(db, user.id, refresh, "refresh")

    user.last_login_at = datetime.now(timezone.utc)
    log_activity(db, user.id, "LOGIN", "User logged in")

    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "role": user.role
    }


@router.post("/refresh")
def refresh_token(data: RefreshSchema, db: Session = Depends(get_db)):
    try:
        payload = decode_token(data.refresh_token)

        if payload.get("type") != "refresh":
            raise ValueError("Not a refresh token")

        user_id = int(payload["sub"])
        jti = payload["jti"]

    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    old_session = db.query(TokenSession).filter(
        TokenSession.jti == jti,
        TokenSession.user_id == user_id,
        TokenSession.token_type == "refresh",
        TokenSession.revoked == False
    ).first()
    
    now = datetime.now(timezone.utc)


    if old_session and old_session.expires_at.tzinfo is None:
        expires_at = old_session.expires_at.replace(tzinfo=timezone.utc)
    else:
        expires_at = old_session.expires_at if old_session else None

    if not old_session or expires_at <= now:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token"
        )

    

    user = db.query(User).filter(
        User.id == user_id,
        User.is_active == True
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # Rotate refresh token: revoke old one and issue a new pair.
    old_session.revoked = True

    access = create_token(user.id, "access")
    refresh = create_token(user.id, "refresh")

    access_token = save_token(db, user.id, access, "access")
    new_refresh_token = save_token(db, user.id, refresh, "refresh")

    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.post("/logout")
def logout(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user is None:
        raise HTTPException(
            status_code=401,
            detail="User authentication required"
        )

    token_session = db.query(TokenSession).filter(
        TokenSession.user_id == current_user.id,
        TokenSession.revoked == False
    ).first()

    if not token_session:
        raise HTTPException(
            status_code=404,
            detail="Active session not found"
        )

    token_session.revoked = True
    db.commit()

    return {"message": "Logout successful"}

@router.get("/me")
def my_profile(
    current_user: User = Depends(get_current_user)
):
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified
    }