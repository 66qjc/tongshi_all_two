"""阶段/资料删除：读路径过滤软删资料，删阶段支持级联软删。"""
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


def test_course_detail_hides_soft_deleted_materials(client, db_session):
    """软删资料不得出现在课程详情阶段列表中。"""
    token = _teacher_token(client)
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    assert course is not None
    stage = CourseStage(course_id=course.id, name="阶段A", sort_order=0)
    db_session.add(stage)
    db_session.flush()
    alive = Material(
        course_id=course.id, stage_id=stage.id, type="pdf",
        title="仍在", url="/alive.pdf", size="1 MB",
    )
    ghost = Material(
        course_id=course.id, stage_id=stage.id, type="pdf",
        title="已删幽灵", url="/ghost.pdf", size="1 MB",
    )
    db_session.add_all([alive, ghost])
    db_session.commit()
    soft_delete(
        db_session,
        ghost,
        AuthUser(id="T001", name="测试教师", role="teacher"),
        action="material.delete",
    )
    db_session.commit()

    detail = client.get(f"/api/courses/{course.id}", headers=auth_header(token)).json()
    assert detail["code"] == 0
    stages = detail["data"]["stages"]
    target = next(s for s in stages if s["id"] == stage.id)
    titles = [m["title"] for m in target["materials"]]
    assert "仍在" in titles
    assert "已删幽灵" not in titles


def test_delete_stage_cascade_soft_deletes_active_materials(client, db_session):
    """cascade_materials=true 时软删阶段下活跃资料并删除阶段。"""
    token = _teacher_token(client)
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    stage = CourseStage(course_id=course.id, name="待删阶段", sort_order=1)
    db_session.add(stage)
    db_session.flush()
    mat = Material(
        course_id=course.id, stage_id=stage.id, type="pdf",
        title="阶段内PDF", url="/s.pdf", size="1 MB",
    )
    db_session.add(mat)
    db_session.commit()
    stage_id, mat_id = stage.id, mat.id

    resp = client.delete(
        f"/api/stages/{stage_id}?cascade_materials=true",
        headers=auth_header(token),
    ).json()
    assert resp["code"] == 0

    db_session.expire_all()
    assert db_session.get(CourseStage, stage_id) is None
    row = db_session.get(Material, mat_id)
    assert row is not None
    assert row.deleted_at is not None


def test_delete_stage_without_cascade_blocks_when_active_materials(client, db_session):
    """默认不传 cascade 且存在活跃资料时拒绝删除。"""
    token = _teacher_token(client)
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    stage = CourseStage(course_id=course.id, name="阻塞阶段", sort_order=2)
    db_session.add(stage)
    db_session.flush()
    db_session.add(Material(
        course_id=course.id, stage_id=stage.id, type="pdf",
        title="挡路", url="/b.pdf", size="1 MB",
    ))
    db_session.commit()

    resp = client.delete(f"/api/stages/{stage.id}", headers=auth_header(token))
    body = resp.json()
    assert body.get("code", 0) != 0 or resp.status_code >= 400
    assert db_session.get(CourseStage, stage.id) is not None


def test_delete_stage_ignores_soft_deleted_materials_without_cascade(client, db_session):
    """仅有软删资料时，不传 cascade 也应能删阶段。"""
    token = _teacher_token(client)
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    stage = CourseStage(course_id=course.id, name="仅幽灵阶段", sort_order=3)
    db_session.add(stage)
    db_session.flush()
    ghost = Material(
        course_id=course.id, stage_id=stage.id, type="pdf",
        title="已软删", url="/g.pdf", size="1 MB",
    )
    db_session.add(ghost)
    db_session.commit()
    soft_delete(
        db_session,
        ghost,
        AuthUser(id="T001", name="测试教师", role="teacher"),
        action="material.delete",
    )
    db_session.commit()
    stage_id = stage.id

    resp = client.delete(f"/api/stages/{stage_id}", headers=auth_header(token)).json()
    assert resp["code"] == 0
    db_session.expire_all()
    assert db_session.get(CourseStage, stage_id) is None


def test_admin_delete_public_stage_cascade(client, db_session):
    """管理端级联删除公共阶段及其活跃资料。"""
    admin_token = _admin_token(client)
    public = Course(name="公共级联课", is_public=True, created_by="admin")
    db_session.add(public)
    db_session.flush()
    stage = CourseStage(course_id=public.id, name="公共阶段", sort_order=0)
    db_session.add(stage)
    db_session.flush()
    mat = Material(
        course_id=public.id, stage_id=stage.id, type="pdf",
        title="公共PDF", url="/p.pdf", size="1 MB",
    )
    db_session.add(mat)
    db_session.commit()
    stage_id, mat_id, course_id = stage.id, mat.id, public.id

    resp = client.delete(
        f"/api/admin/public-courses/{course_id}/stages/{stage_id}?cascade_materials=true",
        headers=auth_header(admin_token),
    ).json()
    assert resp["code"] == 0
    db_session.expire_all()
    assert db_session.get(CourseStage, stage_id) is None
    assert db_session.get(Material, mat_id).deleted_at is not None


def test_admin_delete_public_stage_moves_teacher_owned_material_to_uncategorized(client, db_session):
    """删除公共源阶段时，教师在副本阶段自建的资料必须保留。"""
    admin_token = _admin_token(client)
    teacher_token = _teacher_token(client)
    public = Course(name="公共阶段保留自建资料", is_public=True, created_by="admin")
    teacher_copy = Course(
        name="教师副本保留自建资料",
        is_public=False,
        created_by="T001",
        source_course_id=None,
    )
    db_session.add_all([public, teacher_copy])
    db_session.flush()
    source_stage = CourseStage(course_id=public.id, name="公共源阶段", sort_order=0)
    copy_stage = CourseStage(
        course_id=teacher_copy.id,
        source_stage_id=None,
        name="教师副本阶段",
        sort_order=0,
    )
    db_session.add_all([source_stage, copy_stage])
    db_session.flush()
    copy_stage.source_stage_id = source_stage.id
    source_material = Material(
        course_id=public.id,
        stage_id=source_stage.id,
        type="pdf",
        title="公共同步资料",
        url="/source.pdf",
        size="1 MB",
    )
    db_session.add(source_material)
    db_session.flush()
    synced_material = Material(
        course_id=teacher_copy.id,
        stage_id=copy_stage.id,
        source_material_id=source_material.id,
        type="pdf",
        title="同步副本资料",
        url="/synced.pdf",
        size="1 MB",
    )
    teacher_material = Material(
        course_id=teacher_copy.id,
        stage_id=copy_stage.id,
        type="pdf",
        title="教师自建资料",
        url="/teacher-owned.pdf",
        size="1 MB",
    )
    db_session.add_all([synced_material, teacher_material])
    db_session.commit()
    ids = (source_stage.id, copy_stage.id, source_material.id, synced_material.id, teacher_material.id)

    response = client.delete(
        f"/api/admin/public-courses/{public.id}/stages/{source_stage.id}?cascade_materials=true",
        headers=auth_header(admin_token),
    ).json()

    assert response["code"] == 0
    db_session.expire_all()
    assert db_session.get(CourseStage, ids[0]) is None
    assert db_session.get(CourseStage, ids[1]) is None
    assert db_session.get(Material, ids[2]).deleted_at is not None
    assert db_session.get(Material, ids[3]).deleted_at is not None
    preserved = db_session.get(Material, ids[4])
    assert preserved.deleted_at is None
    assert preserved.stage_id is None

    detail = client.get(
        f"/api/courses/{teacher_copy.id}",
        headers=auth_header(teacher_token),
    ).json()
    assert detail["code"] == 0
    assert [item["title"] for item in detail["data"]["uncategorized_materials"]] == ["教师自建资料"]


def test_admin_delete_public_stage_without_cascade_has_no_copy_side_effects(client, db_session):
    """源阶段存在资料且未请求级联时，不能先改动教师副本。"""
    admin_token = _admin_token(client)
    public = Course(name="公共阶段拒绝副作用", is_public=True, created_by="admin")
    teacher_copy = Course(name="教师副本拒绝副作用", is_public=False, created_by="T001")
    db_session.add_all([public, teacher_copy])
    db_session.flush()
    source_stage = CourseStage(course_id=public.id, name="阻塞源阶段", sort_order=0)
    copy_stage = CourseStage(course_id=teacher_copy.id, name="阻塞副本阶段", sort_order=0)
    db_session.add_all([source_stage, copy_stage])
    db_session.flush()
    copy_stage.source_stage_id = source_stage.id
    db_session.add(Material(
        course_id=public.id,
        stage_id=source_stage.id,
        type="pdf",
        title="阻塞源资料",
        url="/blocking-source.pdf",
        size="1 MB",
    ))
    teacher_material = Material(
        course_id=teacher_copy.id,
        stage_id=copy_stage.id,
        type="pdf",
        title="不应移动的教师资料",
        url="/unchanged.pdf",
        size="1 MB",
    )
    db_session.add(teacher_material)
    db_session.commit()
    source_stage_id, copy_stage_id, material_id = source_stage.id, copy_stage.id, teacher_material.id

    response = client.delete(
        f"/api/admin/public-courses/{public.id}/stages/{source_stage_id}",
        headers=auth_header(admin_token),
    ).json()

    assert response["code"] != 0
    db_session.expire_all()
    assert db_session.get(CourseStage, source_stage_id) is not None
    assert db_session.get(CourseStage, copy_stage_id) is not None
    untouched = db_session.get(Material, material_id)
    assert untouched.deleted_at is None
    assert untouched.stage_id == copy_stage_id
