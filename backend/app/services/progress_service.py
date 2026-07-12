"""学习进度服务。"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_, case, func, or_
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.timezone_utils import to_beijing_iso
from app.models.entities import (
    Class,
    Course,
    CourseProgress,
    Lesson,
    LessonProgress,
    StudentClassEnrollment,
    User,
)
from app.schemas.common import AuthUser, CourseProgressIn, LessonProgressIn
from app.services.access_control_service import student_can_access_course


LESSON_COMPLETED_THRESHOLD = 90
FAST_COMPLETION_NUMERATOR = 3
FAST_COMPLETION_DENOMINATOR = 10


def _utc_now() -> datetime:
    """返回统一的 UTC 时间。"""
    return datetime.now(timezone.utc)


def _require_course_progress_access(db: Session, course_id: int, current_user: AuthUser) -> Course:
    """校验当前用户是否可以读写自己在该课程下的学习进度。"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise BusinessException(404, "课程不存在")
    if current_user.role == "admin":
        return course
    if current_user.role == "teacher":
        if course.created_by != current_user.id:
            raise BusinessException(403, "无权访问该课程进度")
        return course
    if current_user.role == "student":
        if not student_can_access_course(db, current_user.id, course_id):
            raise BusinessException(404, "课程不存在")
        return course
    raise BusinessException(403, "无权访问该课程进度")


def _require_course_analytics_access(db: Session, course_id: int, current_user: AuthUser) -> Course:
    """校验教师或管理员是否可以查看课程学习统计。"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise BusinessException(404, "课程不存在")
    if current_user.role == "admin":
        return course
    if current_user.role == "teacher" and course.created_by == current_user.id:
        return course
    raise BusinessException(403, "无权查看该课程统计")


def _require_class_student_access(
    db: Session,
    class_id: int,
    student_id: str,
    current_user: AuthUser,
) -> tuple[Class, User]:
    """校验教师是否可以查看指定班级学生的学习进度。"""
    cls = db.query(Class).filter(Class.id == class_id, Class.created_by == current_user.id).first()
    if not cls:
        raise BusinessException(404, "班级不存在")

    enrollment = (
        db.query(StudentClassEnrollment)
        .filter(
            StudentClassEnrollment.class_id == class_id,
            StudentClassEnrollment.user_id == student_id,
        )
        .first()
    )
    if not enrollment:
        raise BusinessException(404, "学生不在该班级中")

    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student:
        raise BusinessException(404, "学生不存在")
    return cls, student


def _is_fast_completion(progress: LessonProgress) -> bool:
    """识别疑似刷课：已完成但实际学习时长明显低于播放位置。"""
    if progress.status != "completed":
        return False
    if progress.last_position <= 0:
        return progress.duration_seconds < 30
    return progress.duration_seconds < (
        progress.last_position * FAST_COMPLETION_NUMERATOR
    ) // FAST_COMPLETION_DENOMINATOR


def _fast_completion_flag():
    """返回可用于数据库聚合的疑似刷课标记表达式。"""
    return case(
        (
            and_(
                LessonProgress.status == "completed",
                or_(
                    and_(
                        LessonProgress.last_position <= 0,
                        LessonProgress.duration_seconds < 30,
                    ),
                    and_(
                        LessonProgress.last_position > 0,
                        (LessonProgress.duration_seconds + 1) * FAST_COMPLETION_DENOMINATOR
                        <= LessonProgress.last_position * FAST_COMPLETION_NUMERATOR,
                    ),
                ),
            ),
            1,
        ),
        else_=0,
    )


def _format_lesson_progress(lesson: Lesson, progress: LessonProgress | None) -> dict:
    """将课时和进度记录合并为接口输出。"""
    if progress is None:
        return {
            "lesson_id": lesson.id,
            "course_id": lesson.course_id,
            "title": lesson.title,
            "status": "not_started",
            "progress_percent": 0,
            "last_position": 0,
            "duration_seconds": 0,
            "view_count": 0,
            "is_fast_completion": False,
            "first_viewed_at": None,
            "last_viewed_at": None,
            "completed_at": None,
        }

    return {
        "lesson_id": lesson.id,
        "course_id": lesson.course_id,
        "title": lesson.title,
        "status": progress.status,
        "progress_percent": progress.progress_percent,
        "last_position": progress.last_position,
        "duration_seconds": progress.duration_seconds,
        "view_count": progress.view_count,
        "is_fast_completion": _is_fast_completion(progress),
        "first_viewed_at": to_beijing_iso(progress.first_viewed_at),
        "last_viewed_at": to_beijing_iso(progress.last_viewed_at),
        "completed_at": to_beijing_iso(progress.completed_at),
    }


def _execute_upsert(
    db: Session,
    model,
    *,
    values: dict,
    updates: dict,
    index_elements: list,
) -> None:
    """按当前数据库方言执行原子 upsert。"""
    dialect_name = db.get_bind().dialect.name
    if dialect_name == "sqlite":
        statement = sqlite_insert(model).values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=index_elements,
            set_=updates,
        )
    elif dialect_name == "mysql":
        statement = mysql_insert(model).values(**values)
        statement = statement.on_duplicate_key_update(**updates)
    else:
        raise RuntimeError(f"不支持的进度 upsert 数据库方言：{dialect_name}")
    db.execute(statement)


def _sync_course_last_lesson(
    db: Session,
    user_id: str,
    course_id: int,
    lesson_id: int,
    now: datetime | None = None,
) -> None:
    """同步旧 course_progress 表，保持学习馆继续学习入口兼容。"""
    updated_at = now or _utc_now()
    _execute_upsert(
        db,
        CourseProgress,
        values={
            "user_id": user_id,
            "course_id": course_id,
            "last_lesson_id": lesson_id,
            "updated_at": updated_at,
        },
        updates={
            "last_lesson_id": lesson_id,
            "updated_at": updated_at,
        },
        index_elements=[CourseProgress.user_id, CourseProgress.course_id],
    )


def _course_last_lesson_id(db: Session, user_id: str, course_id: int) -> int | None:
    """读取旧课程进度中的最后课时。"""
    progress = (
        db.query(CourseProgress)
        .filter(CourseProgress.user_id == user_id, CourseProgress.course_id == course_id)
        .first()
    )
    if progress and progress.last_lesson_id:
        return progress.last_lesson_id

    latest = (
        db.query(LessonProgress)
        .filter(LessonProgress.user_id == user_id, LessonProgress.course_id == course_id)
        .order_by(LessonProgress.last_viewed_at.desc(), LessonProgress.id.desc())
        .first()
    )
    return latest.lesson_id if latest else None


def get_progress(db: Session, course_id: int, current_user: AuthUser) -> int | None:
    """获取当前用户在指定课程的旧版学习进度。"""
    _require_course_progress_access(db, course_id, current_user)
    return _course_last_lesson_id(db, current_user.id, course_id)


def save_progress(
    db: Session,
    course_id: int,
    data: CourseProgressIn,
    current_user: AuthUser,
) -> int:
    """保存或更新当前用户在指定课程的旧版学习进度。"""
    _require_course_progress_access(db, course_id, current_user)

    lesson = (
        db.query(Lesson)
        .filter(Lesson.id == data.lesson_id, Lesson.course_id == course_id)
        .first()
    )
    if not lesson:
        raise BusinessException(400, "课时不存在或不属于该课程")
    if current_user.role == "student" and lesson.status != "published":
        raise BusinessException(404, "课时不存在")

    _sync_course_last_lesson(db, current_user.id, course_id, data.lesson_id)
    db.flush()
    return data.lesson_id


def report_lesson_progress(
    db: Session,
    course_id: int,
    lesson_id: int,
    data: LessonProgressIn,
    current_user: AuthUser,
) -> dict:
    """上报课时级学习进度。"""
    _require_course_progress_access(db, course_id, current_user)
    lesson = (
        db.query(Lesson)
        .filter(Lesson.id == lesson_id, Lesson.course_id == course_id)
        .first()
    )
    if not lesson:
        raise BusinessException(400, "课时不存在或不属于该课程")
    if current_user.role == "student" and lesson.status != "published":
        raise BusinessException(404, "课时不存在")

    now = _utc_now()
    incoming_completed = data.progress_percent >= LESSON_COMPLETED_THRESHOLD
    incoming_percent = 100 if incoming_completed else data.progress_percent
    incoming_status = (
        "completed"
        if incoming_completed
        else "in_progress"
        if incoming_percent > 0
        else "not_started"
    )
    highest_percent = case(
        (LessonProgress.progress_percent < incoming_percent, incoming_percent),
        else_=LessonProgress.progress_percent,
    )
    completed_condition = or_(
        LessonProgress.status == "completed",
        highest_percent >= LESSON_COMPLETED_THRESHOLD,
    )
    stored_percent = case(
        (completed_condition, 100),
        else_=highest_percent,
    )
    stored_status = case(
        (completed_condition, "completed"),
        (highest_percent > 0, "in_progress"),
        else_="not_started",
    )
    completed_at = case(
        (LessonProgress.completed_at.is_not(None), LessonProgress.completed_at),
        (completed_condition, now),
        else_=None,
    )
    _execute_upsert(
        db,
        LessonProgress,
        values={
            "user_id": current_user.id,
            "course_id": course_id,
            "lesson_id": lesson_id,
            "status": incoming_status,
            "progress_percent": incoming_percent,
            "last_position": data.last_position,
            "duration_seconds": data.duration_seconds,
            "first_viewed_at": now,
            "last_viewed_at": now,
            "completed_at": now if incoming_completed else None,
            "view_count": 1 if data.visit_started else 0,
        },
        updates={
            "status": stored_status,
            "progress_percent": stored_percent,
            "last_position": data.last_position,
            "duration_seconds": LessonProgress.duration_seconds + data.duration_seconds,
            "last_viewed_at": now,
            "completed_at": completed_at,
            "view_count": LessonProgress.view_count + (1 if data.visit_started else 0),
        },
        index_elements=[LessonProgress.user_id, LessonProgress.lesson_id],
    )
    _sync_course_last_lesson(db, current_user.id, course_id, lesson_id, now)
    progress = (
        db.query(LessonProgress)
        .populate_existing()
        .filter(LessonProgress.user_id == current_user.id, LessonProgress.lesson_id == lesson_id)
        .one()
    )
    return _format_lesson_progress(lesson, progress)


def build_course_progress_summary(db: Session, course_id: int, user_id: str) -> dict:
    """构建指定学生在课程下的课时进度汇总。"""
    lessons = (
        db.query(Lesson)
        .filter(Lesson.course_id == course_id, Lesson.status == "published")
        .order_by(Lesson.sort_order, Lesson.id)
        .all()
    )
    progress_items = (
        db.query(LessonProgress)
        .filter(LessonProgress.user_id == user_id, LessonProgress.course_id == course_id)
        .all()
    )
    progress_map = {item.lesson_id: item for item in progress_items}
    lesson_outputs = [_format_lesson_progress(lesson, progress_map.get(lesson.id)) for lesson in lessons]
    completed_lessons = sum(1 for item in lesson_outputs if item["status"] == "completed")
    total_lessons = len(lessons)
    total_duration = sum(item["duration_seconds"] for item in lesson_outputs)
    completion_rate = round((completed_lessons / total_lessons) * 100, 1) if total_lessons else 0
    return {
        "last_lesson_id": _course_last_lesson_id(db, user_id, course_id),
        "total_lessons": total_lessons,
        "completed_lessons": completed_lessons,
        "total_duration": total_duration,
        "completion_rate": completion_rate,
        "lessons": lesson_outputs,
    }


def get_course_progress_summary(db: Session, course_id: int, current_user: AuthUser) -> dict:
    """获取当前用户在课程下的课时级学习进度汇总。"""
    _require_course_progress_access(db, course_id, current_user)
    return build_course_progress_summary(db, course_id, current_user.id)


def get_class_student_progress(
    db: Session,
    class_id: int,
    student_id: str,
    current_user: AuthUser,
) -> dict:
    """教师查看指定班级学生的课程进度。"""
    cls, student = _require_class_student_access(db, class_id, student_id, current_user)
    summary = build_course_progress_summary(db, cls.course_id, student_id)
    return {
        "class_id": cls.id,
        "class_name": cls.name,
        "course_id": cls.course_id,
        "student": {
            "id": student.id,
            "name": student.name,
            "major": student.major or "",
        },
        "progress": summary,
    }


def get_course_analytics(
    db: Session,
    course_id: int,
    current_user: AuthUser,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """教师端课程学习统计。"""
    _require_course_analytics_access(db, course_id, current_user)
    safe_page = max(1, page)
    safe_page_size = min(100, max(1, page_size))

    course_students = (
        db.query(
            User.id.label("student_id"),
            User.name.label("student_name"),
        )
        .join(
            StudentClassEnrollment,
            StudentClassEnrollment.user_id == User.id,
        )
        .join(Class, Class.id == StudentClassEnrollment.class_id)
        .filter(
            Class.course_id == course_id,
            Class.deleted_at.is_(None),
            User.role == "student",
            User.deleted_at.is_(None),
        )
        .distinct()
        .subquery("course_students")
    )

    student_progress_totals = (
        db.query(
            LessonProgress.user_id.label("student_id"),
            func.sum(
                case((LessonProgress.status == "completed", 1), else_=0),
            ).label("completed_lessons"),
            func.sum(LessonProgress.duration_seconds).label("duration_seconds"),
            func.sum(_fast_completion_flag()).label("fast_completion_count"),
        )
        .join(
            course_students,
            course_students.c.student_id == LessonProgress.user_id,
        )
        .join(Lesson, Lesson.id == LessonProgress.lesson_id)
        .filter(
            LessonProgress.course_id == course_id,
            Lesson.course_id == course_id,
            Lesson.status == "published",
        )
        .group_by(LessonProgress.user_id)
        .subquery("student_progress_totals")
    )

    completed_value = func.coalesce(student_progress_totals.c.completed_lessons, 0)
    duration_value = func.coalesce(student_progress_totals.c.duration_seconds, 0)
    fast_completion_value = func.coalesce(
        student_progress_totals.c.fast_completion_count,
        0,
    )
    overall = (
        db.query(
            func.count(course_students.c.student_id).label("student_count"),
            func.coalesce(func.sum(completed_value), 0).label("completed_lessons"),
            func.coalesce(func.sum(duration_value), 0).label("duration_seconds"),
        )
        .select_from(course_students)
        .outerjoin(
            student_progress_totals,
            student_progress_totals.c.student_id == course_students.c.student_id,
        )
        .one()
    )
    student_count = int(overall.student_count or 0)

    student_rows = (
        db.query(
            course_students.c.student_id,
            course_students.c.student_name,
            completed_value.label("completed_lessons"),
            duration_value.label("duration_seconds"),
            fast_completion_value.label("fast_completion_count"),
        )
        .select_from(course_students)
        .outerjoin(
            student_progress_totals,
            student_progress_totals.c.student_id == course_students.c.student_id,
        )
        .order_by(
            completed_value.asc(),
            duration_value.desc(),
            course_students.c.student_id.asc(),
        )
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )

    lesson_progress_totals = (
        db.query(
            LessonProgress.lesson_id.label("lesson_id"),
            func.sum(LessonProgress.view_count).label("view_count"),
            func.count(LessonProgress.user_id.distinct()).label("viewed_students"),
            func.avg(LessonProgress.progress_percent).label("avg_progress_percent"),
            func.sum(
                case((LessonProgress.status == "completed", 1), else_=0),
            ).label("completed_count"),
            func.avg(LessonProgress.duration_seconds).label("avg_duration"),
            func.sum(_fast_completion_flag()).label("fast_completion_count"),
        )
        .join(
            course_students,
            course_students.c.student_id == LessonProgress.user_id,
        )
        .join(Lesson, Lesson.id == LessonProgress.lesson_id)
        .filter(
            LessonProgress.course_id == course_id,
            Lesson.course_id == course_id,
            Lesson.status == "published",
        )
        .group_by(LessonProgress.lesson_id)
        .subquery("lesson_progress_totals")
    )

    lesson_rows = (
        db.query(
            Lesson.id.label("lesson_id"),
            Lesson.title,
            func.coalesce(lesson_progress_totals.c.view_count, 0).label("view_count"),
            func.coalesce(lesson_progress_totals.c.viewed_students, 0).label("viewed_students"),
            func.coalesce(lesson_progress_totals.c.avg_progress_percent, 0).label("avg_progress_percent"),
            func.coalesce(lesson_progress_totals.c.completed_count, 0).label("completed_count"),
            func.coalesce(lesson_progress_totals.c.avg_duration, 0).label("avg_duration"),
            func.coalesce(lesson_progress_totals.c.fast_completion_count, 0).label("fast_completion_count"),
        )
        .outerjoin(
            lesson_progress_totals,
            lesson_progress_totals.c.lesson_id == Lesson.id,
        )
        .filter(Lesson.course_id == course_id, Lesson.status == "published")
        .order_by(Lesson.sort_order, Lesson.id)
        .all()
    )
    lesson_count = len(lesson_rows)

    student_progress = []
    for row in student_rows:
        completed = int(row.completed_lessons or 0)
        duration = int(row.duration_seconds or 0)
        student_progress.append({
            "student_id": row.student_id,
            "student_name": row.student_name,
            "completed_lessons": completed,
            "total_lessons": lesson_count,
            "completion_rate": round((completed / lesson_count) * 100, 1) if lesson_count else 0,
            "duration_seconds": duration,
            "fast_completion_count": int(row.fast_completion_count or 0),
        })

    lesson_summaries = []
    for row in lesson_rows:
        avg_progress = round(float(row.avg_progress_percent or 0), 1)
        completed_count = int(row.completed_count or 0)
        lesson_summaries.append({
            "lesson_id": row.lesson_id,
            "title": row.title,
            "view_count": int(row.view_count or 0),
            "viewed_students": int(row.viewed_students or 0),
            "avg_progress_percent": avg_progress,
            "completion_rate": round((completed_count / student_count) * 100, 1) if student_count else 0,
            "avg_duration": round(float(row.avg_duration or 0), 1),
            "fast_completion_count": int(row.fast_completion_count or 0),
        })

    return {
        "student_count": student_count,
        "lesson_count": lesson_count,
        "avg_completion_rate": (
            round((int(overall.completed_lessons or 0) / (student_count * lesson_count)) * 100, 1)
            if student_count and lesson_count
            else 0
        ),
        "avg_duration": (
            round(int(overall.duration_seconds or 0) / student_count, 1)
            if student_count
            else 0
        ),
        "most_viewed_lessons": sorted(
            lesson_summaries,
            key=lambda item: (item["view_count"], item["avg_progress_percent"], item["avg_duration"]),
            reverse=True,
        )[:5],
        "low_completion_lessons": sorted(
            [item for item in lesson_summaries if item["avg_progress_percent"] < 50],
            key=lambda item: (item["avg_progress_percent"], -item["lesson_id"]),
        )[:5],
        "student_progress": {
            "items": student_progress,
            "total": student_count,
            "page": safe_page,
            "page_size": safe_page_size,
        },
    }
