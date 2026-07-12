"""课程学习分析规模与查询形态回归测试。"""

from sqlalchemy import event

from app.models.entities import (
    Class,
    Lesson,
    LessonProgress,
    StudentClassEnrollment,
    User,
)
from tests.conftest import auth_header


def test_course_analytics_uses_constant_aggregate_queries(
    client,
    db_session,
    teacher_token,
):
    """100 名学生和 20 个课时时不得加载全量课时进度 ORM。"""
    class_id = db_session.query(Class.id).filter(Class.course_id == 1).scalar()
    students = [
        User(
            id=f"scale-{index:03d}",
            name=f"规模学生{index:03d}",
            hashed_password="unused",
            role="student",
        )
        for index in range(1, 100)
    ]
    db_session.add_all(students)
    db_session.flush()
    db_session.add_all([
        StudentClassEnrollment(user_id=student.id, class_id=class_id)
        for student in students
    ])

    lessons = [
        Lesson(
            course_id=1,
            title=f"规模课时{index:02d}",
            status="published",
            sort_order=index,
        )
        for index in range(1, 21)
    ]
    db_session.add_all(lessons)
    db_session.flush()

    student_ids = ["2025001", *(student.id for student in students)]
    db_session.add_all([
        LessonProgress(
            user_id=student_id,
            course_id=1,
            lesson_id=lesson.id,
            status="completed" if lesson.sort_order % 2 == 0 else "in_progress",
            progress_percent=100 if lesson.sort_order % 2 == 0 else 40,
            duration_seconds=30 + lesson.sort_order,
            last_position=300,
            view_count=1,
        )
        for student_id in student_ids
        for lesson in lessons
    ])
    db_session.commit()
    db_session.expunge_all()

    select_statements: list[str] = []
    loaded_progress_ids: list[int] = []

    def count_selects(_conn, _cursor, statement, _parameters, _context, _executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            select_statements.append(statement)

    def record_progress_load(target, _context):
        loaded_progress_ids.append(target.id)

    event.listen(db_session.bind, "before_cursor_execute", count_selects)
    event.listen(LessonProgress, "load", record_progress_load)
    try:
        response = client.get(
            "/api/courses/1/analytics?page=1&page_size=20",
            headers=auth_header(teacher_token),
        ).json()
    finally:
        event.remove(db_session.bind, "before_cursor_execute", count_selects)
        event.remove(LessonProgress, "load", record_progress_load)

    assert response["code"] == 0
    progress_page = response["data"]["student_progress"]
    assert progress_page["total"] == 100
    assert len(progress_page["items"]) == 20
    assert len(select_statements) <= 8
    assert loaded_progress_ids == []

    progress_selects = [
        statement.lower()
        for statement in select_statements
        if "lesson_progress" in statement.lower()
    ]
    assert progress_selects
    assert all("group by" in statement for statement in progress_selects)
