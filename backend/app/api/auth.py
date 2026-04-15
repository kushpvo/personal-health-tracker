from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    hash_token,
    verify_password,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from app.db.database import get_db
from app.db.models import RefreshToken, User
from app.schemas.schemas import (
    ChangePasswordInput,
    LoginInput,
    SetupInput,
    TokenResponse,
    UpdateProfileInput,
    UserInfo,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"


def _issue_tokens(user: User, db: Session, response: Response) -> TokenResponse:
    raw_refresh = create_refresh_token()
    hashed = hash_token(raw_refresh)
    expires = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(RefreshToken(user_id=user.id, token_hash=hashed, expires_at=expires))
    db.commit()

    response.set_cookie(
        key=REFRESH_COOKIE,
        value=raw_refresh,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/auth",
    )
    return TokenResponse(access_token=create_access_token(user.id, user.role))


@router.get("/setup-required")
def setup_required(db: Session = Depends(get_db)):
    return {"required": db.query(User).count() == 0}


@router.post("/setup", response_model=TokenResponse)
def setup(body: SetupInput, response: Response, db: Session = Depends(get_db)):
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
    return _issue_tokens(user, db, response)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginInput, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    return _issue_tokens(user, db, response)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: Optional[str] = Cookie(default=None, alias=REFRESH_COOKIE),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    hashed = hash_token(refresh_token)
    record = db.query(RefreshToken).filter(
        RefreshToken.token_hash == hashed,
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.now(timezone.utc),
    ).first()
    if not record:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = db.query(User).filter(User.id == record.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    record.revoked = True
    db.commit()
    return _issue_tokens(user, db, response)


@router.post("/logout")
def logout(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: Optional[str] = Cookie(default=None, alias=REFRESH_COOKIE),
):
    if refresh_token:
        hashed = hash_token(refresh_token)
        record = db.query(RefreshToken).filter(RefreshToken.token_hash == hashed).first()
        if record:
            record.revoked = True
            db.commit()
    response.delete_cookie(key=REFRESH_COOKIE, path="/api/auth")
    return {"ok": True}


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


@router.patch("/me/profile", response_model=UserInfo)
def update_profile(
    body: UpdateProfileInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    VALID_SEX = {"male", "female", "other", None}
    if body.sex not in VALID_SEX:
        raise HTTPException(status_code=422, detail="sex must be 'male', 'female', 'other', or null")
    current_user.sex = body.sex
    db.commit()
    db.refresh(current_user)
    return current_user
