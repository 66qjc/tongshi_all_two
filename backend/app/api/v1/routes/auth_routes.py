"""Auth routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user, verify_password, get_password_hash
from app.core.response import success
from app.core.exceptions import BusinessException
from app.schemas.common import AuthUser, LoginRequest, RegisterRequest, ChangePasswordRequest, ForgotPasswordRequest
from app.services.auth_service import login_user, register_user, forgot_password as forgot_password_svc
from app.models.entities import User

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


@router.put("/change-password", summary="修改密码", description="任何已登录用户可用，首次登录教师必须调用")
def change_password(
    req: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """修改密码（任何已登录用户可用，首次登录教师必须调用）"""
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise BusinessException(404, "用户不存在")
    if not verify_password(req.old_password, user.hashed_password):
        raise BusinessException(400, "旧密码不正确")
    # 新密码复杂度已在 Schema 层校验
    user.hashed_password = get_password_hash(req.new_password)
    user.needs_password_change = False
    db.commit()
    return success({"message": "密码修改成功"})


@router.post("/password/forgot", summary="忘记密码（直接重置）")
def forgot_password_route(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """忘记密码：无需登录，直接用学号/工号重置密码"""
    return success(forgot_password_svc(db, data.id, data.new_password))
