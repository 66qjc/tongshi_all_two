"""管理员路由 - 教师账号管理"""
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
import io

from app.db.session import get_db
from app.core.security import require_role, get_password_hash
from app.core.response import success
from app.core.exceptions import BusinessException
from app.models.entities import User
from app.schemas.common import AuthUser, CreateTeacherRequest, TeacherInfo

router = APIRouter()

DEFAULT_PASSWORD = "123456"


def _build_teacher_info(user: User) -> dict:
    """构建教师信息字典"""
    return {
        "id": user.id,
        "name": user.name,
        "major": user.major or "",
        "created_at": user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else "",
        "needs_password_change": user.needs_password_change,
    }


@router.get("/teachers", summary="获取教师列表", description="管理员：获取所有教师账号列表")
def list_teachers(
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_role("admin")),
):
    """获取所有教师列表"""
    teachers = db.query(User).filter(User.role == "teacher").all()
    return success([_build_teacher_info(t) for t in teachers])


@router.post("/teachers", summary="创建教师账号", description="管理员：手动创建单个教师账号，默认密码 123456，首次登录需改密")
def create_teacher(
    req: CreateTeacherRequest,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_role("admin")),
):
    """手动创建单个教师账号，默认密码 123456，首次登录需改密"""
    existing = db.query(User).filter(User.id == req.id).first()
    if existing:
        raise BusinessException(400, f"工号 {req.id} 已存在")
    new_teacher = User(
        id=req.id,
        name=req.name,
        major=req.major or "",
        role="teacher",
        hashed_password=get_password_hash(DEFAULT_PASSWORD),
        needs_password_change=True,
    )
    db.add(new_teacher)
    db.commit()
    db.refresh(new_teacher)
    return success(_build_teacher_info(new_teacher))


@router.post("/teachers/import", summary="批量导入教师", description="管理员：通过 Excel 批量导入教师账号（第一列=姓名，第二列=工号，第一行为表头）")
async def import_teachers(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_role("admin")),
):
    """通过 Excel 批量导入教师账号（第一列=姓名，第二列=工号，第一行为表头）"""
    try:
        import openpyxl
    except ImportError:
        raise BusinessException(500, "服务器缺少 openpyxl 依赖，请联系管理员")

    if not file.filename or not file.filename.endswith(".xlsx"):
        raise BusinessException(400, "请上传 .xlsx 格式的 Excel 文件")

    content = await file.read()
    try:
        wb = openpyxl.load_workbook(io.BytesIO(content))
        ws = wb.active
    except Exception:
        raise BusinessException(400, "Excel 文件格式错误，无法解析")

    created_list = []
    skipped_list = []

    rows = list(ws.iter_rows(min_row=2, values_only=True))  # 跳过表头
    for row in rows:
        if not row or len(row) < 2:
            continue
        name = str(row[0]).strip() if row[0] is not None else ""
        teacher_id = str(row[1]).strip() if row[1] is not None else ""
        if not name or not teacher_id:
            continue
        existing = db.query(User).filter(User.id == teacher_id).first()
        if existing:
            skipped_list.append(teacher_id)
            continue
        new_teacher = User(
            id=teacher_id,
            name=name,
            major="",
            role="teacher",
            hashed_password=get_password_hash(DEFAULT_PASSWORD),
            needs_password_change=True,
        )
        db.add(new_teacher)
        created_list.append(teacher_id)

    db.commit()

    return success({
        "created_count": len(created_list),
        "skipped_count": len(skipped_list),
        "created": created_list,
        "skipped": skipped_list,
        "message": f"成功导入 {len(created_list)} 个教师账号，跳过 {len(skipped_list)} 个（工号已存在）",
    })


@router.post("/teachers/{teacher_id}/reset-password", summary="重置教师密码", description="管理员：将教师密码重置为 123456 并标记需要重新修改密码")
def reset_teacher_password(
    teacher_id: str,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_role("admin")),
):
    """重置教师密码为 123456，并标记需要重新修改密码"""
    teacher = db.query(User).filter(User.id == teacher_id,
                                    User.role == "teacher").first()
    if not teacher:
        raise BusinessException(404, "教师不存在")
    teacher.hashed_password = get_password_hash(DEFAULT_PASSWORD)
    teacher.needs_password_change = True
    db.commit()
    return success({"message": "密码已重置为 123456，教师下次登录需修改密码"})


@router.delete("/teachers/{teacher_id}", summary="删除教师账号", description="管理员：删除指定教师账号")
def delete_teacher(
    teacher_id: str,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_role("admin")),
):
    """删除教师账号"""
    teacher = db.query(User).filter(User.id == teacher_id,
                                    User.role == "teacher").first()
    if not teacher:
        raise BusinessException(404, "教师不存在")
    db.delete(teacher)
    db.commit()
    return success({"message": "删除成功"})
