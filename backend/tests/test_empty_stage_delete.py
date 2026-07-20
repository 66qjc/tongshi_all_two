"""空阶段删除失败修复：覆盖空阶段、幽灵资料、source_stage_id 引用、级联回归、管理端场景。

设计依据：docs/superpowers/specs/2026-07-19-empty-stage-delete-fix-design.md
"""
from app.models.entities import Course, CourseStage, Material
from app.schemas.common import AuthUser
from app.services.soft_delete_service import soft_delete
from tests.conftest import auth_header


def _teacher_token(client) -> str:
    resp = client.post("/api/token", json={"id": "T001", "password": "abc123"})
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def _admin_token(client) -> str:
    resp = client.post("/api/token", json={"id": "admin", "password": "Admin#2026"})
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


# ─── 场景 1：完全空阶段 + cascade_materials=true 删除成功 ───


def test_empty_stage_delete_with_cascade(client, db_session):
    """完全空阶段传 cascade_materials=true 应删除成功。"""
    token = _teacher_token(client)
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    stage = CourseStage(course_id=course.id, name="空阶段", sort_order=10)
    db_session.add(stage)
    db_session.commit()
    stage_id = stage.id

    resp = client.delete(
        f"/api/stages/{stage_id}?cascade_materials=true",
        headers=auth_header(token),
    ).json()
    assert resp["code"] == 0
    db_session.expire_all()
    assert db_session.get(CourseStage, stage_id) is None


# ─── 场景 2：仅软删资料的阶段删除成功，资料 stage_id 置空且仍软删 ───


def test_stage_with_only_soft_deleted_materials_delete_detaches_stage_id(client, db_session):
    """仅有软删资料时删除阶段，软删资料 stage_id 应置 NULL，且资料仍为软删状态。"""
    token = _teacher_token(client)
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    stage = CourseStage(course_id=course.id, name="幽灵资料阶段", sort_order=11)
    db_session.add(stage)
    db_session.flush()
    ghost = Material(
        course_id=course.id, stage_id=stage.id, type="pdf",
        title="幽灵资料", url="/ghost.pdf", size="1 MB",
    )
    db_session.add(ghost)
    db_session.commit()
    # 软删资料
    soft_delete(
        db_session, ghost,
        AuthUser(id="T001", name="测试教师", role="teacher"),
        action="material.delete",
    )
    db_session.commit()
    stage_id, ghost_id = stage.id, ghost.id

    resp = client.delete(
        f"/api/stages/{stage_id}",
        headers=auth_header(token),
    ).json()
    assert resp["code"] == 0
    db_session.expire_all()
    assert db_session.get(CourseStage, stage_id) is None
    # 关键断言：软删资料 stage_id 应被置空
    ghost_row = db_session.get(Material, ghost_id)
    assert ghost_row is not None
    assert ghost_row.deleted_at is not None, "资料应仍为软删状态"
    assert ghost_row.stage_id is None, "软删资料的 stage_id 应被置空"


# ─── 场景 3：存在 source_stage_id 指向目标阶段时删除成功，引用方置 NULL ───


def test_delete_stage_detaches_incoming_source_stage_id(client, db_session):
    """删除被其它阶段 source_stage_id 引用的阶段，引用方 source_stage_id 应置 NULL。"""
    token = _teacher_token(client)
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    # 源阶段（将被删除）
    source_stage = CourseStage(course_id=course.id, name="源阶段", sort_order=12)
    db_session.add(source_stage)
    db_session.flush()
    # 引用方阶段
    referencing_stage = CourseStage(
        course_id=course.id, name="引用方阶段",
        source_stage_id=source_stage.id, sort_order=13,
    )
    db_session.add(referencing_stage)
    db_session.commit()
    source_id, ref_id = source_stage.id, referencing_stage.id

    resp = client.delete(
        f"/api/stages/{source_id}",
        headers=auth_header(token),
    ).json()
    assert resp["code"] == 0
    db_session.expire_all()
    assert db_session.get(CourseStage, source_id) is None
    # 关键断言：引用方 source_stage_id 应被置空
    ref_row = db_session.get(CourseStage, ref_id)
    assert ref_row is not None
    assert ref_row.source_stage_id is None, "引用方的 source_stage_id 应被置空"


# ─── 场景 4：回归 — 有活跃资料不传 cascade 仍拒绝 ───


def test_active_materials_without_cascade_still_blocks(client, db_session):
    """有活跃资料且不传 cascade 时仍应拒绝删除。"""
    token = _teacher_token(client)
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    stage = CourseStage(course_id=course.id, name="活跃资料阻塞", sort_order=14)
    db_session.add(stage)
    db_session.flush()
    db_session.add(Material(
        course_id=course.id, stage_id=stage.id, type="pdf",
        title="活跃资料", url="/active.pdf", size="1 MB",
    ))
    db_session.commit()
    stage_id = stage.id

    resp = client.delete(f"/api/stages/{stage_id}", headers=auth_header(token))
    body = resp.json()
    assert body.get("code", 0) != 0 or resp.status_code >= 400
    db_session.expire_all()
    assert db_session.get(CourseStage, stage_id) is not None


# ─── 场景 5：回归 — 传 cascade 仍软删活跃资料并删阶段 ───


def test_cascade_soft_deletes_active_and_detaches_all(client, db_session):
    """cascade_materials=true 时软删活跃资料、脱钩全部资料 stage_id、删除阶段。"""
    token = _teacher_token(client)
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    stage = CourseStage(course_id=course.id, name="级联全脱钩", sort_order=15)
    db_session.add(stage)
    db_session.flush()
    active_mat = Material(
        course_id=course.id, stage_id=stage.id, type="pdf",
        title="活跃资料", url="/a.pdf", size="1 MB",
    )
    ghost_mat = Material(
        course_id=course.id, stage_id=stage.id, type="pdf",
        title="已软删资料", url="/g.pdf", size="1 MB",
    )
    db_session.add_all([active_mat, ghost_mat])
    db_session.commit()
    # 先软删 ghost_mat
    soft_delete(
        db_session, ghost_mat,
        AuthUser(id="T001", name="测试教师", role="teacher"),
        action="material.delete",
    )
    db_session.commit()
    stage_id = stage.id
    active_id, ghost_id = active_mat.id, ghost_mat.id

    resp = client.delete(
        f"/api/stages/{stage_id}?cascade_materials=true",
        headers=auth_header(token),
    ).json()
    assert resp["code"] == 0
    db_session.expire_all()
    assert db_session.get(CourseStage, stage_id) is None
    # 活跃资料被软删
    active_row = db_session.get(Material, active_id)
    assert active_row.deleted_at is not None
    assert active_row.stage_id is None, "活跃资料软删后 stage_id 应被置空"
    # 已软删资料也脱钩
    ghost_row = db_session.get(Material, ghost_id)
    assert ghost_row.deleted_at is not None
    assert ghost_row.stage_id is None, "已软删资料 stage_id 应被置空"


# ─── 场景 6：管理端 — 空公共阶段可删 ───


def test_admin_delete_empty_public_stage(client, db_session):
    """管理端删除完全空的公共阶段应成功。"""
    admin_token = _admin_token(client)
    public = Course(name="空公共课程", is_public=True, created_by="admin")
    db_session.add(public)
    db_session.flush()
    stage = CourseStage(course_id=public.id, name="空公共阶段", sort_order=0)
    db_session.add(stage)
    db_session.commit()
    stage_id, course_id = stage.id, public.id

    resp = client.delete(
        f"/api/admin/public-courses/{course_id}/stages/{stage_id}",
        headers=auth_header(admin_token),
    ).json()
    assert resp["code"] == 0
    db_session.expire_all()
    assert db_session.get(CourseStage, stage_id) is None


# ─── 场景 7：管理端 — 仅幽灵资料的公共阶段可删 ───


def test_admin_delete_public_stage_with_only_ghost_materials(client, db_session):
    """管理端删除仅有软删资料的公共阶段应成功，资料 stage_id 置空。"""
    admin_token = _admin_token(client)
    public = Course(name="幽灵公共课程", is_public=True, created_by="admin")
    db_session.add(public)
    db_session.flush()
    stage = CourseStage(course_id=public.id, name="幽灵公共阶段", sort_order=0)
    db_session.add(stage)
    db_session.flush()
    ghost = Material(
        course_id=public.id, stage_id=stage.id, type="pdf",
        title="幽灵公共资料", url="/gp.pdf", size="1 MB",
    )
    db_session.add(ghost)
    db_session.commit()
    soft_delete(
        db_session, ghost,
        AuthUser(id="admin", name="管理员", role="admin"),
        action="material.delete",
    )
    db_session.commit()
    stage_id, course_id, ghost_id = stage.id, public.id, ghost.id

    resp = client.delete(
        f"/api/admin/public-courses/{course_id}/stages/{stage_id}",
        headers=auth_header(admin_token),
    ).json()
    assert resp["code"] == 0
    db_session.expire_all()
    assert db_session.get(CourseStage, stage_id) is None
    ghost_row = db_session.get(Material, ghost_id)
    assert ghost_row is not None
    assert ghost_row.deleted_at is not None
    assert ghost_row.stage_id is None, "管理端删除后幽灵资料 stage_id 应被置空"
