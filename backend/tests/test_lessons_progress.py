"""课时阅读和学习进度权限回归测试。"""

from app.models.entities import Course, CourseProgress, Lesson
from tests.conftest import auth_header


def _admin_token(client) -> str:
    """获取管理员 token。"""
    resp = client.post("/api/token", json={"id": "admin", "password": "Admin#2026"})
    return resp.json()["data"]["access_token"]


def _other_student_token(client) -> str:
    """获取未加入测试课程的学生 token。"""
    resp = client.post("/api/token", json={"id": "2025002", "password": "abc123"})
    return resp.json()["data"]["access_token"]


def _create_lesson(db_session, *, course_id: int = 1, status: str = "published", title: str = "第一课", content: str = "正文") -> Lesson:
    """创建课时测试数据。"""
    lesson = Lesson(
        course_id=course_id,
        title=title,
        content=content,
        status=status,
        sort_order=1,
    )
    db_session.add(lesson)
    db_session.commit()
    db_session.refresh(lesson)
    return lesson


def test_student_can_read_published_lessons_in_enrolled_course(client, db_session, student_token):
    """学生应能读取已加入课程下的已发布课时。"""
    published = _create_lesson(db_session, status="published", title="公开课时")
    _create_lesson(db_session, status="draft", title="草稿课时")

    list_resp = client.get("/api/courses/1/lessons", headers=auth_header(student_token)).json()
    detail_resp = client.get(f"/api/lessons/{published.id}", headers=auth_header(student_token)).json()

    assert list_resp["code"] == 0
    assert [item["title"] for item in list_resp["data"]] == ["公开课时"]
    assert detail_resp["code"] == 0
    assert detail_resp["data"]["id"] == published.id


def test_student_cannot_read_draft_or_unenrolled_lessons(client, db_session, student_token):
    """学生不能读取草稿课时，也不能读取未加入课程课时。"""
    draft = _create_lesson(db_session, status="draft", title="草稿课时")
    other_course = db_session.query(Course).filter(Course.created_by == "T002").first()
    other_lesson = _create_lesson(
        db_session,
        course_id=other_course.id,
        status="published",
        title="其它课程课时",
    )

    draft_resp = client.get(f"/api/lessons/{draft.id}", headers=auth_header(student_token)).json()
    other_list_resp = client.get(f"/api/courses/{other_course.id}/lessons", headers=auth_header(student_token)).json()
    other_detail_resp = client.get(f"/api/lessons/{other_lesson.id}", headers=auth_header(student_token)).json()

    assert draft_resp["code"] == 404
    assert other_list_resp["code"] == 404
    assert other_detail_resp["code"] == 404


def test_progress_requires_course_access_and_published_lesson(client, db_session, student_token):
    """学生学习进度只能写入自己有权限访问的已发布课时。"""
    published = _create_lesson(db_session, status="published", title="公开课时")
    draft = _create_lesson(db_session, status="draft", title="草稿课时")
    other_course = db_session.query(Course).filter(Course.created_by == "T002").first()
    other_lesson = _create_lesson(
        db_session,
        course_id=other_course.id,
        status="published",
        title="其它课程课时",
    )

    ok_resp = client.post(
        "/api/courses/1/progress",
        json={"lesson_id": published.id},
        headers=auth_header(student_token),
    ).json()
    draft_resp = client.post(
        "/api/courses/1/progress",
        json={"lesson_id": draft.id},
        headers=auth_header(student_token),
    ).json()
    other_resp = client.post(
        f"/api/courses/{other_course.id}/progress",
        json={"lesson_id": other_lesson.id},
        headers=auth_header(student_token),
    ).json()

    assert ok_resp["code"] == 0
    assert ok_resp["data"]["last_lesson_id"] == published.id
    assert draft_resp["code"] == 404
    assert other_resp["code"] == 404


def test_teacher_and_admin_can_manage_lessons_but_other_teacher_cannot(client, db_session, teacher_token, other_teacher_token):
    """教师只能管理自己的课程课时，管理员可以管理任意课程课时。"""
    admin_token = _admin_token(client)
    other_course = db_session.query(Course).filter(Course.created_by == "T002").first()
    lesson = _create_lesson(db_session, course_id=other_course.id, status="draft", title="待删课时")

    forbidden = client.get(f"/api/lessons/{lesson.id}", headers=auth_header(teacher_token)).json()
    allowed = client.get(f"/api/lessons/{lesson.id}", headers=auth_header(other_teacher_token)).json()
    admin_allowed = client.get(f"/api/lessons/{lesson.id}", headers=auth_header(admin_token)).json()

    assert forbidden["code"] == 403
    assert allowed["code"] == 0
    assert admin_allowed["code"] == 0


def test_delete_lesson_returns_deleted_id(client, db_session, teacher_token):
    """删除课时接口返回被删除课时 ID，保持前端契约稳定。"""
    lesson = _create_lesson(db_session)

    resp = client.delete(f"/api/lessons/{lesson.id}", headers=auth_header(teacher_token)).json()

    assert resp["code"] == 0
    assert resp["data"] == {"id": lesson.id}


def test_delete_lesson_clears_existing_progress_reference(client, db_session, teacher_token):
    """删除已被记录为学习进度的课时时，应先清空进度引用。"""
    lesson = _create_lesson(db_session)
    progress = CourseProgress(user_id="2025001", course_id=1, last_lesson_id=lesson.id)
    db_session.add(progress)
    db_session.commit()

    resp = client.delete(f"/api/lessons/{lesson.id}", headers=auth_header(teacher_token)).json()
    db_session.expire_all()
    saved_progress = db_session.query(CourseProgress).filter(CourseProgress.user_id == "2025001").first()

    assert resp["code"] == 0
    assert saved_progress is not None
    assert saved_progress.last_lesson_id is None


def test_lesson_content_is_sanitized_on_create_and_update(client, teacher_token):
    """课时富文本保存时应过滤危险标签和事件属性。"""
    create_resp = client.post(
        "/api/courses/1/lessons",
        json={
            "title": "安全测试",
            "content": '<p onclick="alert(1)">正文</p><script>alert(1)</script><a href="javascript:alert(1)">链接</a>',
            "status": "published",
        },
        headers=auth_header(teacher_token),
    ).json()

    lesson_id = create_resp["data"]["id"]
    update_resp = client.put(
        f"/api/lessons/{lesson_id}",
        json={"content": '<img src="/safe.png" onerror="alert(1)"><iframe src="x"></iframe>'},
        headers=auth_header(teacher_token),
    ).json()

    assert create_resp["code"] == 0
    assert "<script" not in create_resp["data"]["content"].lower()
    assert "onclick" not in create_resp["data"]["content"].lower()
    assert "javascript:" not in create_resp["data"]["content"].lower()
    assert update_resp["code"] == 0
    assert "onerror" not in update_resp["data"]["content"].lower()
    assert "<iframe" not in update_resp["data"]["content"].lower()


def test_lesson_content_is_sanitized_on_read_for_legacy_data(client, db_session, student_token):
    """历史脏数据被读取时也应清洗，避免直接进入前端 v-html。"""
    lesson = _create_lesson(
        db_session,
        content='<p onclick="alert(1)">正文</p><script>alert(1)</script>',
    )

    resp = client.get(f"/api/lessons/{lesson.id}", headers=auth_header(student_token)).json()

    assert resp["code"] == 0
    assert "onclick" not in resp["data"]["content"].lower()
    assert "<script" not in resp["data"]["content"].lower()
