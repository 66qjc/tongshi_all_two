"""Auth routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.response import success
from app.schemas.common import (
    AuthUser, LoginRequest, ChangePasswordRequest,
    ForgotPasswordCheckRequest,
    ForgotPasswordManualRequest, SecurityQuestionsUpdate,
)
from app.services.auth_service import (
    login_user,
    change_user_password,
    get_security_questions, update_security_questions,
    get_forgot_password_questions, verify_answers_and_reset_password,
    submit_reset_request,
)

router = APIRouter(tags=["auth"])


@router.post("/token", summary="用户登录", description="使用学号/工号和密码登录，返回 JWT access_token")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    return success(login_user(db, data.id, data.password))


@router.get("/me", summary="获取当前用户", description="根据 JWT token 返回当前登录用户信息")
def get_me(current_user: AuthUser = Depends(get_current_user)):
    return success(current_user.model_dump())


@router.put("/change-password", summary="修改密码", description="任何已登录用户可用，首次登录教师必须调用")
def change_password(
    req: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    return success(change_user_password(
        db,
        current_user.id,
        req.old_password,
        req.new_password,
    ))


# ── 密保问题管理（需登录）───────────────────────────────────────────────

@router.get("/security-questions", summary="获取密保问题", description="返回当前用户设置的密保问题（只返回问题文本，不含答案）")
def list_security_questions(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    return success(get_security_questions(db, current_user.id))


@router.put("/security-questions", summary="设置密保问题", description="整体替换密保问题，最多 3 个，传空列表表示清空")
def set_security_questions(
    data: SecurityQuestionsUpdate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    items = [{"question": q.question, "answer": q.answer} for q in data.questions]
    return success(update_security_questions(db, current_user.id, items))


# ── 忘记密码流程（无需登录）─────────────────────────────────────────────

@router.get("/password/forgot/questions", summary="忘记密码—获取密保问题", description="根据学号获取该用户的密保问题（仅返回问题文本）")
def forgot_password_questions(user_id: str, db: Session = Depends(get_db)):
    return success(get_forgot_password_questions(db, user_id))


@router.post("/password/forgot/reset", summary="忘记密码—验证答案并重置", description="回答密保问题后重置密码")
def forgot_password_reset(data: ForgotPasswordCheckRequest, db: Session = Depends(get_db)):
    return success(verify_answers_and_reset_password(
        db, data.user_id, data.answers, data.new_password
    ))


@router.post("/password/forgot/request", summary="忘记密码—提交人工重置申请", description="未设置密保或无法回答时，提交留言申请人工重置")
def forgot_password_request(data: ForgotPasswordManualRequest, db: Session = Depends(get_db)):
    return success(submit_reset_request(db, data.user_id, data.message))

