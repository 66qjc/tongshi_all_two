"""阶段/目录路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import require_role
from app.core.response import success
from app.core.exceptions import BusinessException
from app.schemas.common import AuthUser, CourseStageUpdate
from app.services.course_stage_service import update_stage, delete_stage, format_stage_out

router = APIRouter(prefix="/stages", tags=["stages"])


@router.put("/{stage_id}", summary="更新阶段", description="教师端：修改阶段名称或排序")
def edit_stage(
    stage_id: int,
    data: CourseStageUpdate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("teacher")),
):
    name = data.name.strip() if data.name is not None else None
    stage = update_stage(db, stage_id, name, data.sort_order, current_user.id)
    if not stage:
        raise BusinessException(404, "阶段不存在")
    db.commit()
    return success(format_stage_out(stage))


@router.delete(
    "/{stage_id}",
    summary="删除阶段",
    description="教师端：删除阶段；cascade_materials=true 时级联软删阶段下活跃资料",
)
def remove_stage(
    stage_id: int,
    cascade_materials: bool = False,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_role("teacher")),
):
    if not delete_stage(
        db,
        stage_id,
        current_user.id,
        cascade_materials=cascade_materials,
        operator_id=current_user.id,
        operator_role="teacher",
    ):
        raise BusinessException(404, "阶段不存在")
    db.commit()
    return success()
