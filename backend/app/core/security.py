"""JWT authentication and password utilities"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BusinessException
from app.db.session import get_db
from app.models.entities import User
from app.schemas.common import AuthUser

pwd_context = CryptContext(
    schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token", auto_error=False)


def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(
        timezone.utc) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


async def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> AuthUser:
    # 回退：Authorization header 无 token 时，从 ?token= query 参数读取
    # 支持 <a> / <iframe> / <img> 等无法携带自定义请求头的场景
    if not token:
        allow_query = settings.allow_query_token_for_files and (
            request.url.path.startswith("/api/files/")
            or (
                request.url.path.startswith("/api/materials/")
                and request.url.path.endswith("/file")
            )
        )
        if allow_query:
            token = request.query_params.get("token")
    if not token:
        raise BusinessException(401, "无效的认证凭据")
    try:
        payload = jwt.decode(token, settings.secret_key,
                             algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        if not user_id:
            raise BusinessException(401, "无效的认证凭据")
    except JWTError:
        raise BusinessException(401, "无效的认证凭据")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(401, "无效的认证凭据")
    return AuthUser(
        id=user.id,
        name=user.name,
        role=user.role,
        major=user.major,
        needs_password_change=user.needs_password_change,
    )


def require_role(role: str):
    """Dependency factory that checks current user has the required role."""
    async def _check(current_user: AuthUser = Depends(get_current_user)):
        if current_user.role != role:
            raise BusinessException(403, f"需要{role}权限")
        return current_user
    return _check


def require_roles(*roles: str):
    """Dependency factory that checks current user has one of the required roles."""
    async def _check(current_user: AuthUser = Depends(get_current_user)):
        if current_user.role not in roles:
            raise BusinessException(403, f"需要{'/'.join(roles)}权限")
        return current_user
    return _check
