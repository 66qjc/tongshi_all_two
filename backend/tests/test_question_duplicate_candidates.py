"""题目查重候选集优化测试。"""
import hashlib

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.entities import Course, Question
from app.db.session import Base
from app.db.schema_compat import ensure_schema_compatibility
from app.services.question_bank_service import compute_stem_hash, find_duplicate_question


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


def test_compute_stem_hash_uses_normalized_sha256():
    """题干哈希应统一规范化空白和大小写，并使用 SHA-256。"""
    expected = hashlib.sha256("人工智能 题目".encode("utf-8")).hexdigest()

    assert compute_stem_hash("  人工智能\n题目  ") == expected


def test_schema_compatibility_rewrites_legacy_question_hashes():
    """兼容初始化应把旧 MD5、空值和异常长度哈希升级为当前 SHA-256。"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        course = Course(name="哈希升级课", created_by="T001")
        session.add(course)
        session.flush()
        course_id = course.id
        session.add_all(
            [
                Question(
                    course_id=course.id,
                    type="fill",
                    stem="旧 MD5 题目",
                    answer="答案",
                    stem_hash=hashlib.md5("旧 md5 题目".encode("utf-8")).hexdigest(),
                ),
                Question(
                    course_id=course.id,
                    type="fill",
                    stem="空值题目",
                    answer="答案",
                    stem_hash=None,
                ),
                Question(
                    course_id=course.id,
                    type="fill",
                    stem="异常长度题目",
                    answer="答案",
                    stem_hash="legacy",
                ),
            ]
        )
        session.commit()

    ensure_schema_compatibility(engine)

    with Session(engine) as session:
        questions = session.query(Question).filter(Question.course_id == course_id).all()
        assert [question.stem_hash for question in questions] == [
            compute_stem_hash(question.stem) for question in questions
        ]
