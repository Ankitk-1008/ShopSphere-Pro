
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserActivity
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.core.security import hash_password
from app.dependencies.auth import require_roles, ALLOWED_ROLES

router = APIRouter(prefix="/users", tags=["Module 2 - User Management"])


@router.post("/", response_model=UserResponse)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("Super Admin", "Admin"))
):
    if data.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")

    # Only Super Admin can create another Super Admin.
    if data.role == "Super Admin" and admin.role != "Super Admin":
        raise HTTPException(status_code=403, detail="Only Super Admin can assign this role")

    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=409, detail="Email already exists")

    if data.phone and db.query(User).filter(User.phone == data.phone).first():
        raise HTTPException(status_code=409, detail="Phone already exists")

    user = User(
        full_name=data.full_name,
        email=data.email,
        phone=data.phone,
        hashed_password=hash_password(data.password),
        role=data.role
    )

    db.add(user)
    db.flush()

    db.add(UserActivity(
        user_id=admin.id,
        action="CREATE_USER",
        details=f"Created user ID {user.id}, role {user.role}"
    ))

    db.commit()
    db.refresh(user)
    return user


@router.get("/", response_model=list[UserResponse])
def list_users(
    search: str | None = Query(default=None),
    role: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("Super Admin", "Admin"))
):
    query = db.query(User)

    if search:
        query = query.filter(
            User.full_name.ilike(f"%{search}%") |
            User.email.ilike(f"%{search}%")
        )

    if role:
        query = query.filter(User.role == role)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    return query.order_by(User.id.desc()).offset(skip).limit(limit).all()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("Super Admin", "Admin"))
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("Super Admin", "Admin"))
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    updates = data.model_dump(exclude_unset=True)

    if "role" in updates:
        new_role = updates["role"]

        if new_role not in ALLOWED_ROLES:
            raise HTTPException(status_code=400, detail="Invalid role")

        if new_role == "Super Admin" and admin.role != "Super Admin":
            raise HTTPException(status_code=403, detail="Only Super Admin can assign this role")

        if user.role == "Super Admin" and admin.role != "Super Admin":
            raise HTTPException(status_code=403, detail="Only Super Admin can update this account")

    if user.id == admin.id and updates.get("is_active") is False:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")

    for field, value in updates.items():
        setattr(user, field, value)

    db.add(UserActivity(
        user_id=admin.id,
        action="UPDATE_USER",
        details=f"Updated user ID {user.id}: {', '.join(updates.keys())}"
    ))

    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/deactivate")
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("Super Admin", "Admin"))
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")

    if user.role == "Super Admin" and admin.role != "Super Admin":
        raise HTTPException(status_code=403, detail="Only Super Admin can deactivate this account")

    user.is_active = False

    # Revoke all tokens of the deactivated user.
    for token_session in user.tokens:
        token_session.revoked = True

    db.add(UserActivity(
        user_id=admin.id,
        action="DEACTIVATE_USER",
        details=f"Deactivated user ID {user.id}"
    ))

    db.commit()
    return {"message": "User deactivated successfully"}


@router.get("/{user_id}/activities")
def get_user_activities(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("Super Admin", "Admin"))
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    activities = db.query(UserActivity).filter(
        UserActivity.user_id == user_id
    ).order_by(UserActivity.id.desc()).limit(100).all()

    return [
        {
            "id": activity.id,
            "action": activity.action,
            "details": activity.details,
            "created_at": activity.created_at
        }
        for activity in activities
    ]
