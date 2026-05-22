from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from . import models, schemas, database
from .config import settings
from .models import UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

SECRET_KEY                 = settings.secret_key
ALGORITHM                  = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes


# ─────────────────────────────────────────
# Token helpers
# ─────────────────────────────────────────

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire    = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_access_token(token: str,
                         credentials_exception: HTTPException
                         ) -> schemas.TokenData:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        return schemas.TokenData(id=user_id)
    except JWTError:
        raise credentials_exception


# ─────────────────────────────────────────
# Base dependency — any logged-in user
# ─────────────────────────────────────────

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(database.get_db),
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = verify_access_token(token, credentials_exception)
    user = db.query(models.User).filter(
        models.User.id == token_data.id
    ).first()
    if user is None:
        raise credentials_exception
    return user


# ─────────────────────────────────────────
# Role-based dependencies
# ─────────────────────────────────────────

def require_role(role: UserRole):
    """
    Factory that returns a FastAPI dependency enforcing a specific role.
    Usage:
        current_user = Depends(require_company)
        current_user = Depends(require_candidate)
    """
    def checker(
        current_user: models.User = Depends(get_current_user),
    ) -> models.User:
        if current_user.role != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Only {role.value}s can perform this action.",
            )
        return current_user
    return checker


require_company   = require_role(UserRole.company)
require_candidate = require_role(UserRole.candidate)