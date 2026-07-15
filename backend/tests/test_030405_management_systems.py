"""03/04/05 管理能力回归测试。"""
from datetime import datetime, timezone
from app.models.entities import Announcement, AnnouncementClass, Course, Material, NotificationPreference, NotificationTemplate, PasswordResetRequest, Question, StudentNotification, User
from tests.conftest import auth_header


def _admin_token(client) -> str:
    """获取管理员 token。"""
    resp = client.post("/api/token", json={"id": "admin", "password": "Admin#2026"})
    return resp.json()["data"]["access_token"]


def test_course_delete_is_soft_deleted_and_can_restore(client, db_session, teacher_token):
    """课程删除应进入管理员回收站，恢复后重新可见。"""
    admin_token = _admin_token(client)

    delete_resp = client.delete("/api/courses/1", headers=auth_header(teacher_token)).json()
    deleted_resp = client.get("/api/admin/deleted/courses", headers=auth_header(admin_token)).json()
    list_resp = client.get("/api/courses", headers=auth_header(teacher_token)).json()

    assert delete_resp["code"] == 0
    assert deleted_resp["code"] == 0
    assert any(item["id"] == 1 and item["deleted_by"] == "T001" for item in deleted_resp["data"]["items"])
    assert all(item["id"] != 1 for item in list_resp["data"])

    restore_resp = client.post("/api/admin/restore/courses/1", headers=auth_header(admin_token)).json()
    restored = db_session.query(Course).filter(Course.id == 1).first()

    assert restore_resp["code"] == 0
    assert restored.deleted_at is None
    assert restored.deleted_by is None


def test_course_soft_delete_keeps_question_course_and_creator(
    client,
    db_session,
    teacher_token,
):
    """软删除课程时保留题目的原课程归属与创建人。"""
    admin_token = _admin_token(client)
    material = Material(course_id=1, type="pdf", title="测试资料", url="/x.pdf")
    question = Question(
        course_id=1,
        type="choice",
        stem="课程删除共享题",
        options=["A", "B"],
        answer="A",
        created_by="T001",
    )
    db_session.add_all([material, question])
    db_session.commit()
    question_id = question.id

    resp = client.delete("/api/courses/1", headers=auth_header(teacher_token)).json()
    deleted_classes = client.get("/api/admin/deleted/classes", headers=auth_header(admin_token)).json()
    deleted_materials = client.get("/api/admin/deleted/materials", headers=auth_header(admin_token)).json()
    deleted_questions = client.get("/api/admin/deleted/questions", headers=auth_header(admin_token)).json()
    db_session.expire_all()
    stored_question = db_session.get(Question, question_id)

    assert resp["code"] == 0
    assert any(item["id"] == 1 for item in deleted_classes["data"]["items"])
    assert any(item["id"] == material.id for item in deleted_materials["data"]["items"])
    assert all(item["id"] != question_id for item in deleted_questions["data"]["items"])
    assert stored_question.deleted_at is None
    assert stored_question.course_id == 1
    assert stored_question.created_by == "T001"

    restore_resp = client.post("/api/admin/restore/courses/1", headers=auth_header(admin_token)).json()
    db_session.expire_all()

    assert restore_resp["code"] == 0
    assert db_session.query(Course).filter(Course.id == 1).first().deleted_at is None
    assert db_session.query(Material).filter(Material.id == material.id).first().deleted_at is None
    restored_question = db_session.get(Question, question_id)
    assert restored_question.deleted_at is None
    assert restored_question.course_id == 1
    assert restored_question.created_by == "T001"
    assert db_session.query(Question).filter(Question.id == question_id).count() == 1


def test_course_with_questions_deletes_without_rehome_target(
    client,
    db_session,
    teacher_token,
    other_teacher_token,
):
    """没有承接课程时，删除课程也不得迁移或删除题目。"""
    assert client.delete("/api/courses/2", headers=auth_header(other_teacher_token)).json()["code"] == 0

    response = client.delete("/api/courses/1", headers=auth_header(teacher_token)).json()

    assert response["code"] == 0
    db_session.expire_all()
    assert db_session.get(Course, 1).deleted_at is not None
    question = db_session.get(Question, 1)
    assert question.course_id == 1
    assert question.deleted_at is None


def test_notification_batch_send_preferences_and_read_all(client, db_session, student_token):
    """扩展通知接口应支持偏好过滤、批量发送和全部已读。"""
    admin_token = _admin_token(client)

    pref_resp = client.put(
        "/api/notifications/preferences",
        json={"enable_course_update": False},
        headers=auth_header(student_token),
    ).json()
    skipped = client.post(
        "/api/notifications/send",
        json={
            "user_id": "2025001",
            "type": "course_material_added",
            "category": "course",
            "title": "新增资料",
            "content": "课程新增资料",
            "action_url": "/learn/course/1",
        },
        headers=auth_header(admin_token),
    ).json()
    batch = client.post(
        "/api/notifications/send-batch",
        json={
            "user_ids": ["2025001"],
            "type": "assignment_due_soon",
            "category": "assignment",
            "title": "作业即将截止",
            "content": "请及时完成作业",
            "priority": "high",
            "action_url": "/practice",
        },
        headers=auth_header(admin_token),
    ).json()
    list_resp = client.get("/api/notifications?category=assignment&unread_only=true", headers=auth_header(student_token)).json()
    read_all = client.post("/api/notifications/read-all", headers=auth_header(student_token)).json()
    unread = client.get("/api/notifications/unread-count", headers=auth_header(student_token)).json()

    assert pref_resp["code"] == 0
    assert skipped["code"] == 0
    assert skipped["data"]["sent_count"] == 0
    assert batch["code"] == 0
    assert batch["data"]["sent_count"] == 1
    assert list_resp["code"] == 0
    assert list_resp["data"][0]["category"] == "assignment"
    assert list_resp["data"][0]["action_url"] == "/practice"
    assert read_all["data"]["updated_count"] >= 1
    assert unread["data"]["count"] == 0


def test_teacher_notifications_are_limited_to_managed_students(client, teacher_token):
    """教师只能通知自己班级的学生，批量发送时越权目标应被跳过。"""
    own_student = client.post(
        "/api/notifications/send",
        json={
            "user_id": "2025001",
            "type": "system_notice",
            "title": "本班通知",
            "action_url": "/inbox",
        },
        headers=auth_header(teacher_token),
    ).json()
    other_student = client.post(
        "/api/notifications/send",
        json={
            "user_id": "2025002",
            "type": "system_notice",
            "title": "跨班通知",
            "action_url": "/inbox",
        },
        headers=auth_header(teacher_token),
    ).json()
    batch = client.post(
        "/api/notifications/send-batch",
        json={
            "user_ids": ["2025001", "2025002"],
            "type": "system_notice",
            "title": "批量通知",
            "action_url": "/inbox",
        },
        headers=auth_header(teacher_token),
    ).json()

    assert own_student["code"] == 0
    assert own_student["data"]["sent_count"] == 1
    assert other_student["code"] == 403
    assert batch["code"] == 0
    assert batch["data"]["sent_count"] == 1
    assert batch["data"]["skipped_count"] == 1


def test_notification_admin_can_reach_any_student_and_external_action_url_is_rejected(client):
    """管理员可通知任意学生，但通知跳转地址只能使用站内路径。"""
    admin_token = _admin_token(client)
    allowed = client.post(
        "/api/notifications/send",
        json={
            "user_id": "2025002",
            "type": "system_notice",
            "title": "管理员通知",
            "action_url": "/inbox",
        },
        headers=auth_header(admin_token),
    ).json()
    rejected = client.post(
        "/api/notifications/send",
        json={
            "user_id": "2025002",
            "type": "system_notice",
            "title": "外部跳转",
            "action_url": "https://example.com",
        },
        headers=auth_header(admin_token),
    )

    assert allowed["code"] == 0
    assert allowed["data"]["sent_count"] == 1
    assert rejected.status_code == 422 or rejected.json().get("code") in {400, 422}


def test_audit_logs_query_user_resource_and_export(client, teacher_token):
    """敏感操作应产生审计日志，并支持管理员查询与导出。"""
    admin_token = _admin_token(client)

    client.delete("/api/courses/1", headers=auth_header(teacher_token))

    list_resp = client.get("/api/admin/audit-logs?action=course.delete", headers=auth_header(admin_token)).json()
    user_resp = client.get("/api/admin/users/T001/audit-logs", headers=auth_header(admin_token)).json()
    resource_resp = client.get("/api/admin/resources/courses/1/audit-logs", headers=auth_header(admin_token)).json()
    export_resp = client.get("/api/admin/audit-logs/export", headers=auth_header(admin_token))

    assert list_resp["code"] == 0
    assert list_resp["data"]["total"] >= 1
    assert list_resp["data"]["items"][0]["action"] == "course.delete"
    assert list_resp["data"]["items"][0]["action_name"] == "删除课程"
    assert list_resp["data"]["items"][0]["resource_type_name"] == "课程"
    assert list_resp["data"]["items"][0]["status_name"] in {"成功", "失败", "错误"}
    assert user_resp["code"] == 0
    assert user_resp["data"]["total"] >= 1
    assert resource_resp["code"] == 0
    assert resource_resp["data"]["total"] >= 1
    assert export_resp.status_code == 200
    assert export_resp.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument")



def test_soft_deleted_user_cannot_login_and_deleted_course_hidden(client, db_session, teacher_token):
    """软删除用户不能登录，软删除课程不能从课程列表继续访问。"""
    user = db_session.query(User).filter(User.id == "2025001").first()
    user.deleted_at = datetime.now(timezone.utc)
    user.deleted_by = "admin"
    db_session.commit()

    login_resp = client.post("/api/token", json={"id": "2025001", "password": "Student#2026"}).json()
    assert login_resp["code"] != 0

    course = db_session.query(Course).filter(Course.id == 1).first()
    course.deleted_at = datetime.now(timezone.utc)
    course.deleted_by = "admin"
    db_session.commit()

    list_resp = client.get("/api/courses", headers=auth_header(teacher_token)).json()
    assert list_resp["code"] == 0
    assert all(item["id"] != 1 for item in list_resp["data"])



def test_audit_log_filters_status_string_resource_and_records_export(client, db_session):
    """审计日志应支持字符串资源 ID、状态筛选，并记录导出操作。"""
    from app.models.entities import AuditLog

    admin_token = _admin_token(client)
    db_session.add_all([
        AuditLog(user_id="admin", user_role="admin", action="user.password_reset", resource_type="users", resource_id="2025-ABC", resource_name="学生账号", status="failed", error_message="测试失败"),
        AuditLog(user_id="admin", user_role="admin", action="course.delete", resource_type="courses", resource_id="1", resource_name="测试课程", status="success"),
    ])
    db_session.commit()

    filtered = client.get(
        "/api/admin/audit-logs?resource_type=users&resource_id=2025-ABC&status=failed",
        headers=auth_header(admin_token),
    ).json()
    export_resp = client.get(
        "/api/admin/audit-logs/export?resource_type=users&resource_id=2025-ABC&status=failed",
        headers=auth_header(admin_token),
    )
    export_log = client.get(
        "/api/admin/audit-logs?action=audit_log.export&resource_type=audit_logs",
        headers=auth_header(admin_token),
    ).json()

    assert filtered["code"] == 0
    assert filtered["data"]["total"] == 1
    assert filtered["data"]["items"][0]["resource_id"] == "2025-ABC"
    assert filtered["data"]["items"][0]["status"] == "failed"
    assert export_resp.status_code == 200
    assert export_log["code"] == 0
    assert export_log["data"]["total"] >= 1
    assert export_log["data"]["items"][0]["details"]["export_count"] == 1


def test_audit_log_invalid_date_returns_business_error(client):
    """审计日志日期参数格式错误时应返回业务错误，而不是 500。"""
    admin_token = _admin_token(client)
    resp = client.get("/api/admin/audit-logs?start_date=not-a-date", headers=auth_header(admin_token)).json()

    assert resp["code"] == 400
    assert "日期格式错误" in resp["message"]



def test_admin_sensitive_user_operations_write_audit_logs(client, db_session):
    """教师账号管理和密码重置审批等敏感操作应写入审计日志。"""
    admin_token = _admin_token(client)

    create_resp = client.post(
        "/api/admin/teachers",
        json={"id": "T900", "name": "审计教师", "major": "测试学院"},
        headers=auth_header(admin_token),
    ).json()
    reset_resp = client.post("/api/admin/teachers/T900/reset-password", headers=auth_header(admin_token)).json()
    delete_resp = client.delete("/api/admin/teachers/T900", headers=auth_header(admin_token)).json()

    req = PasswordResetRequest(user_id="2025001", message="忘记密码", status="pending")
    db_session.add(req)
    db_session.commit()
    approve_resp = client.post(f"/api/admin/password-reset-requests/{req.id}/approve", headers=auth_header(admin_token)).json()

    create_log = client.get("/api/admin/audit-logs?action=user.create&resource_id=T900", headers=auth_header(admin_token)).json()
    reset_log = client.get("/api/admin/audit-logs?action=user.password_reset&resource_id=T900", headers=auth_header(admin_token)).json()
    delete_log = client.get("/api/admin/audit-logs?action=user.delete&resource_id=T900", headers=auth_header(admin_token)).json()
    approve_log = client.get("/api/admin/audit-logs?action=user.password_reset&resource_id=2025001", headers=auth_header(admin_token)).json()

    assert create_resp["code"] == 0
    assert reset_resp["code"] == 0
    assert delete_resp["code"] == 0
    assert approve_resp["code"] == 0
    assert create_log["data"]["total"] == 1
    assert reset_log["data"]["total"] == 1
    assert delete_log["data"]["total"] == 1
    assert approve_log["data"]["total"] == 1
    assert approve_log["data"]["items"][0]["details"]["result"] == "approved"


def test_admin_teacher_password_reset_invalidates_existing_token(client, teacher_token):
    """管理员重置教师密码后，该教师已有 JWT 必须立即失效。"""
    admin_token = _admin_token(client)

    reset = client.post(
        "/api/admin/teachers/T001/reset-password",
        headers=auth_header(admin_token),
    ).json()
    current = client.get("/api/me", headers=auth_header(teacher_token)).json()

    assert reset["code"] == 0
    assert current["code"] == 401


def test_admin_reset_approval_invalidates_existing_token(client, db_session, student_token):
    """管理员审批人工重置后，目标学生已有 JWT 必须立即失效。"""
    admin_token = _admin_token(client)
    request = PasswordResetRequest(user_id="2025001", message="忘记密码", status="pending")
    db_session.add(request)
    db_session.commit()

    approved = client.post(
        f"/api/admin/password-reset-requests/{request.id}/approve",
        headers=auth_header(admin_token),
    ).json()
    current = client.get("/api/me", headers=auth_header(student_token)).json()

    assert approved["code"] == 0
    assert current["code"] == 401



def test_assignment_due_soon_reminder_job_respects_preferences_and_deduplicates(db_session):
    """作业截止提醒应尊重偏好并按公告去重。"""
    from app.services.notification_service import send_assignment_due_soon_reminders

    now = datetime.now(timezone.utc)
    ann = Announcement(
        course_id=1,
        teacher_id="T001",
        type="homework",
        title="期末作业",
        content="",
        question_ids=[1],
        start_time=now,
        end_time=now + __import__("datetime").timedelta(hours=12),
    )
    db_session.add(ann)
    db_session.flush()
    db_session.add(AnnouncementClass(announcement_id=ann.id, class_id=1))
    db_session.add(NotificationPreference(user_id="2025001", enable_assignment_due=True))
    db_session.commit()

    first = send_assignment_due_soon_reminders(db_session, now=now)
    second = send_assignment_due_soon_reminders(db_session, now=now)
    notifications = db_session.query(StudentNotification).filter(
        StudentNotification.user_id == "2025001",
        StudentNotification.type == "assignment_due_soon",
        StudentNotification.action_url == f"/practice/announcement/{ann.id}",
    ).all()

    assert first["sent_count"] == 1
    assert first["skipped_count"] == 0
    assert second["sent_count"] == 0
    assert second["skipped_count"] == 1
    assert len(notifications) == 1
    assert notifications[0].category == "assignment"
    assert notifications[0].priority == "high"
    assert "???" not in notifications[0].title
    assert "???" not in notifications[0].content
    assert notifications[0].title == "作业《期末作业》即将截止"
    assert "请及时完成作业" in notifications[0].content
    assert notifications[0].extra_data["announcement_id"] == ann.id


def test_notification_templates_seed_render_and_cleanup_expired_read(db_session):
    """通知模板应可初始化、渲染变量，并可清理已读过期通知。"""
    from app.services.notification_service import (
        cleanup_read_expired_notifications,
        ensure_default_notification_templates,
        list_notifications,
        render_template,
        unread_count,
    )

    created = ensure_default_notification_templates(db_session)
    template = db_session.query(NotificationTemplate).filter_by(code="assignment_due_soon").first()

    assert created >= 1
    assert template is not None
    rendered = render_template(template, {"title": "期末作业", "announcement_id": "123"})
    assert rendered["title"] == "作业《期末作业》即将截止"
    assert rendered["action_url"] == "/practice/announcement/123"

    expired = StudentNotification(
        user_id="2025001",
        type="system_notice",
        title="旧通知",
        content="已读且过期",
        category="system",
        is_read=True,
        expires_at=datetime.now(timezone.utc) - __import__("datetime").timedelta(days=1),
    )
    unread_expired = StudentNotification(
        user_id="2025001",
        type="system_notice",
        title="未读旧通知",
        content="未读不清理",
        category="system",
        is_read=False,
        expires_at=datetime.now(timezone.utc) - __import__("datetime").timedelta(days=1),
    )
    db_session.add_all([expired, unread_expired])
    db_session.commit()

    assert list_notifications(db_session, "2025001") == []
    assert unread_count(db_session, "2025001") == 0

    result = cleanup_read_expired_notifications(db_session, now=datetime.now(timezone.utc))

    assert result["deleted_count"] == 1
    assert db_session.get(StudentNotification, expired.id) is None
    assert db_session.get(StudentNotification, unread_expired.id) is not None
