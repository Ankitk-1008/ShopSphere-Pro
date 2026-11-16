
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, TokenSession
from app.core.security import decode_token

bearer_scheme = HTTPBearer()

ALLOWED_ROLES = {
    "Super Admin",
    "Admin",
    "Product Manager",
    "Inventory Manager",
    "Order Manager",
    "Support Agent",
    "Customer",
    "Delivery Manager",
    "Finance Manager",
}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    token = credentials.credentials

    try:
        payload = decode_token(token)

        user_id = int(payload["sub"])
        jti = payload["jti"]

        if payload.get("type") != "access":
            raise ValueError("Invalid token type")

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token"
        )

    session = db.query(TokenSession).filter(
        TokenSession.jti == jti,
        TokenSession.user_id == user_id,
        TokenSession.token_type == "access"
    ).first()

    if not session or session.revoked:
        raise HTTPException(
            status_code=401,
            detail="Invalid or revoked access token"
        )

    now = datetime.now(timezone.utc)

    expires_at = session.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= now:
        raise HTTPException(
            status_code=401,
            detail="Access token expired"
        )

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="Inactive or missing user"
        )

    return user


def require_roles(*roles):
    def role_checker(
        current_user: User = Depends(get_current_user)
    ):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission"
            )

        return current_user

    return role_checker
