"""软删除读路径过滤测试：已软删资源在正常业务中不可见/不可用。"""

from datetime import datetime, timezone

from app.models.entities import (
    Announcement,
    AnnouncementClass,
    Class,
    Course,
    Material,
    Project,
    Question,
    StudentClassEnrollment,
    User,
)
from app.services import admin_public_course_service
from app.services.question_bank_service import (
    collect_question_fingerprints,
    count_all_questions,
    find_duplicate_question,
    find_same_stem_question,
    list_all_questions,
)
from app.services.question_service import import_questions_from_excel
from app.services.access_control_service import student_can_access_course
from app.services.material_service import can_view_course_materials, list_materials
from app.services.public_learning_service import list_public_courses, list_public_materials, get_public_course
from app.services.task_service import get_accessible_assignment
from app.api.v1.routes import admin_public_course_routes
from app.core.exceptions import BusinessException
import pytest


def test_student_cannot_access_soft_deleted_course(db_session):
    course = db_session.query(Course).filter(Course.name == "测试课程").first()
    assert student_can_access_course(db_session, "2025001", course.id) is True

    course.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    assert student_can_access_course(db_session, "2025001", course.id) is False


def test_student_cannot_access_course_via_soft_deleted_class(db_session):
    course = db_session.query(Course).filter(Course.name == "测试课程").first()
    cls = db_session.query(Class).filter(Class.course_id == course.id).first()
    assert student_can_access_course(db_session, "2025001", course.id) is True

    cls.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    assert student_can_access_course(db_session, "2025001", course.id) is False


def test_list_materials_hides_soft_deleted_material_and_course(db_session):
    course = db_session.query(Course).filter(Course.name == "测试课程").first()
    live = Material(course_id=course.id, type="pdf", title="活跃资料", url="/a.pdf", size="1 MB")
    dead = Material(course_id=course.id, type="pdf", title="已删资料", url="/b.pdf", size="1 MB")
    db_session.add_all([live, dead])
    db_session.flush()
    dead.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    materials, total = list_materials(db_session, course_id=course.id)
    titles = [m.title for m in materials]
    assert "活跃资料" in titles
    assert "已删资料" not in titles
    assert total == len(materials)

    course.deleted_at = datetime.now(timezone.utc)
    db_session.commit()
    materials_after, total_after = list_materials(db_session, course_id=course.id)
    assert materials_after == []
    assert total_after == 0


def test_can_view_course_materials_rejects_soft_deleted_course(db_session):
    course = db_session.query(Course).filter(Course.name == "测试课程").first()
    assert can_view_course_materials(db_session, course.id, "2025001", "student") is True
    course.deleted_at = datetime.now(timezone.utc)
    db_session.commit()
    assert can_view_course_materials(db_session, course.id, "2025001", "student") is False


def test_get_accessible_assignment_rejects_soft_deleted_announcement(db_session):
    course = db_session.query(Course).filter(Course.name == "测试课程").first()
    cls = db_session.query(Class).filter(Class.course_id == course.id).first()
    ann = Announcement(
        course_id=course.id,
        teacher_id="T001",
        type="task",
        title="软删作业",
        question_ids=[],
        max_score=100.0,
    )
    db_session.add(ann)
    db_session.flush()
    db_session.add(AnnouncementClass(announcement_id=ann.id, class_id=cls.id))
    db_session.commit()

    assert get_accessible_assignment(db_session, "2025001", ann.id) is not None

    ann.deleted_at = datetime.now(timezone.utc)
    db_session.commit()
    assert get_accessible_assignment(db_session, "2025001", ann.id) is None


def test_get_accessible_assignment_rejects_soft_deleted_class(db_session):
    course = db_session.query(Course).filter(Course.name == "测试课程").first()
    cls = db_session.query(Class).filter(Class.course_id == course.id).first()
    ann = Announcement(
        course_id=course.id,
        teacher_id="T001",
        type="task",
        title="班级软删作业",
        question_ids=[],
        max_score=100.0,
    )
    db_session.add(ann)
    db_session.flush()
    db_session.add(AnnouncementClass(announcement_id=ann.id, class_id=cls.id))
    db_session.commit()

    cls.deleted_at = datetime.now(timezone.utc)
    db_session.commit()
    assert get_accessible_assignment(db_session, "2025001", ann.id) is None


def test_public_learning_hides_soft_deleted_course_and_material(db_session):
    public_course = Course(name="公开软删课", created_by="admin", is_public=True)
    db_session.add(public_course)
    db_session.flush()
    live = Material(course_id=public_course.id, type="pdf", title="公开活跃资料", url="/p1.pdf", size="1 MB")
    dead = Material(course_id=public_course.id, type="pdf", title="公开已删资料", url="/p2.pdf", size="1 MB")
    db_session.add_all([live, dead])
    db_session.flush()
    dead.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    materials = list_public_materials(db_session, course_id=public_course.id)
    titles = [item["title"] for item in materials["items"]]
    assert "公开活跃资料" in titles
    assert "公开已删资料" not in titles

    public_course.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    listed = list_public_courses(db_session)
    names = [item["name"] for item in listed["courses"]]
    assert "公开软删课" not in names

    with pytest.raises(BusinessException) as exc:
        get_public_course(db_session, public_course.id)
    assert exc.value.code == 404


def test_admin_public_course_queries_hide_soft_deleted_courses(db_session):
    """管理员公共课程列表和按 ID 查询都不应返回软删除课程。"""
    live = Course(name="管理端活跃公共课", created_by="admin", is_public=True)
    deleted = Course(
        name="管理端已删公共课",
        created_by="admin",
        is_public=True,
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add_all([live, deleted])
    db_session.commit()

    courses = admin_public_course_service.list_public_courses.__wrapped__(db_session)
    assert live in courses
    assert deleted not in courses
    assert admin_public_course_service.get_course_by_id(db_session, deleted.id) is None
    assert admin_public_course_service._get_public_course(db_session, deleted.id) is None


def test_admin_public_material_queries_hide_soft_deleted_records(db_session):
    """软删除资料及其所属软删除课程不能再被管理员读取、编辑或删除。"""
    course = Course(name="管理端资料软删课", created_by="admin", is_public=True)
    db_session.add(course)
    db_session.flush()
    live = Material(course_id=course.id, type="link", title="活跃管理资料", url="https://example.com/live")
    deleted = Material(
        course_id=course.id,
        type="link",
        title="已删管理资料",
        url="https://example.com/deleted",
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add_all([live, deleted])
    db_session.commit()

    listed = admin_public_course_service.list_public_materials(db_session, course.id)
    assert live in listed
    assert deleted not in listed
    assert admin_public_course_service.get_public_material(db_session, deleted.id) is None
    assert admin_public_course_service.update_public_material(
        db_session,
        deleted.id,
        {"title": "不应更新"},
    ) is None
    assert admin_public_course_service.delete_public_material(db_session, deleted.id) is False

    course.deleted_at = datetime.now(timezone.utc)
    db_session.commit()
    assert admin_public_course_service.get_public_material(db_session, live.id) is None
    assert admin_public_course_service.update_public_material(
        db_session,
        live.id,
        {"title": "课程删除后不应更新"},
    ) is None
    assert admin_public_course_service.delete_public_material(db_session, live.id) is False
    with pytest.raises(BusinessException) as exc:
        admin_public_course_service.list_public_materials(db_session, course.id)
    assert exc.value.code == 404


@pytest.mark.parametrize(
    ("role", "operator_id"),
    [("teacher", "T001"), ("admin", "admin")],
)
def test_question_excel_import_rejects_soft_deleted_course_for_teacher_and_admin(
    db_session,
    role,
    operator_id,
):
    """教师和管理员导入时都不得向已软删除课程写入题目。"""
    course = Course(
        name=f"已删除导入课程-{role}",
        created_by="T001",
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add(course)
    db_session.commit()

    result = import_questions_from_excel(
        db_session,
        [{
            "课程名称": course.name,
            "题型": "fill",
            "题干": f"{role} 软删除课程导入题目",
            "选项": "",
            "答案": "答案",
            "解析": "",
            "标签": "",
        }],
        teacher_id=operator_id,
        role=role,
    )

    assert result["success_count"] == 0
    assert result["fail_count"] == 1
    assert "未找到课程" in result["errors"][0]["reason"]
    assert db_session.query(Question).filter(Question.course_id == course.id).count() == 0


def test_admin_public_course_format_ignores_soft_deleted_materials_and_questions(db_session):
    """公共课程格式化仅统计活跃资料和题目，仍保留传入的全站题目总数。"""
    course = Course(name="管理端汇总软删除课程", created_by="admin", is_public=True)
    db_session.add(course)
    db_session.flush()
    db_session.add_all([
        Material(course_id=course.id, type="link", title="活跃资料", url="https://example.com/live"),
        Material(
            course_id=course.id,
            type="link",
            title="已删除资料",
            url="https://example.com/deleted",
            deleted_at=datetime.now(timezone.utc),
        ),
        Question(
            course_id=course.id,
            type="fill",
            stem="已删除汇总题目",
            options=[],
            answer="答案",
            deleted_at=datetime.now(timezone.utc),
        ),
    ])
    db_session.commit()

    formatted = admin_public_course_routes._format_course(course)
    assert formatted["material_count"] == 1
    assert formatted["question_count"] == 0
    assert admin_public_course_routes._format_course(course, total_question_count=99)["question_count"] == 99


def test_admin_public_course_sync_status_ignores_soft_deleted_copies_and_records(db_session):
    """同步摘要只统计活跃副本、活跃源资料和活跃同步资料。"""
    course = Course(name="管理端同步软删除课程", created_by="admin", is_public=True)
    db_session.add(course)
    db_session.flush()
    active_source_material = Material(
        course_id=course.id,
        type="link",
        title="活跃源资料",
        url="https://example.com/source-live",
    )
    deleted_source_material = Material(
        course_id=course.id,
        type="link",
        title="已删除源资料",
        url="https://example.com/source-deleted",
        deleted_at=datetime.now(timezone.utc),
    )
    deleted_source_question = Question(
        course_id=course.id,
        type="fill",
        stem="已删除源题目",
        options=[],
        answer="答案",
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add_all([active_source_material, deleted_source_material, deleted_source_question])
    db_session.flush()

    active_copy = Course(
        name="管理端同步活跃副本",
        created_by="T001",
        source_course_id=course.id,
    )
    deleted_copy = Course(
        name="管理端同步已删除副本",
        created_by="T002",
        source_course_id=course.id,
        deleted_at=datetime.now(timezone.utc),
    )
    unrelated_course = Course(name="管理端同步无关课程", created_by="T001")
    db_session.add_all([active_copy, deleted_copy, unrelated_course])
    db_session.flush()
    db_session.add_all([
        Material(
            course_id=active_copy.id,
            type="link",
            title="活跃同步资料",
            url="https://example.com/synced-live",
            source_material_id=active_source_material.id,
        ),
        Material(
            course_id=active_copy.id,
            type="link",
            title="已删除同步资料",
            url="https://example.com/synced-deleted",
            source_material_id=active_source_material.id,
            deleted_at=datetime.now(timezone.utc),
        ),
        Material(
            course_id=deleted_copy.id,
            type="link",
            title="已删除副本资料",
            url="https://example.com/deleted-copy",
            source_material_id=active_source_material.id,
        ),
        Material(
            course_id=active_copy.id,
            type="link",
            title="来自已删除源资料的副本",
            url="https://example.com/deleted-source",
            source_material_id=deleted_source_material.id,
        ),
        Material(
            course_id=unrelated_course.id,
            type="link",
            title="无关课程误关联资料",
            url="https://example.com/unrelated-course",
            source_material_id=active_source_material.id,
        ),
    ])
    db_session.commit()

    sync_info = admin_public_course_service.get_course_sync_status(db_session, course)
    assert sync_info["sync_copy_count"] == 1
    assert sync_info["synced_material_count"] == 1
    assert sync_info["synced_question_count"] == 0
    assert sync_info["sync_status"] == "synced"


def test_admin_public_course_sync_status_excludes_shared_questions_from_sync_denominator(db_session):
    """共享题库题目不复制到副本，不应阻塞资料同步状态。"""
    course = Course(name="管理端共享题同步状态课程", created_by="admin", is_public=True)
    db_session.add(course)
    db_session.flush()
    source_material = Material(
        course_id=course.id,
        type="link",
        title="待同步资料",
        url="https://example.com/source",
    )
    shared_question = Question(
        course_id=course.id,
        type="fill",
        stem="不应进入同步分母的共享题",
        options=[],
        answer="答案",
    )
    db_session.add_all([source_material, shared_question])
    db_session.flush()
    copy = Course(
        name="管理端共享题同步状态副本",
        created_by="T001",
        source_course_id=course.id,
    )
    db_session.add(copy)
    db_session.flush()
    db_session.add(Material(
        course_id=copy.id,
        type="link",
        title="已同步资料",
        url="https://example.com/copy",
        source_material_id=source_material.id,
    ))
    db_session.commit()

    sync_info = admin_public_course_service.get_course_sync_status(db_session, course)
    assert sync_info["sync_copy_count"] == 1
    assert sync_info["synced_material_count"] == 1
    assert sync_info["synced_question_count"] == 0
    assert sync_info["sync_status"] == "synced"


def test_shared_question_helpers_ignore_soft_deleted_questions_and_courses(db_session):
    """共享题库列表、统计和查重都只处理活跃题目及活跃课程。"""
    active_course = Course(name="活跃共享题课程", created_by="T001")
    deleted_course = Course(
        name="已删共享题课程",
        created_by="T001",
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add_all([active_course, deleted_course])
    db_session.flush()
    active = Question(
        course_id=active_course.id,
        type="fill",
        stem="共享题活跃题干",
        options=[],
        answer="活跃",
    )
    deleted_question = Question(
        course_id=active_course.id,
        type="fill",
        stem="共享题软删题干",
        options=[],
        answer="软删",
        deleted_at=datetime.now(timezone.utc),
    )
    deleted_course_question = Question(
        course_id=deleted_course.id,
        type="fill",
        stem="共享题已删课程题干",
        options=[],
        answer="课程软删",
    )
    db_session.add_all([active, deleted_question, deleted_course_question])
    db_session.commit()

    listed_ids = {item.id for item in list_all_questions(db_session).all()}
    assert active.id in listed_ids
    assert deleted_question.id not in listed_ids
    assert deleted_course_question.id not in listed_ids
    assert count_all_questions(db_session) == len(listed_ids)
    fingerprints = collect_question_fingerprints(db_session)
    assert all(fingerprint[1] != "共享题软删题干" for fingerprint in fingerprints)
    assert all(fingerprint[1] != "共享题已删课程题干" for fingerprint in fingerprints)
    assert find_duplicate_question(
        db_session,
        "fill",
        "共享题软删题干",
        [],
        "软删",
    ) is None
    assert find_duplicate_question(
        db_session,
        "fill",
        "共享题已删课程题干",
        [],
        "课程软删",
    ) is None
    assert find_same_stem_question(db_session, "共享题软删题干") is None
    assert find_same_stem_question(db_session, "共享题已删课程题干") is None


def test_admin_question_update_rejects_soft_deleted_question_and_course(db_session):
    """管理员不能更新软删除题目，也不能更新归属软删除课程的题目。"""
    course = Course(name="管理端题目软删课", created_by="admin", is_public=True)
    db_session.add(course)
    db_session.flush()
    deleted_question = Question(
        course_id=course.id,
        type="fill",
        stem="管理端已删题目",
        options=[],
        answer="答案",
        deleted_at=datetime.now(timezone.utc),
    )
    live_question = Question(
        course_id=course.id,
        type="fill",
        stem="管理端活跃题目",
        options=[],
        answer="答案",
    )
    db_session.add_all([deleted_question, live_question])
    db_session.commit()

    assert admin_public_course_service.update_public_question(
        db_session,
        deleted_question.id,
        {"stem": "不应更新"},
    ) is None
    course.deleted_at = datetime.now(timezone.utc)
    db_session.commit()
    assert admin_public_course_service.update_public_question(
        db_session,
        live_question.id,
        {"stem": "课程删除后不应更新"},
    ) is None


def test_list_announcements_hides_soft_deleted_assignment(db_session):
    """作业列表不返回软删除作业。"""
    from app.schemas.common import AuthUser
    from app.services.announcement_service import list_announcements

    teacher = AuthUser(id="T001", name="测试教师", role="teacher")
    before = {item["id"] for item in list_announcements(db_session, teacher)}
    ann = Announcement(
        course_id=1,
        teacher_id="T001",
        type="quiz",
        title="软删后应隐藏作业",
        question_ids=[1],
    )
    db_session.add(ann)
    db_session.commit()
    after_create = {item["id"] for item in list_announcements(db_session, teacher)}
    assert ann.id in after_create - before

    ann.deleted_at = datetime.now(timezone.utc)
    db_session.commit()
    after_delete = {item["id"] for item in list_announcements(db_session, teacher)}
    assert ann.id not in after_delete


def test_get_announcement_and_unread_count_reject_soft_deleted(db_session):
    """作业详情与未读数都忽略软删除作业。"""
    from app.schemas.common import AuthUser
    from app.services.announcement_service import get_announcement, unread_count

    cls = db_session.query(Class).filter(Class.created_by == "T001").first()
    ann = Announcement(
        course_id=cls.course_id,
        teacher_id="T001",
        type="quiz",
        title="未读软删作业",
        question_ids=[1],
    )
    db_session.add(ann)
    db_session.flush()
    db_session.add(AnnouncementClass(announcement_id=ann.id, class_id=cls.id))
    db_session.commit()

    student = AuthUser(id="2025001", name="测试学生", role="student")
    assert get_announcement(db_session, ann.id, student) is not None
    assert unread_count(db_session, "2025001") >= 1

    before_unread = unread_count(db_session, "2025001")
    ann.deleted_at = datetime.now(timezone.utc)
    db_session.commit()
    assert get_announcement(db_session, ann.id, student) is None
    assert get_announcement(db_session, ann.id, AuthUser(id="T001", name="t", role="teacher")) is None
    assert unread_count(db_session, "2025001") == before_unread - 1


def test_project_lists_hide_soft_deleted_projects(db_session):
    """作品列表/详情不返回软删除作品。"""
    from app.services.project_service import get_project, list_approved_projects, get_user_projects

    project = Project(
        title="待软删作品",
        author_id="2025001",
        course_id=1,
        status="approved",
        date="2026-07-15",
    )
    db_session.add(project)
    db_session.commit()
    assert get_project(db_session, project.id) is not None
    approved_ids = {p.id for p in list_approved_projects(db_session)[0]}
    user_ids = {p.id for p in get_user_projects(db_session, "2025001")[0]}
    assert project.id in approved_ids
    assert project.id in user_ids

    project.deleted_at = datetime.now(timezone.utc)
    db_session.commit()
    assert get_project(db_session, project.id) is None
    approved_ids = {p.id for p in list_approved_projects(db_session)[0]}
    user_ids = {p.id for p in get_user_projects(db_session, "2025001")[0]}
    assert project.id not in approved_ids
    assert project.id not in user_ids


def test_portfolio_hides_soft_deleted_projects_and_users(db_session):
    """成长档案不展示软删作品；软删用户返回空。"""
    from app.services.portfolio_service import get_portfolio

    project = Project(
        title="档案软删作品",
        author_id="2025001",
        course_id=1,
        status="approved",
        date="2026-07-15",
    )
    db_session.add(project)
    db_session.commit()
    data = get_portfolio(db_session, "2025001")
    assert data is not None
    assert any(item["id"] == project.id for item in data["projects"])

    project.deleted_at = datetime.now(timezone.utc)
    db_session.commit()
    data = get_portfolio(db_session, "2025001")
    assert all(item["id"] != project.id for item in data["projects"])

    user = db_session.get(User, "2025001")
    user.deleted_at = datetime.now(timezone.utc)
    db_session.commit()
    assert get_portfolio(db_session, "2025001") is None


def test_teacher_stats_and_lists_ignore_soft_deleted_resources(db_session):
    """教师统计与作品列表只统计活跃课程/班级/作品。"""
    from app.services.teacher_service import get_teacher_stats, list_all_projects

    before = get_teacher_stats(db_session, "T001")
    course = Course(name="软删统计课", created_by="T001")
    db_session.add(course)
    db_session.flush()
    cls = Class(name="软删统计班", course_id=course.id, created_by="T001")
    project = Project(
        title="软删统计作品",
        author_id="2025001",
        course_id=course.id,
        status="pending",
        date="2026-07-15",
    )
    db_session.add_all([cls, project])
    db_session.commit()

    mid = get_teacher_stats(db_session, "T001")
    assert mid["my_courses"] == before["my_courses"] + 1
    assert mid["pending_reviews"] == before["pending_reviews"] + 1
    project_ids = {p.id for p in list_all_projects(db_session, teacher_id="T001")[0]}
    assert project.id in project_ids

    course.deleted_at = datetime.now(timezone.utc)
    cls.deleted_at = datetime.now(timezone.utc)
    project.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    after = get_teacher_stats(db_session, "T001")
    assert after["my_courses"] == before["my_courses"]
    assert after["pending_reviews"] == before["pending_reviews"]
    project_ids = {p.id for p in list_all_projects(db_session, teacher_id="T001")[0]}
    assert project.id not in project_ids
