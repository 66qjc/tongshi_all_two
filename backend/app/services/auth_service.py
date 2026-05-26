"""Auth service: login and register"""
import logging
from datetime import timedelta

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.exceptions import BusinessException
from app.models.entities import User
from app.schemas.common import RegisterRequest

logger = logging.getLogger(__name__)


def login_user(db: Session, user_id: str, password: str) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not verify_password(password, user.hashed_password):
        logger.warning(f"登录失败: user_id={user_id}")
        raise BusinessException(401, "学号或密码错误")
    logger.info(f"用户登录: user_id={user_id}, role={user.role}")
    token = create_access_token(
        {"sub": user.id},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "name": user.name, "role": user.role, "major": user.major, "needs_password_change": user.needs_password_change},
    }


def register_user(db: Session, data: RegisterRequest) -> dict:
    existing = db.query(User).filter(User.id == data.id).first()
    if existing:
        raise BusinessException(400, "该学号已注册")
    user = User(
        id=data.id,
        name=data.name,
        hashed_password=get_password_hash(data.password),
        role=data.role,
        major=data.major or "",
    )
    try:
        db.add(user)
        db.commit()
        logger.info(f"用户注册成功: user_id={user.id}, role={user.role}")
    except IntegrityError:
        db.rollback()
        raise BusinessException(400, "该学号已注册")
    except SQLAlchemyError:
        db.rollback()
        raise BusinessException(500, "注册失败，请稍后重试")
    return {"success": True, "message": "注册成功"}


def forgot_password(db: Session, user_id: str, new_password: str) -> dict:
    """忘记密码：直接用学号/工号重置密码，无需旧密码"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(404, "学号不存在")
    user.hashed_password = get_password_hash(new_password)
    user.needs_password_change = False
    db.commit()
    logger.info(f"密码重置成功: user_id={user_id}")
    return {"message": "密码重置成功"}
