"""
Auth API:
  POST /auth/register  - Đăng ký tài khoản mới
  POST /auth/login     - Đăng nhập, trả về JWT access token
  GET  /auth/me        - Thông tin user hiện tại (cần token)
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db, User

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Auth"])

# ─── Crypto ──────────────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 ngày


def _hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.API_SECRET_KEY, algorithm="HS256")


# ─── Schemas ─────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("username phải có ít nhất 3 ký tự")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("password phải có ít nhất 6 ký tự")
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    is_admin: bool
    role: Optional[str] = "van_phong"
    created_at: Optional[datetime]


# ─── Helpers ─────────────────────────────────────────────────────────────────
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token không hợp lệ hoặc đã hết hạn",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.API_SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise credentials_exc
    return user


def _role_of(user: User) -> str:
    return getattr(user, "role", None) or ("admin" if user.is_admin else "van_phong")


def require_roles(*allowed: str):
    """Dependency factory: chỉ role trong danh sách (admin luôn được qua)."""
    async def _check(current: User = Depends(get_current_user)) -> User:
        role = _role_of(current)
        if role != "admin" and role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' không có quyền. Cần: {', '.join(allowed)}",
            )
        return current
    return _check


# ─── Endpoints ───────────────────────────────────────────────────────────────
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Đăng ký tài khoản mới."""
    # Kiểm tra email / username đã tồn tại
    existing = await db.execute(
        select(User).where(
            (User.email == payload.email) | (User.username == payload.username)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email hoặc username đã được sử dụng")

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=_hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return _to_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Đăng nhập bằng username hoặc email + password. Trả về JWT token."""
    # Tìm bằng username hoặc email
    result = await db.execute(
        select(User).where(
            (User.username == form.username) | (User.email == form.username)
        )
    )
    user = result.scalar_one_or_none()

    if not user or not _verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai username/email hoặc mật khẩu",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Tài khoản đã bị vô hiệu hóa")

    token = _create_access_token({"sub": user.id, "username": user.username})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    """Thông tin user hiện tại (yêu cầu Bearer token)."""
    return _to_response(current_user)


# ─── Helper ──────────────────────────────────────────────────────────────────
def _to_response(u: User) -> UserResponse:
    return UserResponse(
        id=u.id,
        email=u.email,
        username=u.username,
        full_name=u.full_name,
        is_active=u.is_active,
        is_admin=u.is_admin,
        role=getattr(u, "role", None) or ("admin" if u.is_admin else "van_phong"),
        created_at=u.created_at,
    )
