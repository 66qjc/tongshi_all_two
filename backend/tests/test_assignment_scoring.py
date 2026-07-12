"""作业评分系统测试（简化版）"""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.db.schema_compat import ensure_schema_compatibility
from app.models.entities import Announcement, AnnouncementClass, Class, Course, Question, QuizAttempt, StudentClassEnrollment, TaskCompletion, User
from app.services.quiz_service import _update_assignment_score, submit_answer
from app.services.teacher_service import _latest_task_scores


@pytest.fixture(scope="module")
def db_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    ensure_schema_compatibility(engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()
    # 清理测试数据
    Base.metadata.drop_all(db_engine)
    Base.metadata.create_all(db_engine)
    ensure_schema_compatibility(db_engine)


@pytest.fixture
def test_data(db_session):
    """准备测试数据：1个教师、1门课程、5道题、1个作业"""
    teacher = User(id="T001", name="教师", role="teacher", hashed_password="hash")
    student1 = User(id="S001", name="学生1", role="student", hashed_password="hash")
    student2 = User(id="S002", name="学生2", role="student", hashed_password="hash")
    db_session.add_all([teacher, student1, student2])

    course = Course(id=1, name="测试课程", created_by="T001")
    db_session.add(course)

    # 创建班级
    class_obj = Class(id=1, name="测试班级", course_id=1, created_by="T001")
    db_session.add(class_obj)

    # 学生加入班级
    enrollment1 = StudentClassEnrollment(user_id="S001", class_id=1)
    enrollment2 = StudentClassEnrollment(user_id="S002", class_id=1)
    db_session.add_all([enrollment1, enrollment2])

    questions = [
        Question(id=1, course_id=1, type="choice", stem="题目1", options=["A", "B"], answer="A", explanation=""),
        Question(id=2, course_id=1, type="choice", stem="题目2", options=["A", "B"], answer="B", explanation=""),
        Question(id=3, course_id=1, type="choice", stem="题目3", options=["A", "B"], answer="A", explanation=""),
        Question(id=4, course_id=1, type="choice", stem="题目4", options=["A", "B"], answer="B", explanation=""),
        Question(id=5, course_id=1, type="choice", stem="题目5", options=["A", "B"], answer="A", explanation=""),
    ]
    db_session.add_all(questions)

    announcement = Announcement(
        id=1,
        course_id=1,
        teacher_id="T001",
        type="task",
        title="测试作业",
        question_ids=[1, 2, 3, 4, 5],
        max_score=100.0,
    )
    db_session.add(announcement)

    # 作业关联班级
    ann_class = AnnouncementClass(announcement_id=1, class_id=1)
    db_session.add(ann_class)

    db_session.commit()

    return {
        "teacher": teacher,
        "student1": student1,
        "student2": student2,
        "course": course,
        "class": class_obj,
        "questions": questions,
        "announcement": announcement,
    }


def test_auto_scoring_on_submit(db_session, test_data):
    """测试答题后自动计分"""
    # 学生1答对3题（60分）
    submit_answer(db_session, "S001", 1, "A", role="student", announcement_id=1)
    submit_answer(db_session, "S001", 2, "B", role="student", announcement_id=1)
    submit_answer(db_session, "S001", 3, "A", role="student", announcement_id=1)
    submit_answer(db_session, "S001", 4, "A", role="student", announcement_id=1)  # 错误
    submit_answer(db_session, "S001", 5, "B", role="student", announcement_id=1)  # 错误

    completion = db_session.query(TaskCompletion).filter(
        TaskCompletion.user_id == "S001",
        TaskCompletion.announcement_id == 1
    ).first()

    assert completion is not None, "答题后应自动创建 TaskCompletion 记录"
    assert completion.score == 60.0, f"3/5正确应得60分，实际得分：{completion.score}"
    assert completion.max_score == 100.0


def test_score_update_on_retry(db_session, test_data):
    """测试重新答题后分数更新"""
    # 学生2第一次答对2题（40分）
    submit_answer(db_session, "S002", 1, "A", role="student", announcement_id=1)
    submit_answer(db_session, "S002", 2, "A", role="student", announcement_id=1)  # 错误
    submit_answer(db_session, "S002", 3, "B", role="student", announcement_id=1)  # 错误
    submit_answer(db_session, "S002", 4, "B", role="student", announcement_id=1)
    submit_answer(db_session, "S002", 5, "B", role="student", announcement_id=1)  # 错误

    completion = db_session.query(TaskCompletion).filter(
        TaskCompletion.user_id == "S002",
        TaskCompletion.announcement_id == 1
    ).first()
    assert completion.score == 40.0

    # 学生2重新答题，第2题改对（60分）
    submit_answer(db_session, "S002", 2, "B", role="student", announcement_id=1)

    db_session.expire(completion)
    db_session.refresh(completion)
    assert completion.score == 60.0, "重新答题后分数应更新"


def test_export_uses_stored_score(db_session, test_data):
    """测试导出时使用持久化分数"""
    # 学生1答对4题（80分）
    submit_answer(db_session, "S001", 1, "A", role="student", announcement_id=1)
    submit_answer(db_session, "S001", 2, "B", role="student", announcement_id=1)
    submit_answer(db_session, "S001", 3, "A", role="student", announcement_id=1)
    submit_answer(db_session, "S001", 4, "B", role="student", announcement_id=1)
    submit_answer(db_session, "S001", 5, "B", role="student", announcement_id=1)  # 错误

    # 调用导出逻辑
    task_question_counts = {1: 5}
    scores = _latest_task_scores(db_session, [1], task_question_counts)

    assert ("S001", 1) in scores
    assert scores[("S001", 1)] == 80, f"导出应读取持久化分数80，实际：{scores[('S001', 1)]}"


def test_backward_compatibility(db_session, test_data):
    """测试兼容旧数据（无持久化分数时实时计算）"""
    # 手动创建一个 TaskCompletion 记录（score 为 NULL，模拟旧数据）
    old_completion = TaskCompletion(
        user_id="S002",
        announcement_id=1,
        score=None,
        max_score=100.0
    )
    db_session.add(old_completion)
    db_session.commit()

    # 创建答题记录（3题正确）
    attempts = [
        QuizAttempt(user_id="S002", question_id=1, announcement_id=1, user_answer="A", is_correct=True),
        QuizAttempt(user_id="S002", question_id=2, announcement_id=1, user_answer="A", is_correct=False),
        QuizAttempt(user_id="S002", question_id=3, announcement_id=1, user_answer="A", is_correct=True),
        QuizAttempt(user_id="S002", question_id=4, announcement_id=1, user_answer="B", is_correct=True),
        QuizAttempt(user_id="S002", question_id=5, announcement_id=1, user_answer="B", is_correct=False),
    ]
    db_session.add_all(attempts)
    db_session.commit()

    # 调用导出逻辑
    task_question_counts = {1: 5}
    scores = _latest_task_scores(db_session, [1], task_question_counts)

    assert ("S002", 1) in scores
    assert scores[("S002", 1)] == 60, "旧数据应实时计算分数（3/5=60分）"


def test_custom_max_score(db_session, test_data):
    """测试自定义满分（非100分）"""
    # 创建一个150分的作业
    announcement_150 = Announcement(
        id=2,
        course_id=1,
        teacher_id="T001",
        type="task",
        title="高分作业",
        question_ids=[1, 2, 3, 4, 5],
        max_score=150.0,
    )
    db_session.add(announcement_150)

    # 作业关联班级
    ann_class = AnnouncementClass(announcement_id=2, class_id=1)
    db_session.add(ann_class)
    db_session.commit()

    # 学生1答对3题（90分 = 3/5 * 150）
    submit_answer(db_session, "S001", 1, "A", role="student", announcement_id=2)
    submit_answer(db_session, "S001", 2, "B", role="student", announcement_id=2)
    submit_answer(db_session, "S001", 3, "A", role="student", announcement_id=2)
    submit_answer(db_session, "S001", 4, "A", role="student", announcement_id=2)  # 错误
    submit_answer(db_session, "S001", 5, "B", role="student", announcement_id=2)  # 错误

    completion = db_session.query(TaskCompletion).filter(
        TaskCompletion.user_id == "S001",
        TaskCompletion.announcement_id == 2
    ).first()

    assert completion.score == 90.0, f"3/5正确，满分150应得90分，实际：{completion.score}"
    assert completion.max_score == 150.0


def test_assignment_completion_recovers_from_concurrent_insert(tmp_path):
    """完成记录被另一事务抢先插入时，当前评分事务应复用该记录。"""
    db_path = tmp_path / "assignment-concurrency.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA journal_mode=WAL")
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with SessionLocal() as seed:
        seed.add_all([
            User(id="T900", name="教师", role="teacher", hashed_password="hash"),
            User(id="S900", name="学生", role="student", hashed_password="hash"),
            Course(id=900, name="并发测试课程", created_by="T900"),
            Question(
                id=900,
                course_id=900,
                type="choice",
                stem="并发完成题",
                options=["A", "B"],
                answer="A",
                explanation="",
            ),
            Announcement(
                id=900,
                course_id=900,
                teacher_id="T900",
                type="task",
                title="并发完成作业",
                question_ids=[900],
                max_score=100.0,
            ),
            QuizAttempt(
                user_id="S900",
                question_id=900,
                announcement_id=900,
                user_answer="A",
                is_correct=True,
            ),
        ])
        seed.commit()

    session = SessionLocal()
    competing_inserted = False

    def insert_competing_completion(current_session, _flush_context, _instances):
        nonlocal competing_inserted
        if competing_inserted or not any(isinstance(item, TaskCompletion) for item in current_session.new):
            return
        competing_inserted = True
        with SessionLocal() as competing_session:
            competing_session.add(TaskCompletion(
                user_id="S900",
                announcement_id=900,
                score=0,
                max_score=100.0,
            ))
            competing_session.commit()

    event.listen(session, "before_flush", insert_competing_completion)
    try:
        _update_assignment_score(session, "S900", 900)
        session.commit()
    finally:
        event.remove(session, "before_flush", insert_competing_completion)
        session.rollback()
        session.close()

    with SessionLocal() as verify:
        completions = verify.query(TaskCompletion).filter(
            TaskCompletion.user_id == "S900",
            TaskCompletion.announcement_id == 900,
        ).all()
        assert len(completions) == 1
        assert completions[0].score == 100.0

    engine.dispose()
