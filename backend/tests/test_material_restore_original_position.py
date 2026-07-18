"""资料原位恢复：删除写阶段快照，恢复挂回或重建同名阶段。"""
from app.models.entities import Course, CourseStage, Material
from app.schemas.common import AuthUser
from app.services.soft_delete_service import soft_delete
from tests.conftest import auth_header


def _owned_course(db_session) -> Course:
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    assert course is not None
    return course


def _teacher_token(client) -> str:
    resp = client.post("/api/token", json={"id": "T001", "password": "abc123"})
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def _admin_token(client) -> str:
    resp = client.post("/api/token", json={"id": "admin", "password": "Admin#2026"})
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


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


def test_restore_material_returns_to_existing_stage(client, db_session):
    course = _owned_course(db_session)
    stage = CourseStage(course_id=course.id, name="恢复挂回阶段", sort_order=1)
    db_session.add(stage)
    db_session.flush()
    mat = Material(
        course_id=course.id,
        stage_id=stage.id,
        type="pdf",
        title="可恢复资料",
        url="/r.pdf",
        size="1 MB",
    )
    db_session.add(mat)
    db_session.commit()
    mat_id, stage_id, course_id = mat.id, stage.id, course.id

    soft_delete(
        db_session,
        mat,
        AuthUser(id="T001", name="测试教师", role="teacher"),
        action="material.delete",
    )
    db_session.commit()

    admin = _admin_token(client)
    resp = client.post(
        f"/api/admin/restore/materials/{mat_id}",
        headers=auth_header(admin),
    ).json()
    assert resp["code"] == 0

    db_session.expire_all()
    row = db_session.get(Material, mat_id)
    assert row.deleted_at is None
    assert row.course_id == course_id
    assert row.stage_id == stage_id
    assert row.deleted_stage_name is None
    assert row.deleted_stage_id is None


def test_restore_material_rebuilds_stage_after_cascade_delete(client, db_session):
    token = _teacher_token(client)
    course = _owned_course(db_session)
    stage = CourseStage(course_id=course.id, name="级联原阶段", sort_order=5)
    db_session.add(stage)
    db_session.flush()
    mat = Material(
        course_id=course.id,
        stage_id=stage.id,
        type="pdf",
        title="级联内资料",
        url="/c.pdf",
        size="1 MB",
    )
    db_session.add(mat)
    db_session.commit()
    stage_id, mat_id, course_id = stage.id, mat.id, course.id
    stage_name = "级联原阶段"

    resp = client.delete(
        f"/api/stages/{stage_id}?cascade_materials=true",
        headers=auth_header(token),
    ).json()
    assert resp["code"] == 0
    db_session.expire_all()
    assert db_session.get(CourseStage, stage_id) is None
    dead = db_session.get(Material, mat_id)
    assert dead.deleted_at is not None
    assert dead.deleted_stage_name == stage_name

    admin = _admin_token(client)
    restored = client.post(
        f"/api/admin/restore/materials/{mat_id}",
        headers=auth_header(admin),
    ).json()
    assert restored["code"] == 0

    db_session.expire_all()
    row = db_session.get(Material, mat_id)
    assert row.deleted_at is None
    assert row.course_id == course_id
    assert row.stage_id is not None
    new_stage = db_session.get(CourseStage, row.stage_id)
    assert new_stage is not None
    assert new_stage.course_id == course_id
    assert new_stage.name == stage_name


def test_restore_material_reuses_existing_same_name_stage(client, db_session):
    token = _teacher_token(client)
    course = _owned_course(db_session)
    stage = CourseStage(course_id=course.id, name="同名阶段", sort_order=1)
    db_session.add(stage)
    db_session.flush()
    mat = Material(
        course_id=course.id, stage_id=stage.id, type="pdf",
        title="同名复用", url="/s.pdf", size="1 MB",
    )
    db_session.add(mat)
    db_session.commit()
    stage_id, mat_id = stage.id, mat.id

    assert client.delete(
        f"/api/stages/{stage_id}?cascade_materials=true",
        headers=auth_header(token),
    ).json()["code"] == 0

    recreated = CourseStage(course_id=course.id, name="同名阶段", sort_order=9)
    db_session.add(recreated)
    db_session.commit()
    recreated_id = recreated.id

    admin = _admin_token(client)
    assert client.post(
        f"/api/admin/restore/materials/{mat_id}",
        headers=auth_header(admin),
    ).json()["code"] == 0

    db_session.expire_all()
    row = db_session.get(Material, mat_id)
    assert row.stage_id == recreated_id
    count = db_session.query(CourseStage).filter(
        CourseStage.course_id == course.id, CourseStage.name == "同名阶段"
    ).count()
    assert count == 1


def test_restore_material_without_snapshot_leaves_stage_null(client, db_session):
    course = _owned_course(db_session)
    mat = Material(
        course_id=course.id, stage_id=None, type="pdf",
        title="无阶段旧数据", url="/n.pdf", size="1 MB",
    )
    db_session.add(mat)
    db_session.commit()
    soft_delete(
        db_session, mat,
        AuthUser(id="T001", name="测试教师", role="teacher"),
        action="material.delete",
    )
    mat.deleted_stage_id = None
    mat.deleted_stage_name = None
    mat.deleted_stage_sort_order = None
    db_session.commit()
    mat_id = mat.id

    admin = _admin_token(client)
    assert client.post(
        f"/api/admin/restore/materials/{mat_id}",
        headers=auth_header(admin),
    ).json()["code"] == 0
    db_session.expire_all()
    row = db_session.get(Material, mat_id)
    assert row.deleted_at is None
    assert row.stage_id is None
