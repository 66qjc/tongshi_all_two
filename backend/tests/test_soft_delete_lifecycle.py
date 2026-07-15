"""软删除生命周期的正式服务与管理员路由回归测试。"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.core.exceptions import BusinessException
from app.models.entities import (
    Announcement,
    AnnouncementClass,
    AnnouncementRead,
    Class,
    Course,
    Material,
    MaterialPreview,
    PasswordResetRequest,
    Project,
    ProjectImage,
    ProjectLike,
    Question,
    QuizAttempt,
    StoredFile,
    StudentClassEnrollment,
    TaskCompletion,
    User,
)
from app.schemas.common import AuthUser
from app.services.soft_delete_service import purge_resource, restore_resource, soft_delete
from tests.conftest import auth_header


def _admin_token(client) -> str:
    response = client.post("/api/token", json={"id": "admin", "password": "Admin#2026"})
    return response.json()["data"]["access_token"]


def test_course_restore_only_restores_same_batch_children_and_never_touches_questions(client, db_session):
    """统一课程删除服务只恢复同一批子资源，题目始终不受影响。"""
    admin_token = _admin_token(client)
    operator = AuthUser(id="T001", name="测试教师", role="teacher")
    course = Course(name="软删批次课程", created_by=operator.id)
    db_session.add(course)
    db_session.flush()

    cls = Class(name="软删批次班", course_id=course.id, created_by=operator.id)
    material = Material(course_id=course.id, type="link", title="同批资料", url="https://example.com/batch")
    separately_deleted_material = Material(
        course_id=course.id,
        type="link",
        title="独立删除资料",
        url="https://example.com/separate",
    )
    question = Question(
        course_id=course.id,
        type="choice",
        stem="课程删除不得移动我",
        options=["A", "B"],
        answer="A",
        created_by=operator.id,
    )
    db_session.add_all([cls, material, separately_deleted_material, question])
    db_session.flush()
    announcement = Announcement(
        class_id=cls.id,
        course_id=course.id,
        teacher_id=operator.id,
        type="quiz",
        title="同批作业",
        question_ids=[question.id],
    )
    db_session.add(announcement)
    db_session.commit()

    soft_delete(db_session, separately_deleted_material, operator, action="material.delete")
    db_session.commit()
    soft_delete(db_session, course, operator, action="course.delete")
    db_session.commit()
    db_session.expire_all()

    deleted_course = db_session.get(Course, course.id)
    deleted_cls = db_session.get(Class, cls.id)
    deleted_material = db_session.get(Material, material.id)
    deleted_announcement = db_session.get(Announcement, announcement.id)
    separately_deleted = db_session.get(Material, separately_deleted_material.id)
    untouched_question = db_session.get(Question, question.id)

    assert deleted_course is not None and deleted_course.deleted_at is not None
    assert deleted_cls is not None and deleted_cls.deleted_at == deleted_course.deleted_at
    assert deleted_material is not None and deleted_material.deleted_at == deleted_course.deleted_at
    assert deleted_announcement is not None and deleted_announcement.deleted_at == deleted_course.deleted_at
    assert deleted_cls is not None and deleted_cls.deleted_by == operator.id
    assert deleted_material is not None and deleted_material.deleted_by == operator.id
    assert deleted_announcement is not None and deleted_announcement.deleted_by == operator.id
    assert separately_deleted is not None and separately_deleted.deleted_at is not None
    assert untouched_question is not None and untouched_question.deleted_at is None
    assert untouched_question.course_id == course.id

    restored = client.post(
        f"/api/admin/restore/courses/{course.id}",
        headers=auth_header(admin_token),
    ).json()
    db_session.expire_all()

    assert restored["code"] == 0
    assert restored["data"]["恢复子资源数量"] == 3
    assert db_session.get(Course, course.id).deleted_at is None
    assert db_session.get(Class, cls.id).deleted_at is None
    assert db_session.get(Material, material.id).deleted_at is None
    assert db_session.get(Announcement, announcement.id).deleted_at is None
    assert db_session.get(Material, separately_deleted_material.id).deleted_at is not None
    assert db_session.get(Question, question.id).deleted_at is None
    assert db_session.get(Question, question.id).course_id == course.id


def test_teacher_string_id_restores_and_purge_is_rejected(client, db_session, teacher_token):
    """管理员软删教师保留关联事实，字符串 ID 可恢复且公开 purge 被拒绝。"""
    admin_token = _admin_token(client)
    teacher = User(id="TDEL", name="待删教师", hashed_password="hash", role="teacher")
    db_session.add(teacher)
    db_session.flush()
    course = Course(name="待删教师课程", created_by=teacher.id)
    db_session.add(course)
    db_session.flush()
    cls = Class(name="待删教师班", course_id=course.id, created_by=teacher.id)
    project = Project(title="待删教师作品", author_id=teacher.id, course_id=course.id)
    announcement = Announcement(course_id=course.id, teacher_id=teacher.id, type="quiz", title="待删教师作业")
    file = StoredFile(object_key="teacher/file", original_name="teacher.txt", stored_name="teacher.txt", created_by=teacher.id)
    db_session.add_all([cls, project, announcement, file])
    db_session.flush()
    enrollment = StudentClassEnrollment(user_id=teacher.id, class_id=cls.id)
    attempt = QuizAttempt(user_id=teacher.id, question_id=1, announcement_id=announcement.id, user_answer="A")
    reset_request = PasswordResetRequest(user_id="2025001", message="请重置", resolved_by=teacher.id)
    db_session.add_all([enrollment, attempt, reset_request])
    db_session.commit()

    deleted = client.delete("/api/admin/teachers/TDEL", headers=auth_header(admin_token))
    assert deleted.status_code == 200
    assert deleted.json()["code"] == 0
    db_session.expire_all()

    deleted_teacher = db_session.get(User, teacher.id)
    assert deleted_teacher is not None and deleted_teacher.deleted_at is not None
    assert db_session.get(Course, course.id) is not None
    assert db_session.get(Class, cls.id) is not None
    assert db_session.get(Project, project.id) is not None
    assert db_session.get(Announcement, announcement.id) is not None
    assert db_session.get(StoredFile, file.id) is not None
    assert db_session.get(StudentClassEnrollment, enrollment.id) is not None
    assert db_session.get(QuizAttempt, attempt.id) is not None
    assert db_session.get(PasswordResetRequest, reset_request.id).resolved_by == teacher.id

    teachers = client.get("/api/admin/teachers", headers=auth_header(admin_token)).json()
    assert teachers["code"] == 0
    assert all(item["id"] != teacher.id for item in teachers["data"])

    teacher_recycle = client.get("/api/admin/deleted/users", headers=auth_header(teacher_token)).json()
    recycle = client.get("/api/admin/deleted/users", headers=auth_header(admin_token)).json()
    purge = client.delete("/api/admin/purge/users/TDEL", headers=auth_header(admin_token)).json()
    assert teacher_recycle["code"] == 403
    assert any(item["id"] == teacher.id for item in recycle["data"]["items"])
    assert purge["code"] == 403
    assert purge["message"] == "资源仍在保留期，不能提前彻底删除"

    restored = client.post("/api/admin/restore/users/TDEL", headers=auth_header(admin_token))
    assert restored.status_code == 200
    assert restored.json()["code"] == 0
    db_session.expire_all()
    assert db_session.get(User, teacher.id).deleted_at is None


def test_question_referenced_by_active_assignment_cannot_be_soft_deleted(db_session):
    """题目仍被未删除作业使用时，统一删除服务必须返回中文 400。"""
    operator = AuthUser(id="admin", name="管理员", role="admin")
    course = Course(name="题目引用课程", created_by=operator.id, is_public=True)
    db_session.add(course)
    db_session.flush()
    question = Question(
        course_id=course.id,
        type="choice",
        stem="仍被作业引用的题目",
        options=["A", "B"],
        answer="A",
        created_by=operator.id,
    )
    db_session.add(question)
    db_session.flush()
    assignment = Announcement(
        course_id=course.id,
        teacher_id="T001",
        type="quiz",
        title="引用题目的作业",
        question_ids=[question.id],
    )
    db_session.add(assignment)
    db_session.commit()

    with pytest.raises(BusinessException) as exc_info:
        soft_delete(db_session, question, operator, action="question.delete")

    assert exc_info.value.code == 400
    assert exc_info.value.message == "题目已被未删除作业使用，不能删除"
    db_session.expire_all()
    assert db_session.get(Question, question.id).deleted_at is None
    assert db_session.get(Announcement, assignment.id).question_ids == [question.id]


@pytest.mark.parametrize(
    "question_ids",
    [
        1,
        "1",
        {"id": 1},
        [{"id": 1}],
        [None],
        [""],
        [{}],
        0,
        [True],
    ],
)
def test_question_with_malformed_active_assignment_data_cannot_be_soft_deleted(db_session, question_ids):
    """活跃作业的题目数据不是列表时，保守拒绝删除题目且不影响答题事实。"""
    operator = AuthUser(id="admin", name="管理员", role="admin")
    course = Course(name="异常题目数据课程", created_by=operator.id)
    db_session.add(course)
    db_session.flush()
    question = Question(
        course_id=course.id,
        type="choice",
        stem="题目数据异常时不得删除",
        options=["A", "B"],
        answer="A",
        created_by=operator.id,
    )
    db_session.add(question)
    db_session.flush()
    assignment = Announcement(
        course_id=course.id,
        teacher_id="T001",
        type="quiz",
        title="题目数据异常的作业",
        question_ids=question_ids,
    )
    db_session.add(assignment)
    db_session.flush()
    attempt = QuizAttempt(
        user_id="2025001",
        question_id=question.id,
        announcement_id=assignment.id,
        user_answer="A",
    )
    db_session.add(attempt)
    db_session.commit()

    with pytest.raises(BusinessException) as exc_info:
        soft_delete(db_session, question, operator, action="question.delete")

    assert exc_info.value.code == 400
    assert exc_info.value.message == "作业题目数据格式异常，不能删除题目"
    db_session.expire_all()
    assert db_session.get(Question, question.id).deleted_at is None
    assert db_session.get(QuizAttempt, attempt.id) is not None


def test_question_with_raw_invalid_assignment_json_cannot_be_soft_deleted(db_session):
    """历史作业题目 JSON 损坏时，题目删除必须返回业务错误且保留答题事实。"""
    operator = AuthUser(id="admin", name="管理员", role="admin")
    course = Course(name="原始 JSON 损坏课程", created_by=operator.id)
    db_session.add(course)
    db_session.flush()
    question = Question(
        course_id=course.id,
        type="choice",
        stem="原始 JSON 损坏时不允许删除",
        options=["A", "B"],
        answer="A",
        created_by=operator.id,
    )
    assignment = Announcement(
        course_id=course.id,
        teacher_id="T001",
        type="quiz",
        title="原始 JSON 损坏作业",
        question_ids=[question.id],
    )
    db_session.add_all([question, assignment])
    db_session.flush()
    attempt = QuizAttempt(
        user_id="2025001",
        question_id=question.id,
        announcement_id=assignment.id,
        user_answer="A",
    )
    db_session.add(attempt)
    db_session.commit()
    db_session.execute(
        text("UPDATE announcements SET question_ids = :question_ids WHERE id = :assignment_id"),
        {"question_ids": "{无效 JSON", "assignment_id": assignment.id},
    )
    db_session.commit()

    with pytest.raises(BusinessException) as exc_info:
        soft_delete(db_session, question, operator, action="question.delete")

    assert exc_info.value.code == 400
    assert exc_info.value.message == "作业题目数据格式异常，不能删除题目"
    db_session.expire_all()
    assert db_session.get(Question, question.id).deleted_at is None
    assert db_session.get(QuizAttempt, attempt.id) is not None


def test_question_with_raw_null_assignment_data_cannot_be_soft_deleted(db_session):
    """历史作业题目字段为 SQL NULL 时也必须保守拒绝删除题目。"""
    operator = AuthUser(id="admin", name="管理员", role="admin")
    course = Course(name="原始空题目数据课程", created_by=operator.id)
    db_session.add(course)
    db_session.flush()
    question = Question(
        course_id=course.id,
        type="choice",
        stem="原始空值时不允许删除",
        options=["A", "B"],
        answer="A",
        created_by=operator.id,
    )
    assignment = Announcement(
        course_id=course.id,
        teacher_id="T001",
        type="quiz",
        title="原始空值作业",
        question_ids=[question.id],
    )
    db_session.add_all([question, assignment])
    db_session.flush()
    attempt = QuizAttempt(
        user_id="2025001",
        question_id=question.id,
        announcement_id=assignment.id,
        user_answer="A",
    )
    db_session.add(attempt)
    db_session.commit()
    db_session.execute(
        text("UPDATE announcements SET question_ids = NULL WHERE id = :assignment_id"),
        {"assignment_id": assignment.id},
    )
    db_session.commit()

    with pytest.raises(BusinessException) as exc_info:
        soft_delete(db_session, question, operator, action="question.delete")

    assert exc_info.value.code == 400
    assert exc_info.value.message == "作业题目数据格式异常，不能删除题目"
    db_session.expire_all()
    assert db_session.get(Question, question.id).deleted_at is None
    assert db_session.get(QuizAttempt, attempt.id) is not None


def test_soft_deleted_teacher_cannot_reset_password_or_query_dependencies(client, db_session):
    """已删除教师只能由回收站处理，管理入口不得改密或读取关联数据。"""
    admin_token = _admin_token(client)
    teacher = db_session.get(User, "T001")
    password_before = teacher.hashed_password
    token_version_before = teacher.token_version
    needs_password_change_before = teacher.needs_password_change

    deleted = client.delete("/api/admin/teachers/T001", headers=auth_header(admin_token)).json()
    assert deleted["code"] == 0

    reset = client.post(
        "/api/admin/teachers/T001/reset-password",
        headers=auth_header(admin_token),
    ).json()
    dependencies = client.get(
        "/api/admin/teachers/T001/dependencies",
        headers=auth_header(admin_token),
    ).json()

    assert reset["code"] == 404
    assert dependencies["code"] == 404
    db_session.expire_all()
    deleted_teacher = db_session.get(User, "T001")
    assert deleted_teacher.deleted_at is not None
    assert deleted_teacher.hashed_password == password_before
    assert deleted_teacher.token_version == token_version_before
    assert deleted_teacher.needs_password_change == needs_password_change_before


def test_deleted_assignment_with_malformed_question_data_does_not_block_question_deletion(db_session):
    """已删除作业的异常题目数据不参与题目删除校验。"""
    operator = AuthUser(id="admin", name="管理员", role="admin")
    course = Course(name="已删除异常作业课程", created_by=operator.id)
    db_session.add(course)
    db_session.flush()
    question = Question(
        course_id=course.id,
        type="choice",
        stem="已删除异常作业不阻止删除",
        options=["A", "B"],
        answer="A",
        created_by=operator.id,
    )
    assignment = Announcement(
        course_id=course.id,
        teacher_id="T001",
        type="quiz",
        title="已删除的异常作业",
        question_ids={"id": 1},
    )
    db_session.add_all([question, assignment])
    db_session.flush()
    soft_delete(db_session, assignment, operator, action="announcement.delete")
    db_session.commit()

    soft_delete(db_session, question, operator, action="question.delete")
    db_session.commit()
    db_session.expire_all()

    assert db_session.get(Question, question.id).deleted_at is not None


def test_restore_resource_rejects_malformed_numeric_id(db_session):
    """整型资源的恢复入口应拒绝非数字 ID。"""
    operator = AuthUser(id="admin", name="管理员", role="admin")

    with pytest.raises(BusinessException) as exc_info:
        restore_resource(db_session, "courses", "bad-id", operator)

    assert exc_info.value.code == 400
    assert exc_info.value.message == "资源 ID 格式不正确"


def test_purge_resource_is_rejected_by_service_and_keeps_resource(db_session):
    """保留期内即使直接调用服务也不能物理删除资源。"""
    operator = AuthUser(id="admin", name="管理员", role="admin")
    course = Course(name="禁止提前清理课程", created_by=operator.id)
    db_session.add(course)
    db_session.commit()

    with pytest.raises(BusinessException) as exc_info:
        purge_resource(db_session, "courses", str(course.id), operator)

    assert exc_info.value.code == 403
    assert db_session.get(Course, course.id) is not None


def test_teacher_and_student_cannot_restore_or_purge_resources(client, teacher_token, student_token):
    """回收站恢复和提前清理仅管理员可调用。"""
    for token in (teacher_token, student_token):
        restore = client.post("/api/admin/restore/courses/1", headers=auth_header(token)).json()
        purge = client.delete("/api/admin/purge/courses/1", headers=auth_header(token)).json()
        assert restore["code"] == 403
        assert purge["code"] == 403


def test_delete_entry_services_soft_delete_resources_and_preserve_related_facts(db_session):
    """班级、作业、资料和作品删除入口只软删主体，保留所有关联事实。"""
    from app.services.announcement_service import delete_announcement
    from app.services.class_service import delete_class
    from app.services.material_service import delete_material
    from app.services.project_service import delete_project

    cls = Class(name="待删班级", course_id=1, created_by="T001")
    announcement = Announcement(
        class_id=None,
        course_id=1,
        teacher_id="T001",
        type="quiz",
        title="待删作业",
        question_ids=[1],
    )
    file = StoredFile(
        object_key="materials/to-delete.pdf",
        original_name="待删资料.pdf",
        stored_name="to-delete.pdf",
        created_by="T001",
    )
    material = Material(
        course_id=1,
        type="pdf",
        title="待删资料",
        url="/materials/to-delete.pdf",
    )
    project = Project(title="待删作品", author_id="2025001", course_id=1)
    db_session.add_all([cls, announcement, file, material, project])
    db_session.flush()

    announcement_class = AnnouncementClass(announcement_id=announcement.id, class_id=cls.id)
    announcement_read = AnnouncementRead(user_id="2025001", announcement_id=announcement.id)
    completion = TaskCompletion(announcement_id=announcement.id, user_id="2025001")
    material.file_id = file.id
    preview = MaterialPreview(material_id=material.id, status="ready")
    image = ProjectImage(project_id=project.id, image_url="/projects/to-delete.png")
    like = ProjectLike(project_id=project.id, user_id="2025001")
    db_session.add_all([announcement_class, announcement_read, completion, preview, image, like])
    db_session.commit()

    assert delete_class(db_session, cls.id, "T001") is not None
    assert db_session.get(Class, cls.id).deleted_at is not None
    assert db_session.get(AnnouncementClass, announcement_class.id) is not None
    assert db_session.get(AnnouncementRead, announcement_read.id) is not None
    assert db_session.get(TaskCompletion, completion.id) is not None
    assert db_session.get(Announcement, announcement.id).deleted_at is None

    assert delete_announcement(db_session, announcement.id, "T001") is not None
    assert db_session.get(Announcement, announcement.id).deleted_at is not None
    assert db_session.get(AnnouncementClass, announcement_class.id) is not None
    assert db_session.get(AnnouncementRead, announcement_read.id) is not None
    assert db_session.get(TaskCompletion, completion.id) is not None

    assert delete_material(db_session, material.id, "T001") is True
    assert db_session.get(Material, material.id).deleted_at is not None
    assert db_session.get(StoredFile, file.id) is not None
    assert db_session.get(MaterialPreview, preview.id) is not None

    assert delete_project(db_session, project.id, "T001") is not None
    assert db_session.get(Project, project.id).deleted_at is not None
    assert db_session.get(ProjectImage, image.id) is not None
    assert db_session.get(ProjectLike, like.id) is not None


def test_question_delete_entry_preserves_attempt_and_assignment_question_ids(db_session):
    """题目删除入口对活跃作业返回中文 400，成功时不破坏答题和作业事实。"""
    from app.services.question_service import delete_question

    question = Question(
        course_id=1,
        type="choice",
        stem="待删题目",
        options=["A", "B"],
        answer="A",
        created_by="T001",
    )
    db_session.add(question)
    db_session.flush()
    assignment = Announcement(
        course_id=1,
        teacher_id="T001",
        type="quiz",
        title="活跃引用作业",
        question_ids=[question.id],
    )
    db_session.add(assignment)
    db_session.flush()
    attempt = QuizAttempt(
        user_id="2025001",
        question_id=question.id,
        announcement_id=assignment.id,
        user_answer="A",
    )
    db_session.add(attempt)
    db_session.commit()

    with pytest.raises(BusinessException) as exc_info:
        delete_question(db_session, question.id, "T001")
    assert exc_info.value.code == 400
    assert exc_info.value.message == "题目已被未删除作业使用，不能删除"
    assert db_session.get(Question, question.id).deleted_at is None
    assert db_session.get(QuizAttempt, attempt.id) is not None
    assert db_session.get(Announcement, assignment.id).question_ids == [question.id]

    assignment.deleted_at = db_session.get(Course, 1).created_at
    assignment.deleted_by = "T001"
    db_session.commit()

    assert delete_question(db_session, question.id, "T001") is True
    assert db_session.get(Question, question.id).deleted_at is not None
    assert db_session.get(QuizAttempt, attempt.id) is not None
    assert db_session.get(Announcement, assignment.id).question_ids == [question.id]


def test_course_delete_entry_does_not_move_or_soft_delete_questions(db_session):
    """课程删除只处理固定子资源，题目归属和软删除状态保持不变。"""
    from app.services.question_service import delete_course

    question = Question(
        course_id=1,
        type="choice",
        stem="课程删除后仍归原课程",
        options=["A", "B"],
        answer="A",
        created_by="T001",
    )
    db_session.add(question)
    db_session.commit()

    assert delete_course(db_session, 1, "T001") is not None
    db_session.expire_all()

    stored_question = db_session.get(Question, question.id)
    assert stored_question.course_id == 1
    assert stored_question.deleted_at is None
