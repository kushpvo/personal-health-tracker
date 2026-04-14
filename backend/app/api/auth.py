from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.db.database import get_db
from app.db.models import User
from app.schemas.schemas import (
    ChangePasswordInput,
    LoginInput,
    SetupInput,
    TokenResponse,
    UserInfo,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/setup-required")
def setup_required(db: Session = Depends(get_db)):
    return {"required": db.query(User).count() == 0}


@router.post("/setup", response_model=TokenResponse)
def setup(body: SetupInput, db: Session = Depends(get_db)):
    if db.query(User).count() > 0:
        raise HTTPException(status_code=403, detail="Setup already complete")
    if len(body.password) < 8:
        raise HTTPException(
            status_code=422,
            detail="Password must be at least 8 characters",
        )
    user = User(
        username=body.username,
        hashed_password=hash_password(body.password),
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id, user.role))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginInput, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    return TokenResponse(access_token=create_access_token(user.id, user.role))


@router.get("/me", response_model=UserInfo)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me/password")
def change_password(
    body: ChangePasswordInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(
            status_code=422,
            detail="Password must be at least 8 characters",
        )
    current_user.hashed_password = hash_password(body.new_password)
    db.commit()
    return {"ok": True}
