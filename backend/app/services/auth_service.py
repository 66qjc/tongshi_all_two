"""Auth service: login and register"""
import logging
import random
import string
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.exceptions import BusinessException
from app.models.entities import User, SecurityQuestion, PasswordResetRequest
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
    allowed_roles = {"student"}
    if data.role not in allowed_roles:
        raise BusinessException(400, "注册角色不合法")
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


# ── 密保问题管理 ────────────────────────────────────────────────────────────

def get_security_questions(db: Session, user_id: str) -> list[dict]:
    """获取当前用户的密保问题列表（只返回 id 和 question，不含答案）"""
    questions = db.query(SecurityQuestion).filter(
        SecurityQuestion.user_id == user_id
    ).order_by(SecurityQuestion.id).all()
    return [{"id": q.id, "question": q.question} for q in questions]


def update_security_questions(db: Session, user_id: str, questions: list[dict]) -> list[dict]:
    """整体替换用户的密保问题（最多 3 个）"""
    if len(questions) > 3:
        raise BusinessException(400, "密保问题最多 3 个")
    # 删除旧问题
    db.query(SecurityQuestion).filter(SecurityQuestion.user_id == user_id).delete()
    # 插入新问题
    for item in questions:
        q = SecurityQuestion(
            user_id=user_id,
            question=item["question"],
            answer_hash=get_password_hash(item["answer"]),
        )
        db.add(q)
    db.commit()
    return get_security_questions(db, user_id)


# ── 忘记密码流程 ──────────────────────────────────────────────────────────

# 内存计数：{user_id: [(attempt_time, ...), ...]}，5 分钟内最多 5 次错误
_FORGOT_FAILURES: dict[str, list[datetime]] = {}

_MAX_ATTEMPTS = 5
_ATTEMPT_WINDOW_MINUTES = 5
_CLEANUP_INTERVAL_MINUTES = 10
_LAST_FORGOT_FAILURE_CLEANUP: datetime | None = None


def _cleanup_forgot_failures(now: datetime | None = None) -> None:
    """清理所有已过期的忘记密码失败记录，避免长时间运行时字典膨胀。"""
    current = now or datetime.now(timezone.utc)
    cutoff = current - timedelta(minutes=_ATTEMPT_WINDOW_MINUTES)
    expired_users = []
    for user_id, attempts in list(_FORGOT_FAILURES.items()):
        active_attempts = [attempt for attempt in attempts if attempt > cutoff]
        if active_attempts:
            _FORGOT_FAILURES[user_id] = active_attempts
        else:
            expired_users.append(user_id)
    for user_id in expired_users:
        _FORGOT_FAILURES.pop(user_id, None)


def _check_and_record_failure(user_id: str) -> int:
    """检查并记录一次失败尝试，返回剩余尝试次数；-1 表示已锁定"""
    global _LAST_FORGOT_FAILURE_CLEANUP
    now = datetime.now(timezone.utc)
    if (
        _LAST_FORGOT_FAILURE_CLEANUP is None
        or now - _LAST_FORGOT_FAILURE_CLEANUP > timedelta(minutes=_CLEANUP_INTERVAL_MINUTES)
    ):
        _cleanup_forgot_failures(now)
        _LAST_FORGOT_FAILURE_CLEANUP = now
    cutoff = now - timedelta(minutes=_ATTEMPT_WINDOW_MINUTES)
    # 清理过期记录
    attempts = [t for t in _FORGOT_FAILURES.get(user_id, []) if t > cutoff]
    if len(attempts) >= _MAX_ATTEMPTS:
        _FORGOT_FAILURES[user_id] = attempts
        return -1
    attempts.append(now)
    _FORGOT_FAILURES[user_id] = attempts
    return _MAX_ATTEMPTS - len(attempts)


def _clear_failures(user_id: str) -> None:
    _FORGOT_FAILURES.pop(user_id, None)


def get_forgot_password_questions(db: Session, user_id: str) -> list[dict]:
    """获取指定用户的密保问题列表（用于忘记密码页，仅返回问题文本，不验证身份）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(404, "学号不存在")
    return get_security_questions(db, user_id)


def verify_answers_and_reset_password(db: Session, user_id: str, answers: list[dict], new_password: str) -> dict:
    """验证密保答案并重置密码"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(404, "学号不存在")

    questions = db.query(SecurityQuestion).filter(
        SecurityQuestion.user_id == user_id
    ).all()
    if not questions:
        raise BusinessException(400, "未设置密保问题，请申请人工重置")

    # 构建 id → question 映射
    q_map = {q.id: q for q in questions}

    # 检查答案数量
    if len(answers) != len(questions):
        raise BusinessException(400, f"需要回答全部 {len(questions)} 个密保问题")

    # 检查失败次数是否超限
    remaining = _check_and_record_failure(user_id)  # 先记一次，验证通过再清除
    if remaining == -1:
        raise BusinessException(429, f"验证次数超限，请等待 {_ATTEMPT_WINDOW_MINUTES} 分钟后重试，或申请人工重置")

    # 验证每个答案
    errors = []
    for ans in answers:
        qid = ans.get("question_id")
        q = q_map.get(qid)
        if not q:
            errors.append(f"问题 {qid} 不存在")
            continue
        if not verify_password(ans.get("answer", ""), q.answer_hash):
            errors.append(f"问题「{q.question}」答案错误")

    if errors:
        # 验证失败，剩余次数
        if remaining == 0:
            raise BusinessException(429, f"验证次数超限，请等待 {_ATTEMPT_WINDOW_MINUTES} 分钟后重试，或申请人工重置")
        raise BusinessException(400, f"{'；'.join(errors)}（剩余 {remaining} 次尝试）")

    # 全部通过，清除失败计数，重置密码
    _clear_failures(user_id)
    user.hashed_password = get_password_hash(new_password)
    user.needs_password_change = False
    db.commit()
    logger.info(f"密保验证通过，密码已重置: user_id={user_id}")
    return {"message": "密码重置成功"}


def submit_reset_request(db: Session, user_id: str, message: str) -> dict:
    """提交人工密码重置申请"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(404, "学号不存在")

    # 检查是否有 pending 请求
    existing = db.query(PasswordResetRequest).filter(
        PasswordResetRequest.user_id == user_id,
        PasswordResetRequest.status == "pending",
    ).first()
    if existing:
        raise BusinessException(400, "已有待处理的密码重置申请，请耐心等待")

    req = PasswordResetRequest(user_id=user_id, message=message)
    db.add(req)
    db.commit()
    logger.info(f"密码重置申请已提交: user_id={user_id}")
    return {"message": "申请已提交，请等待教师或管理员审核"}


# ── 审批管理 ─────────────────────────────────────────────────────────────

def _generate_temp_password() -> str:
    """生成随机 8 位临时密码（包含大小写字母和数字）"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=8))


def get_reset_requests_for_teacher(db: Session, teacher_id: str, status: str | None = None) -> list[dict]:
    """获取教师的密码重置请求（仅本班学生），支持状态筛选"""
    from app.models.entities import StudentClassEnrollment, Class
    class_ids = [row[0] for row in db.query(Class.id).filter(
        Class.created_by == teacher_id
    ).all()]
    if not class_ids:
        return []
    student_ids = [row[0] for row in db.query(StudentClassEnrollment.user_id).filter(
        StudentClassEnrollment.class_id.in_(class_ids)
    ).all()]
    if not student_ids:
        return []
    q = db.query(PasswordResetRequest).filter(
        PasswordResetRequest.user_id.in_(student_ids),
    )
    if status:
        q = q.filter(PasswordResetRequest.status == status)
    requests = q.order_by(PasswordResetRequest.created_at.desc()).all()
    return [_reset_request_out(db, r) for r in requests]


def get_reset_requests_for_admin(db: Session, status: str | None = None) -> list[dict]:
    """获取所有密码重置请求（管理员），支持状态筛选"""
    q = db.query(PasswordResetRequest)
    if status:
        q = q.filter(PasswordResetRequest.status == status)
    requests = q.order_by(PasswordResetRequest.created_at.desc()).all()
    return [_reset_request_out(db, r) for r in requests]


def _teacher_can_resolve_reset_request(db: Session, teacher_id: str, request_id: int) -> PasswordResetRequest | None:
    """返回当前教师班级内的密码重置申请；不在范围内时返回 None。"""
    from app.models.entities import Class, StudentClassEnrollment

    return (
        db.query(PasswordResetRequest)
        .join(StudentClassEnrollment, StudentClassEnrollment.user_id == PasswordResetRequest.user_id)
        .join(Class, Class.id == StudentClassEnrollment.class_id)
        .filter(
            PasswordResetRequest.id == request_id,
            Class.created_by == teacher_id,
        )
        .first()
    )


def approve_reset_request(db: Session, request_id: int, resolver_id: str) -> dict:
    """审批通过密码重置请求"""
    req = db.query(PasswordResetRequest).filter(
        PasswordResetRequest.id == request_id
    ).first()
    if not req:
        raise BusinessException(404, "申请不存在")
    if req.status != "pending":
        raise BusinessException(400, "该申请已被处理")

    new_pwd = _generate_temp_password()
    user = db.query(User).filter(User.id == req.user_id).first()
    if user:
        user.hashed_password = get_password_hash(new_pwd)
        user.needs_password_change = True

    req.status = "approved"
    req.resolved_by = resolver_id
    req.new_password_hash = get_password_hash(new_pwd)
    req.temp_password = new_pwd  # 存储临时密码明文，供后续查看
    req.resolved_at = datetime.now(timezone.utc)
    db.commit()
    logger.info(f"密码重置申请已审批: request_id={request_id}, resolver={resolver_id}")
    return {"message": "密码已重置", "temp_password": new_pwd}


def approve_reset_request_for_teacher(db: Session, request_id: int, teacher_id: str) -> dict:
    """教师审批密码重置前先校验申请人是否属于自己的班级。"""
    req = _teacher_can_resolve_reset_request(db, teacher_id, request_id)
    if not req:
        raise BusinessException(404, "申请不存在")
    return approve_reset_request(db, request_id, teacher_id)


def reject_reset_request(db: Session, request_id: int, resolver_id: str, reason: str) -> dict:
    """驳回密码重置请求"""
    req = db.query(PasswordResetRequest).filter(
        PasswordResetRequest.id == request_id
    ).first()
    if not req:
        raise BusinessException(404, "申请不存在")
    if req.status != "pending":
        raise BusinessException(400, "该申请已被处理")

    req.status = "rejected"
    req.resolved_by = resolver_id
    req.resolved_at = datetime.now(timezone.utc)
    db.commit()
    logger.info(f"密码重置申请已驳回: request_id={request_id}, resolver={resolver_id}, reason={reason}")
    return {"message": "已驳回"}


def reject_reset_request_for_teacher(db: Session, request_id: int, teacher_id: str, reason: str) -> dict:
    """教师驳回密码重置前先校验申请人是否属于自己的班级。"""
    req = _teacher_can_resolve_reset_request(db, teacher_id, request_id)
    if not req:
        raise BusinessException(404, "申请不存在")
    return reject_reset_request(db, request_id, teacher_id, reason)


def _reset_request_out(db: Session, req: PasswordResetRequest) -> dict:
    user = db.query(User).filter(User.id == req.user_id).first()
    resolver_name = ""
    if req.resolved_by:
        resolver = db.query(User).filter(User.id == req.resolved_by).first()
        resolver_name = resolver.name if resolver else ""
    return {
        "id": req.id,
        "user_id": req.user_id,
        "user_name": user.name if user else "",
        "message": req.message,
        "status": req.status,
        "resolved_by": req.resolved_by,
        "resolved_by_name": resolver_name,
        "temp_password": "",
        "resolved_at": req.resolved_at.isoformat() if req.resolved_at else "",
        "created_at": req.created_at.isoformat() if req.created_at else "",
    }
