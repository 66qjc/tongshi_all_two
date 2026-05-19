"""Auth routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.response import success
from app.schemas.common import AuthUser, LoginRequest, RegisterRequest
from app.services.auth_service import login_user, register_user

router = APIRouter(tags=["auth"])


@router.post("/token", summary="用户登录", description="使用学号/工号和密码登录，返回 JWT access_token")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    return success(login_user(db, data.id, data.password))


@router.post("/register", summary="用户注册", description="注册新用户，密码需包含字母和数字")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    return success(register_user(db, data))


@router.get("/me", summary="获取当前用户", description="根据 JWT token 返回当前登录用户信息")
def get_me(current_user: AuthUser = Depends(get_current_user)):
    return success(current_user.model_dump())
