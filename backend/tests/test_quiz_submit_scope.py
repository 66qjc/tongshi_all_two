"""自由练习提交范围与题目可见性测试。"""

from datetime import datetime, timezone

import pytest

from app.core.exceptions import BusinessException
from app.models.entities import (
    Announcement,
    AnnouncementClass,
    Class,
    Course,
    Question,
    StudentClassEnrollment,
    User,
)
from app.services.quiz_service import submit_answer
from app.services.question_service import get_course_questions, can_view_course_questions


def _add_question(db, course_id: int, stem: str, answer: str = "A") -> Question:
    question = Question(
        type="choice",
        course_id=course_id,
        stem=stem,
        options=["A. 1", "B. 2"],
        answer=answer,
        explanation=f"{stem}解析",
    )
    db.add(question)
    db.flush()
    return question


def test_free_practice_allows_joined_course_question(db_session):
    """学生可提交自己已加入课程下的活跃题目。"""
    course = db_session.query(Course).filter(Course.name == "测试课程").first()
    question = db_session.query(Question).filter(Question.course_id == course.id).first()

    result = submit_answer(db_session, "2025001", question.id, "B", role="student")
    assert result["is_correct"] is True
    assert result["correct_answer"] == "B"


def test_free_practice_blocks_other_private_course_question(db_session):
    """学生不能提交其它教师私有课程下的题目以探测答案。"""
    other_course = db_session.query(Course).filter(Course.name == "其它课程").first()
    secret = _add_question(db_session, other_course.id, "私有秘密题", answer="A")
    db_session.commit()

    with pytest.raises(BusinessException) as exc:
        submit_answer(db_session, "2025001", secret.id, "A", role="student")
    assert exc.value.code == 404
    assert "题目不存在" in exc.value.message


def test_free_practice_allows_public_shared_bank_for_enrolled_student(db_session):
    """全站共享公共题库：已加入任一活跃课程的学生可练公共课题目。"""
    public_course = Course(name="公共题库课", created_by="admin", is_public=True)
    db_session.add(public_course)
    db_session.flush()
    public_q = _add_question(db_session, public_course.id, "公共共享题", answer="A")
    db_session.commit()

    result = submit_answer(db_session, "2025001", public_q.id, "A", role="student")
    assert result["is_correct"] is True
    assert result["correct_answer"] == "A"


def test_free_practice_blocks_soft_deleted_question(db_session):
    course = db_session.query(Course).filter(Course.name == "测试课程").first()
    question = _add_question(db_session, course.id, "已删题目", answer="A")
    question.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    with pytest.raises(BusinessException) as exc:
        submit_answer(db_session, "2025001", question.id, "A", role="student")
    assert exc.value.code == 404


def test_free_practice_blocks_soft_deleted_course_question(db_session):
    course = db_session.query(Course).filter(Course.name == "测试课程").first()
    question = db_session.query(Question).filter(Question.course_id == course.id).first()
    course.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    with pytest.raises(BusinessException) as exc:
        submit_answer(db_session, "2025001", question.id, "B", role="student")
    assert exc.value.code == 404


def test_free_practice_blocks_student_without_active_enrollment(db_session):
    lonely = User(
        id="2025099",
        name="无课学生",
        hashed_password="hash",
        role="student",
        major="测试",
    )
    db_session.add(lonely)
    course = db_session.query(Course).filter(Course.name == "测试课程").first()
    question = db_session.query(Question).filter(Question.course_id == course.id).first()
    db_session.commit()

    with pytest.raises(BusinessException) as exc:
        submit_answer(db_session, "2025099", question.id, "B", role="student")
    assert exc.value.code == 404


def test_assignment_submit_still_works_for_assigned_questions(db_session):
    course = db_session.query(Course).filter(Course.name == "测试课程").first()
    cls = db_session.query(Class).filter(Class.course_id == course.id).first()
    q1 = db_session.query(Question).filter(Question.course_id == course.id).first()
    q2 = _add_question(db_session, course.id, "作业第二题", answer="A")

    ann = Announcement(
        course_id=course.id,
        teacher_id="T001",
        type="task",
        title="范围测试作业",
        question_ids=[q1.id],
        max_score=100.0,
    )
    db_session.add(ann)
    db_session.flush()
    db_session.add(AnnouncementClass(announcement_id=ann.id, class_id=cls.id))
    db_session.commit()

    ok = submit_answer(db_session, "2025001", q1.id, "B", role="student", announcement_id=ann.id)
    assert ok["is_correct"] is True

    with pytest.raises(BusinessException) as exc:
        submit_answer(db_session, "2025001", q2.id, "A", role="student", announcement_id=ann.id)
    assert exc.value.code == 404


def test_get_course_questions_hides_soft_deleted(db_session):
    course = db_session.query(Course).filter(Course.name == "测试课程").first()
    live = _add_question(db_session, course.id, "可见题")
    dead = _add_question(db_session, course.id, "软删题")
    dead.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    questions = get_course_questions(db_session, course.id)
    ids = {q.id for q in questions}
    assert live.id in ids
    assert dead.id not in ids


def test_can_view_course_questions_rejects_soft_deleted_course(db_session):
    course = db_session.query(Course).filter(Course.name == "测试课程").first()
    assert can_view_course_questions(db_session, course.id, "2025001", "student") is True
    course.deleted_at = datetime.now(timezone.utc)
    db_session.commit()
    assert can_view_course_questions(db_session, course.id, "2025001", "student") is False


def test_student_course_questions_api_hides_answers(client, student_token, db_session):
    """学生拉题接口不得预下发标准答案与解析。"""
    course = db_session.query(Course).filter(Course.name == "测试课程").first()
    other_course = db_session.query(Course).filter(Course.name == "其它课程").first()
    secret = _add_question(db_session, other_course.id, "API不可见私有题", answer="Z")
    db_session.commit()

    resp = client.get(
        f"/api/questions/course/{course.id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    items = body["data"]
    assert items
    assert all(item.get("answer", "") == "" for item in items)
    assert all(item.get("explanation", "") == "" for item in items)
    assert all(item["id"] != secret.id for item in items)


def test_student_course_questions_include_public_bank_only(client, student_token, db_session):
    public_course = Course(name="API公共题库", created_by="admin", is_public=True)
    db_session.add(public_course)
    db_session.flush()
    public_q = _add_question(db_session, public_course.id, "API公共题", answer="A")
    db_session.commit()

    course = db_session.query(Course).filter(Course.name == "测试课程").first()
    resp = client.get(
        f"/api/questions/course/{course.id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    ids = {item["id"] for item in resp.json()["data"]}
    assert public_q.id in ids
