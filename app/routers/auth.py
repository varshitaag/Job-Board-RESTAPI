from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas, utils, oauth2
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.UserOut,
    summary="Register as a company or candidate",
)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user account.

    - **role** must be either `company` or `candidate`
    - After registering, create your profile:
      - Companies  → `POST /company/profile`
      - Candidates → `POST /candidate/profile`
    """
    existing = db.query(models.User).filter(
        models.User.email == user.email
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    new_user          = models.User(**user.dict())
    new_user.password = utils.hash(user.password)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post(
    "/login",
    response_model=schemas.Token,
    summary="Login and receive a JWT token",
)
def login(
    credentials: schemas.UserLogin,
    db: Session = Depends(get_db),
):
    """
    Authenticate with email and password.
    Returns a **Bearer token** — attach it to all subsequent requests via:

        Authorization: Bearer <token>
    """
    user = db.query(models.User).filter(
        models.User.email == credentials.email
    ).first()

    if not user or not utils.verify(credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    token = oauth2.create_access_token(data={"user_id": user.id})
    return {"access_token": token, "token_type": "bearer"}