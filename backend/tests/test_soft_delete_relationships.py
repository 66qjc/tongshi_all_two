"""正式删除入口的软删除与关联保留回归测试。"""

import pytest

from app.core.exceptions import BusinessException
from app.models.entities import (
    Announcement,
    AnnouncementClass,
    AnnouncementRead,
    Class,
    Course,
    Material,
    MaterialPreview,
    Project,
    ProjectImage,
    ProjectLike,
    Question,
    QuizAttempt,
    TaskCompletion,
    User,
)
from app.schemas.common import AuthUser
from app.services.admin_public_course_service import (
    delete_public_course,
    delete_public_material,
    delete_public_question,
)
from app.services.announcement_service import delete_announcement
from app.services.class_service import delete_class
from app.services.material_service import delete_material
from app.services.project_service import delete_project


def _admin_operator() -> AuthUser:
    return AuthUser(id="admin", name="管理员", role="admin")


def test_class_delete_preserves_announcement_relationships(db_session):
    """删除空班级应保留班级、作业及已读/完成关联，并标记班级为已删除。"""
    cls = Class(name="待删除班级", course_id=1, created_by="T001")
    db_session.add(cls)
    db_session.flush()
    announcement = Announcement(
        course_id=1,
        teacher_id="T001",
        type="quiz",
        title="班级作业",
        question_ids=[1],
    )
    db_session.add(announcement)
    db_session.flush()
    db_session.add_all(
        [
            AnnouncementClass(announcement_id=announcement.id, class_id=cls.id),
            AnnouncementRead(user_id="2025001", announcement_id=announcement.id),
            TaskCompletion(user_id="2025001", announcement_id=announcement.id),
        ]
    )
    db_session.commit()

    assert delete_class(db_session, cls.id, "T001") is not None

    db_session.expire_all()
    assert db_session.get(Class, cls.id).deleted_at is not None
    assert db_session.get(Announcement, announcement.id).deleted_at is None
    assert db_session.query(AnnouncementClass).filter_by(announcement_id=announcement.id).count() == 1
    assert db_session.query(AnnouncementRead).filter_by(announcement_id=announcement.id).count() == 1
    assert db_session.query(TaskCompletion).filter_by(announcement_id=announcement.id).count() == 1


def test_announcement_delete_is_soft(db_session):
    """删除作业应保留主记录并写入删除时间。"""
    announcement = Announcement(
        course_id=1,
        teacher_id="T001",
        type="quiz",
        title="待删除作业",
        question_ids=[1],
    )
    db_session.add(announcement)
    db_session.commit()

    assert delete_announcement(db_session, announcement.id, "T001") is not None

    db_session.expire_all()
    stored = db_session.get(Announcement, announcement.id)
    assert stored is not None
    assert stored.deleted_at is not None
    assert stored.deleted_by == "T001"


def test_material_delete_preserves_preview(db_session):
    """删除资料应保留资料和预览元数据，文件权限由软删除状态控制。"""
    material = Material(course_id=1, type="pdf", title="待删除资料", url="/material.pdf")
    db_session.add(material)
    db_session.flush()
    preview = MaterialPreview(material_id=material.id, status="ready", summary="摘要")
    db_session.add(preview)
    db_session.commit()

    assert delete_material(db_session, material.id, "T001") is True

    db_session.expire_all()
    stored = db_session.get(Material, material.id)
    assert stored is not None
    assert stored.deleted_at is not None
    assert db_session.get(MaterialPreview, preview.id) is not None


def test_project_delete_preserves_images_and_likes(db_session):
    """删除作品应保留图片和点赞历史。"""
    project = Project(
        title="待删除作品",
        author_id="2025001",
        course_id=1,
        status="approved",
    )
    db_session.add(project)
    db_session.flush()
    image = ProjectImage(project_id=project.id, image_url="/project.png", sort_order=0)
    like = ProjectLike(project_id=project.id, user_id="2025002")
    db_session.add_all([image, like])
    db_session.commit()

    assert delete_project(db_session, project.id) is not None

    db_session.expire_all()
    stored = db_session.get(Project, project.id)
    assert stored is not None
    assert stored.deleted_at is not None
    assert db_session.get(ProjectImage, image.id) is not None
    assert db_session.get(ProjectLike, like.id) is not None


def test_teacher_delete_is_soft_and_keeps_account(db_session, client):
    """管理员强制删除教师时应保留教师账号，关联资源进入可恢复状态。"""
    admin_token = client.post(
        "/api/token", json={"id": "admin", "password": "Admin#2026"}
    ).json()["data"]["access_token"]

    response = client.delete(
        "/api/admin/teachers/T002?force=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    db_session.expire_all()
    teacher = db_session.get(User, "T002")
    assert teacher is not None
    assert teacher.deleted_at is not None
    assert db_session.query(Course).filter(Course.created_by == "T002").count() >= 1

    restore_response = client.post(
        "/api/admin/restore/users/T002",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert restore_response.status_code == 200
    assert restore_response.json()["code"] == 0
    db_session.expire_all()
    assert db_session.get(User, "T002").deleted_at is None


def test_public_course_delete_is_soft(db_session):
    """管理员删除公共课程时应保留课程并写入回收站状态。"""
    course = Course(name="待删除公共课程", created_by="admin", is_public=True)
    db_session.add(course)
    db_session.commit()

    assert delete_public_course(db_session, course.id) is True

    db_session.expire_all()
    stored = db_session.get(Course, course.id)
    assert stored is not None
    assert stored.deleted_at is not None


def test_public_material_delete_is_soft(db_session):
    """管理员删除公共资料时应保留资料记录。"""
    course = db_session.get(Course, 1)
    course.is_public = True
    material = Material(course_id=course.id, type="link", title="公共待删除资料", url="/public")
    db_session.add(material)
    db_session.commit()

    assert delete_public_material(db_session, material.id) is True

    db_session.expire_all()
    stored = db_session.get(Material, material.id)
    assert stored is not None
    assert stored.deleted_at is not None


def test_public_question_delete_rejects_referenced_question(db_session):
    """有作业引用的共享题目不得删除，答题记录和题目引用必须保留。"""
    course = db_session.get(Course, 1)
    course.is_public = True
    question = db_session.get(Question, 1)
    announcement = Announcement(
        course_id=course.id,
        teacher_id="T001",
        type="quiz",
        title="引用共享题",
        question_ids=[question.id],
    )
    db_session.add(announcement)
    db_session.flush()
    attempt = QuizAttempt(
        user_id="2025001",
        question_id=question.id,
        announcement_id=announcement.id,
        user_answer="B",
        is_correct=True,
    )
    db_session.add(attempt)
    db_session.commit()

    with pytest.raises(BusinessException) as exc_info:
        delete_public_question(db_session, question.id)

    assert exc_info.value.code == 400
    db_session.expire_all()
    assert db_session.get(Question, question.id) is not None
    assert db_session.get(Announcement, announcement.id).question_ids == [question.id]
    assert db_session.get(QuizAttempt, attempt.id) is not None
