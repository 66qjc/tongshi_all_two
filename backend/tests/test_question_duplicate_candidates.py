"""题目查重候选集优化测试。"""
from app.models.entities import Course, Question
from app.services.question_bank_service import find_duplicate_question


def test_find_duplicate_question_detects_same_fingerprint_with_candidate_filter(db_session):
    """相同题型、题干、选项、答案的题目应被识别为重复。"""
    course = Course(name="查重课", created_by="T001", is_public=False)
    db_session.add(course)
    db_session.flush()
    question = Question(
        course_id=course.id,
        type="choice",
        stem="人工智能的英文缩写是什么？",
        options=["AI", "BI"],
        answer="AI",
    )
    db_session.add(question)
    db_session.commit()

    duplicate = find_duplicate_question(
        db_session,
        "choice",
        "人工智能的英文缩写是什么？",
        ["AI", "BI"],
        "AI",
    )

    assert duplicate is not None
    assert duplicate.id == question.id


def test_find_duplicate_question_ignores_different_answer(db_session):
    """相同题干但不同答案不应被视为重复。"""
    course = Course(name="查重课2", created_by="T001", is_public=False)
    db_session.add(course)
    db_session.flush()
    db_session.add(
        Question(
            course_id=course.id,
            type="choice",
            stem="Python 是什么？",
            options=["语言", "动物"],
            answer="语言",
        )
    )
    db_session.commit()

    duplicate = find_duplicate_question(
        db_session,
        "choice",
        "Python 是什么？",
        ["语言", "动物"],
        "动物",
    )

    assert duplicate is None
