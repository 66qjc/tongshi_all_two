"""学生端任务练习闭环回归测试。"""
from datetime import datetime, timedelta, timezone

from app.core.security import get_password_hash
from app.models.entities import (
    Class,
    Course,
    Question,
    QuizAttempt,
    StudentClassEnrollment,
    TaskCompletion,
    User,
)
from tests.conftest import auth_header


def _create_other_course_question(db_session, stem="共享题库跨课程题"):
    """创建一题归属其他教师课程的共享题，用来验证全站题库入口。"""
    other_course = db_session.query(Course).filter(Course.created_by == "T002").first()
    question = Question(
        type="choice",
        course_id=other_course.id,
        stem=stem,
        options=["A. 正确", "B. 错误"],
        answer="A",
        explanation="共享题库题目",
    )
    db_session.add(question)
    db_session.commit()
    db_session.refresh(question)
    return question


def _seed_assignment(client, db_session, teacher_token, title="任务练习", question_ids=None, **extra):
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    if question_ids is None:
        question = db_session.query(Question).filter(Question.course_id == course.id).first()
        question_ids = [question.id]
    payload = {
        "course_id": course.id,
        "class_ids": [1],
        "title": title,
        "question_ids": question_ids,
    }
    payload.update(extra)
    return client.post("/api/announcements", json=payload, headers=auth_header(teacher_token)).json()["data"]["id"]


def test_student_gets_only_accessible_active_assignment_questions(client, db_session, teacher_token, student_token):
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    question = db_session.query(Question).filter(Question.course_id == course.id).first()
    announcement_id = _seed_assignment(client, db_session, teacher_token, "任务题目读取", [question.id])

    resp = client.get(
        f"/api/announcements/{announcement_id}/questions",
        headers=auth_header(student_token),
    )
    data = resp.json()

    assert data["code"] == 0
    assert data["data"]["announcement"]["id"] == announcement_id
    assert data["data"]["announcement"]["course_id"] == course.id
    assert [item["id"] for item in data["data"]["questions"]] == [question.id]


def test_teacher_can_publish_assignment_with_shared_bank_question(client, db_session, teacher_token, student_token):
    """全站共享题库下，作业可以引用其他课程归属的题目。"""
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    shared_question = _create_other_course_question(db_session)

    create_resp = client.post(
        "/api/announcements",
        json={
            "course_id": course.id,
            "class_ids": [1],
            "title": "共享题库作业",
            "question_ids": [shared_question.id],
        },
        headers=auth_header(teacher_token),
    ).json()

    assert create_resp["code"] == 0
    announcement_id = create_resp["data"]["id"]

    questions_resp = client.get(
        f"/api/announcements/{announcement_id}/questions",
        headers=auth_header(student_token),
    ).json()
    submit_resp = client.post(
        "/api/quiz/submit",
        json={
            "question_id": shared_question.id,
            "user_answer": shared_question.answer,
            "announcement_id": announcement_id,
        },
        headers=auth_header(student_token),
    ).json()

    assert questions_resp["code"] == 0
    assert [item["id"] for item in questions_resp["data"]["questions"]] == [shared_question.id]
    assert submit_resp["code"] == 0


def test_other_student_cannot_get_assignment_questions(client, db_session, teacher_token):
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    question = db_session.query(Question).filter(Question.course_id == course.id).first()
    announcement_id = _seed_assignment(client, db_session, teacher_token, "无权任务题目读取", [question.id])
    other_token = client.post("/api/token", json={"id": "2025002", "password": "abc123"}).json()["data"]["access_token"]

    resp = client.get(
        f"/api/announcements/{announcement_id}/questions",
        headers=auth_header(other_token),
    )
    data = resp.json()

    assert data["code"] == 404
    assert "题目任务不存在" in data["message"]


def test_not_started_assignment_blocks_questions_submit_and_completion(client, db_session, teacher_token, student_token):
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    question = db_session.query(Question).filter(Question.course_id == course.id).first()
    future = (datetime.now(timezone(timedelta(hours=8))) + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    announcement_id = _seed_assignment(
        client,
        db_session,
        teacher_token,
        "未开始任务",
        [question.id],
        start_time=future,
    )

    questions_resp = client.get(
        f"/api/announcements/{announcement_id}/questions",
        headers=auth_header(student_token),
    ).json()
    submit_resp = client.post(
        "/api/quiz/submit",
        json={"question_id": question.id, "user_answer": question.answer, "announcement_id": announcement_id},
        headers=auth_header(student_token),
    ).json()
    complete_resp = client.post(
        f"/api/announcements/{announcement_id}/complete",
        headers=auth_header(student_token),
    ).json()

    assert questions_resp["code"] == 400
    assert "尚未开始" in questions_resp["message"]
    assert submit_resp["code"] == 400
    assert "尚未开始" in submit_resp["message"]
    assert complete_resp["code"] == 400
    assert "尚未开始" in complete_resp["message"]


def test_expired_assignment_blocks_submit_and_completion(client, db_session, teacher_token, student_token):
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    question = db_session.query(Question).filter(Question.course_id == course.id).first()
    past = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    announcement_id = _seed_assignment(
        client,
        db_session,
        teacher_token,
        "已截止任务",
        [question.id],
        end_time=past,
    )

    submit_resp = client.post(
        "/api/quiz/submit",
        json={"question_id": question.id, "user_answer": question.answer, "announcement_id": announcement_id},
        headers=auth_header(student_token),
    ).json()
    complete_resp = client.post(
        f"/api/announcements/{announcement_id}/complete",
        headers=auth_header(student_token),
    ).json()

    assert submit_resp["code"] == 400
    assert "已截止" in submit_resp["message"]
    assert complete_resp["code"] == 400
    assert "已截止" in complete_resp["message"]


def test_assignment_requires_all_questions_answered_before_completion(client, db_session, teacher_token, student_token):
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    first_question = db_session.query(Question).filter(Question.course_id == course.id).first()
    second_question = Question(
        type="choice",
        course_id=course.id,
        stem="2+2=?",
        options=["A. 3", "B. 4"],
        answer="B",
        explanation="基础加法",
    )
    db_session.add(second_question)
    db_session.commit()
    announcement_id = _seed_assignment(
        client,
        db_session,
        teacher_token,
        "必须答完全部题",
        [first_question.id, second_question.id],
    )

    empty_resp = client.post(
        f"/api/announcements/{announcement_id}/complete",
        headers=auth_header(student_token),
    ).json()
    client.post(
        "/api/quiz/submit",
        json={"question_id": first_question.id, "user_answer": first_question.answer, "announcement_id": announcement_id},
        headers=auth_header(student_token),
    )
    assert db_session.query(TaskCompletion).filter(
        TaskCompletion.announcement_id == announcement_id,
        TaskCompletion.user_id == "2025001",
    ).count() == 0
    partial_resp = client.post(
        f"/api/announcements/{announcement_id}/complete",
        headers=auth_header(student_token),
    ).json()
    client.post(
        "/api/quiz/submit",
        json={"question_id": second_question.id, "user_answer": second_question.answer, "announcement_id": announcement_id},
        headers=auth_header(student_token),
    )
    done_resp = client.post(
        f"/api/announcements/{announcement_id}/complete",
        headers=auth_header(student_token),
    ).json()
    done_again_resp = client.post(
        f"/api/announcements/{announcement_id}/complete",
        headers=auth_header(student_token),
    ).json()

    assert empty_resp["code"] == 400
    assert "完成全部题目" in empty_resp["message"]
    assert partial_resp["code"] == 400
    assert "完成全部题目" in partial_resp["message"]
    assert done_resp["code"] == 0
    assert done_again_resp["code"] == 0
    assert db_session.query(TaskCompletion).filter(
        TaskCompletion.announcement_id == announcement_id,
        TaskCompletion.user_id == "2025001",
    ).count() == 1


def test_assignment_submit_records_announcement_id(client, db_session, teacher_token, student_token):
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    question = db_session.query(Question).filter(Question.course_id == course.id).first()
    announcement_id = _seed_assignment(client, db_session, teacher_token, "答题关联任务", [question.id])

    resp = client.post(
        "/api/quiz/submit",
        json={"question_id": question.id, "user_answer": question.answer, "announcement_id": announcement_id},
        headers=auth_header(student_token),
    ).json()
    attempt = db_session.query(QuizAttempt).filter(QuizAttempt.id == resp["data"]["id"]).one()

    assert resp["code"] == 0
    assert attempt.announcement_id == announcement_id


def test_assignment_report_uses_latest_attempt_per_question_and_current_announcement_only(client, db_session, teacher_token, student_token):
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    question = db_session.query(Question).filter(Question.course_id == course.id).first()
    first_id = _seed_assignment(client, db_session, teacher_token, "当前任务", [question.id])
    second_id = _seed_assignment(client, db_session, teacher_token, "其它任务", [question.id])

    # 自由练习和其它任务答对同一道题，不应影响当前任务报告。
    client.post("/api/quiz/submit", json={"question_id": question.id, "user_answer": question.answer}, headers=auth_header(student_token))
    client.post("/api/quiz/submit", json={"question_id": question.id, "user_answer": question.answer, "announcement_id": second_id}, headers=auth_header(student_token))
    client.post("/api/quiz/submit", json={"question_id": question.id, "user_answer": "A", "announcement_id": first_id}, headers=auth_header(student_token))
    client.post("/api/quiz/submit", json={"question_id": question.id, "user_answer": question.answer, "announcement_id": first_id}, headers=auth_header(student_token))
    client.post(f"/api/announcements/{first_id}/complete", headers=auth_header(student_token))

    report = client.get(
        f"/api/announcements/{first_id}/completion-report",
        headers=auth_header(teacher_token),
    ).json()

    assert report["code"] == 0
    assert report["data"]["completed_students"]["items"][0]["score"] == 100
    assert report["data"]["completed_students"]["items"][0]["total_questions"] == 1


def test_student_free_practice_can_submit_shared_bank_question_and_stats_count_it(client, db_session, student_token):
    """学生在任一已加入课程入口自由练习时，可以作答全站共享题并纳入该入口统计。"""
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    public_course = Course(name="共享题库公共课", created_by="admin", is_public=True)
    db_session.add(public_course)
    db_session.flush()
    shared_question = Question(
        type="choice",
        course_id=public_course.id,
        stem="共享题库自由练习题",
        options=["A. 正确", "B. 错误"],
        answer="A",
        explanation="公共课程挂载的共享题库题目",
    )
    db_session.add(shared_question)
    db_session.commit()
    db_session.refresh(shared_question)

    submit_resp = client.post(
        "/api/quiz/submit",
        json={"question_id": shared_question.id, "user_answer": shared_question.answer},
        headers=auth_header(student_token),
    ).json()
    stats_resp = client.get(
        f"/api/quiz/stats/{course.id}",
        headers=auth_header(student_token),
    ).json()

    assert submit_resp["code"] == 0
    assert stats_resp["code"] == 0
    assert stats_resp["data"]["questions_done"] == 1
    assert stats_resp["data"]["accuracy"] == 100
