"""资料原位恢复：删除写阶段快照，恢复挂回或重建同名阶段。"""
from app.models.entities import Course, CourseStage, Material
from app.schemas.common import AuthUser
from app.services.soft_delete_service import soft_delete


def _owned_course(db_session) -> Course:
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    assert course is not None
    return course


def test_soft_delete_material_writes_stage_snapshot(db_session):
    course = _owned_course(db_session)
    stage = CourseStage(course_id=course.id, name="原位阶段A", sort_order=3)
    db_session.add(stage)
    db_session.flush()
    mat = Material(
        course_id=course.id,
        stage_id=stage.id,
        type="pdf",
        title="待删PDF",
        url="/a.pdf",
        size="1 MB",
    )
    db_session.add(mat)
    db_session.commit()

    soft_delete(
        db_session,
        mat,
        AuthUser(id="T001", name="测试教师", role="teacher"),
        action="material.delete",
    )
    db_session.commit()
    db_session.expire_all()

    row = db_session.get(Material, mat.id)
    assert row is not None
    assert row.deleted_at is not None
    assert row.deleted_stage_id == stage.id
    assert row.deleted_stage_name == "原位阶段A"
    assert row.deleted_stage_sort_order == 3
