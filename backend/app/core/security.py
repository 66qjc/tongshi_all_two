"""JWT authentication and password utilities"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends
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
FILE_ACCESS_TOKEN_EXPIRE_SECONDS = 300
INVALID_AUTH_MESSAGE = "无效的认证凭据"
INVALID_FILE_ACCESS_MESSAGE = "文件访问凭据无效或已过期"


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
    # token_version 由调用方从 user.token_version 传入，默认为 0
    # 写入 payload 后，get_current_user 在校验时对比数据库值，改密后旧 token 立即失效
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_file_access_token(
    user_id: str,
    file_id: int,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """签发仅可访问单个文件的短时凭据。"""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(seconds=FILE_ACCESS_TOKEN_EXPIRE_SECONDS)
    )
    return jwt.encode(
        {
            "sub": user_id,
            "scope": "file_access",
            "file_id": file_id,
            "exp": expire,
        },
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def decode_file_access_token(token: str, expected_file_id: int) -> str:
    """解析并严格校验单文件短时凭据，成功时返回用户 ID。"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload["sub"]
        scope = payload["scope"]
        file_id = payload["file_id"]
        expires_at = payload["exp"]
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("invalid sub")
        if scope != "file_access":
            raise ValueError("invalid scope")
        if type(file_id) is not int or file_id != expected_file_id:
            raise ValueError("invalid file_id")
        if type(expires_at) is not int or expires_at <= datetime.now(timezone.utc).timestamp():
            raise ValueError("invalid exp")
        return user_id
    except (JWTError, KeyError, TypeError, ValueError):
        raise BusinessException(401, INVALID_FILE_ACCESS_MESSAGE)


def authenticate_bearer_token(token: str, db: Session) -> AuthUser:
    """完整校验普通登录 Bearer Token 并返回真实用户。"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload["sub"]
        if not isinstance(user_id, str) or not user_id:
            raise ValueError("invalid sub")
        if payload.get("scope") not in (None, ""):
            raise ValueError("scoped token is not a login token")
    except (JWTError, KeyError, TypeError, ValueError):
        raise BusinessException(401, INVALID_AUTH_MESSAGE)

    user = db.query(User).filter(
        User.id == user_id,
        User.deleted_at.is_(None),
    ).first()
    if not user:
        raise BusinessException(401, INVALID_AUTH_MESSAGE)
    # 校验 token_version：修改密码后旧 token 立即失效
    token_version = payload.get("token_version", 0)
    if token_version != (user.token_version or 0):
        raise BusinessException(401, "登录状态已失效，请重新登录")
    return AuthUser(
        id=user.id,
        name=user.name,
        role=user.role,
        major=user.major,
        needs_password_change=user.needs_password_change,
    )


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> AuthUser:
    if not token:
        raise BusinessException(401, INVALID_AUTH_MESSAGE)
    return authenticate_bearer_token(token, db)


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
