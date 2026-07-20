"""课程活跃名称唯一约束测试。

覆盖：同教师重名拒绝、不同教师同名允许、软删后同名可建、恢复冲突拒绝。
"""
from app.models.entities import Course
from app.schemas.common import AuthUser
from app.services.question_service import add_public_course, create_course, update_course
from app.services.soft_delete_service import soft_delete, restore_resource
from app.services.admin_public_course_service import create_public_course, update_public_course
from app.core.exceptions import BusinessException
from tests.conftest import auth_header

from datetime import datetime, timezone

import pytest


# ─── 场景 1：同教师创建同名活跃课程被拒绝 ───


def test_same_teacher_duplicate_active_name_rejected(client, db_session):
    """同教师下已存在活跃同名课程时，再次创建应拒绝。"""
    resp = client.post("/api/token", json={"id": "T001", "password": "abc123"})
    token = resp.json()["data"]["access_token"]

    # 种子数据已有"测试课程"(T001)，再创建同名
    resp = client.post(
        "/api/courses",
        json={"name": "测试课程"},
        headers=auth_header(token),
    )
    body = resp.json()
    # 应返回业务错误（code != 0）
    assert body.get("code", 0) != 0 or resp.status_code >= 400


# ─── 场景 2：不同教师可以创建同名课程 ───


def test_different_teacher_same_name_allowed(client, db_session):
    """不同教师创建同名课程应成功。"""
    resp = client.post("/api/token", json={"id": "T002", "password": "abc123"})
    token = resp.json()["data"]["access_token"]

    resp = client.post(
        "/api/courses",
        json={"name": "测试课程"},
        headers=auth_header(token),
    )
    body = resp.json()
    assert body["code"] == 0
    # 验证确实创建了
    courses = db_session.query(Course).filter(
        Course.name == "测试课程", Course.created_by == "T002", Course.deleted_at.is_(None)
    ).all()
    assert len(courses) == 1


# ─── 场景 3：软删课程后同教师可创建同名课程 ───


def test_soft_deleted_course_does_not_block_same_name(client, db_session):
    """软删课程后，同教师可以创建同名新课程。"""
    # 软删种子数据中的"测试课程"
    course = db_session.query(Course).filter(
        Course.name == "测试课程", Course.created_by == "T001"
    ).first()
    soft_delete(
        db_session, course,
        AuthUser(id="T001", name="测试教师", role="teacher"),
        action="course.delete",
    )
    db_session.commit()

    resp = client.post("/api/token", json={"id": "T001", "password": "abc123"})
    token = resp.json()["data"]["access_token"]

    resp = client.post(
        "/api/courses",
        json={"name": "测试课程"},
        headers=auth_header(token),
    )
    body = resp.json()
    assert body["code"] == 0


# ─── 场景 4：恢复课程时与活跃同名课程冲突被拒绝 ───


def test_restore_conflicts_with_active_same_name(client, db_session):
    """恢复软删课程时，若同教师下已有活跃同名课程，应拒绝恢复。"""
    # 先软删"测试课程"
    course = db_session.query(Course).filter(
        Course.name == "测试课程", Course.created_by == "T001"
    ).first()
    soft_delete(
        db_session, course,
        AuthUser(id="T001", name="测试教师", role="teacher"),
        action="course.delete",
    )
    db_session.commit()
    deleted_course_id = course.id

    # 创建同名新课程
    resp = client.post("/api/token", json={"id": "T001", "password": "abc123"})
    token = resp.json()["data"]["access_token"]
    resp = client.post(
        "/api/courses",
        json={"name": "测试课程"},
        headers=auth_header(token),
    )
    assert resp.json()["code"] == 0

    # 尝试恢复旧课程，应冲突
    with pytest.raises(BusinessException) as exc_info:
        restore_resource(
            db_session, "courses", str(deleted_course_id),
            AuthUser(id="T001", name="测试教师", role="teacher"),
        )
    assert "已存在活跃课程" in str(exc_info.value.message)


# ─── 场景 5：多个软删同名课程不互相阻塞 ───


def test_multiple_soft_deleted_same_name_allowed(client, db_session):
    """多个软删同名课程可以共存，不互相阻塞。"""
    course = db_session.query(Course).filter(
        Course.name == "测试课程", Course.created_by == "T001"
    ).first()
    # 软删第一个
    soft_delete(
        db_session, course,
        AuthUser(id="T001", name="测试教师", role="teacher"),
        action="course.delete",
    )
    db_session.commit()

    # 创建第二个同名
    new_course = Course(name="测试课程", created_by="T001")
    db_session.add(new_course)
    db_session.commit()

    # 软删第二个
    soft_delete(
        db_session, new_course,
        AuthUser(id="T001", name="测试教师", role="teacher"),
        action="course.delete",
    )
    db_session.commit()

    # 两个软删同名课程共存
    deleted = db_session.query(Course).filter(
        Course.name == "测试课程", Course.created_by == "T001", Course.deleted_at.isnot(None)
    ).all()
    assert len(deleted) == 2

    # 仍可创建新的活跃同名课程
    resp = client.post("/api/token", json={"id": "T001", "password": "abc123"})
    token = resp.json()["data"]["access_token"]
    resp = client.post(
        "/api/courses",
        json={"name": "测试课程"},
        headers=auth_header(token),
    )
    assert resp.json()["code"] == 0




def test_update_course_ignores_same_name_soft_deleted_course(db_session):
    """课程改名时，只有活跃课程才应阻止同名。"""
    active = Course(name="active-course", created_by="T001")
    deleted = Course(
        name="historical-name",
        created_by="T001",
        deleted_at=datetime.now(timezone.utc),
        deleted_by="T001",
    )
    db_session.add_all([active, deleted])
    db_session.commit()

    updated = update_course(db_session, active.id, "historical-name", "T001")

    assert updated.name == "historical-name"


def test_restore_course_integrity_error_is_business_error(db_session, monkeypatch):
    """恢复时数据库唯一冲突应回滚并返回业务错误，而不是 500。"""
    course = Course(
        name="concurrent-restore-course",
        created_by="T001",
        deleted_at=datetime.now(timezone.utc),
        deleted_by="T001",
    )
    db_session.add(course)
    db_session.commit()

    from sqlalchemy.exc import IntegrityError

    rollback_called = False
    original_rollback = db_session.rollback

    def fail_flush(*args, **kwargs):
        raise IntegrityError("UPDATE courses", {}, Exception("duplicate key"))

    def track_rollback():
        nonlocal rollback_called
        rollback_called = True
        original_rollback()

    monkeypatch.setattr(db_session, "flush", fail_flush)
    monkeypatch.setattr(db_session, "rollback", track_rollback)

    with pytest.raises(BusinessException) as exc_info:
        restore_resource(
            db_session,
            "courses",
            str(course.id),
            AuthUser(id="T001", name="tester", role="teacher"),
        )

    assert rollback_called
    assert exc_info.value.code == 400


def test_create_public_course_ignores_same_name_soft_deleted_course(db_session):
    """管理员创建公共课时，历史软删同名课程不应阻塞。"""
    deleted = Course(
        name="历史公共课程",
        created_by="admin",
        is_public=True,
        deleted_at=datetime.now(timezone.utc),
        deleted_by="admin",
    )
    db_session.add(deleted)
    db_session.commit()

    created = create_public_course(db_session, "历史公共课程", "admin")

    assert created.deleted_at is None
    assert created.id != deleted.id



def test_add_public_course_integrity_error_is_business_error(db_session, monkeypatch):
    """教师并发添加同名公共课副本时，唯一冲突应回滚并返回业务错误。"""
    from sqlalchemy.exc import IntegrityError

    source = Course(name="并发公共课程", created_by="admin", is_public=True)
    db_session.add(source)
    db_session.commit()

    rollback_called = False
    original_rollback = db_session.rollback

    def fail_flush(*args, **kwargs):
        raise IntegrityError("INSERT courses", {}, Exception("duplicate key"))

    def track_rollback():
        nonlocal rollback_called
        rollback_called = True
        original_rollback()

    monkeypatch.setattr(db_session, "flush", fail_flush)
    monkeypatch.setattr(db_session, "rollback", track_rollback)

    with pytest.raises(BusinessException) as exc_info:
        add_public_course(db_session, source.id, "T001")

    assert rollback_called
    assert exc_info.value.code == 400
    assert "课程已存在" in exc_info.value.message



def test_update_public_course_rolls_back_copy_name_conflict(db_session):
    """公共课改名若与教师已有课程冲突，应整体回滚公共课及副本名称。"""
    source = Course(name="公共课原名", created_by="admin", is_public=True)
    db_session.add(source)
    db_session.flush()
    copy = Course(
        name="公共课原名",
        created_by="T001",
        source_course_id=source.id,
    )
    occupied = Course(name="教师占用名", created_by="T001")
    db_session.add_all([copy, occupied])
    db_session.commit()

    with pytest.raises(BusinessException) as exc_info:
        update_public_course(db_session, source.id, "教师占用名")

    assert exc_info.value.code == 400
    assert "教师课程中已存在同名课程" in exc_info.value.message
    db_session.expire_all()
    assert db_session.get(Course, source.id).name == "公共课原名"
    assert db_session.get(Course, copy.id).name == "公共课原名"
