"""Auth routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.response import success
from app.schemas.common import AuthUser, LoginRequest, RegisterRequest
from app.services.auth_service import login_user, register_user

router = APIRouter(tags=["auth"])


@router.post("/token")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    return success(login_user(db, data.id, data.password))


@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    return success(register_user(db, data))


@router.get("/me")
def get_me(current_user: AuthUser = Depends(get_current_user)):
    return success(current_user.model_dump())
