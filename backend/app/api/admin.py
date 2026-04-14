from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import create_access_token, get_admin_user, hash_password
from app.db.database import get_db
from app.db.models import User
from app.schemas.schemas import (
    CreateUserInput,
    TokenResponse,
    UpdateUserInput,
    UserInfo,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[UserInfo])
def list_users(db: Session = Depends(get_db), _: User = Depends(get_admin_user)):
    return db.query(User).order_by(User.created_at.asc()).all()


@router.post("/users", response_model=UserInfo, status_code=201)
def create_user(
    body: CreateUserInput,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    if body.role not in ("admin", "user"):
        raise HTTPException(status_code=422, detail="role must be 'admin' or 'user'")
    if len(body.password) < 8:
        raise HTTPException(
            status_code=422,
            detail="Password must be at least 8 characters",
        )
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=409, detail="Username already exists")
    user = User(
        username=body.username,
        hashed_password=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserInfo)
def update_user(
    user_id: int,
    body: UpdateUserInput,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.is_active is not None:
        if user.id == admin.id and not body.is_active:
            raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
        user.is_active = body.is_active
    if body.password is not None:
        if len(body.password) < 8:
            raise HTTPException(
                status_code=422,
                detail="Password must be at least 8 characters",
            )
        user.hashed_password = hash_password(body.password)
    db.commit()
    db.refresh(user)
    return user


@router.post("/impersonate/{user_id}", response_model=TokenResponse)
def impersonate(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot impersonate yourself")
    token = create_access_token(
        admin.id,
        admin.role,
        acting_as=target.id,
        expire_hours=8,
    )
    return TokenResponse(access_token=token)
