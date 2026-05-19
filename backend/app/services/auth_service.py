"""Auth service: login and register"""
from datetime import timedelta

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.exceptions import BusinessException
from app.models.entities import User
from app.schemas.common import RegisterRequest


def login_user(db: Session, user_id: str, password: str) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not verify_password(password, user.hashed_password):
        raise BusinessException(401, "学号或密码错误")
    token = create_access_token(
        {"sub": user.id},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "name": user.name, "role": user.role, "major": user.major},
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
    except IntegrityError:
        db.rollback()
        raise BusinessException(400, "该学号已注册")
    except SQLAlchemyError:
        db.rollback()
        raise BusinessException(500, "注册失败，请稍后重试")
    return {"success": True, "message": "注册成功"}
