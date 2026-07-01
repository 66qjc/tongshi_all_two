"""Teacher service"""
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from app.models.entities import (
    Announcement,
    AnnouncementClass,
    Class,
    Course,
    Project,
    QuizAttempt,
    StudentClassEnrollment,
    TaskCompletion,
    User,
)


def _teacher_class_ids(db: Session, teacher_id: str) -> list[int]:
    return [
        row.id for row in db.query(Class.id)
        .filter(Class.created_by == teacher_id)
        .all()
    ]


def _teacher_student_ids(db: Session, teacher_id: str) -> list[str]:
    class_ids = _teacher_class_ids(db, teacher_id)
    if not class_ids:
        return []
    return [
        row.user_id for row in db.query(StudentClassEnrollment.user_id)
        .filter(StudentClassEnrollment.class_id.in_(class_ids))
        .distinct()
        .all()
    ]


def _teacher_course_ids(db: Session, teacher_id: str) -> list[int]:
    return [
        row.id for row in db.query(Course.id)
        .filter(Course.created_by == teacher_id)
        .all()
    ]


def _apply_teacher_project_scope(query, db: Session, teacher_id: str):
    course_ids = _teacher_course_ids(db, teacher_id)
    student_ids = _teacher_student_ids(db, teacher_id)
    filters = []
    if course_ids:
        filters.append(Project.course_id.in_(course_ids))
    if student_ids:
        filters.append(Project.course_id.is_(None) & Project.author_id.in_(student_ids))
    if not filters:
        return query.filter(False)
    return query.filter(or_(*filters))


def get_teacher_stats(db: Session, teacher_id: str):
    student_ids = _teacher_student_ids(db, teacher_id)
    total_students = len(student_ids)
    my_courses = db.query(Course).filter(Course.created_by == teacher_id).count()
    public_courses = db.query(Course).filter(Course.is_public == True).count()
    pending_reviews_query = _apply_teacher_project_scope(
        db.query(Project).filter(Project.status == "pending"),
        db,
        teacher_id,
    )
    pending_reviews = pending_reviews_query.count()
    weekly_exercises_query = db.query(QuizAttempt)
    if student_ids:
        weekly_exercises_query = weekly_exercises_query.filter(QuizAttempt.user_id.in_(student_ids))
    else:
        weekly_exercises_query = weekly_exercises_query.filter(False)
    weekly_exercises = weekly_exercises_query.count()  # simplified: total instead of weekly
    return {
        "total_students": total_students,
        "my_courses": my_courses,
        "public_courses": public_courses,
        "pending_reviews": pending_reviews,
        "weekly_exercises": weekly_exercises,
    }


def list_students(
    db: Session,
    teacher_id: str,
    class_id: int = None,
    page: int = None,
    page_size: int = None,
    keyword: str = None,
    course_id: int = None,
):
    class_query = db.query(Class.id).filter(Class.created_by == teacher_id)
    if course_id:
        course_exists = db.query(Course.id).filter(
            Course.id == course_id,
            Course.created_by == teacher_id,
        ).first()
        if not course_exists:
            return [], 0
        class_query = class_query.filter(Class.course_id == course_id)
    class_ids = [row.id for row in class_query.all()]
    if class_id:
        if class_id not in class_ids:
            return [], 0
        class_ids = [class_id]
    if not class_ids:
        return [], 0

    # 数据库层去重排序：每个学生取所在最小班级 ID 和最早导入顺序作为排序基
    sort_sub = (
        db.query(
            StudentClassEnrollment.user_id.label("user_id"),
            func.min(Class.id).label("sort_class_id"),
            func.min(func.coalesce(StudentClassEnrollment.import_order, 0)).label("sort_import_order"),
        )
        .join(Class, Class.id == StudentClassEnrollment.class_id)
        .filter(StudentClassEnrollment.class_id.in_(class_ids))
        .group_by(StudentClassEnrollment.user_id)
        .subquery()
    )

    student_query = (
        db.query(User, sort_sub.c.sort_class_id, sort_sub.c.sort_import_order)
        .join(sort_sub, sort_sub.c.user_id == User.id)
        .filter(User.role == "student")
    )
    if keyword:
        keyword_like = f"%{keyword.strip()}%"
        student_query = student_query.filter(
            (User.id.ilike(keyword_like)) | (User.name.ilike(keyword_like))
        )

    total = student_query.count()
    student_query = student_query.order_by(
        sort_sub.c.sort_class_id.asc(),
        sort_sub.c.sort_import_order.asc(),
        User.id.asc(),
    )

    if page and page_size:
        safe_page = max(page, 1)
        safe_page_size = max(min(page_size, 100), 1)
        rows = student_query.offset((safe_page - 1) * safe_page_size).limit(safe_page_size).all()
    else:
        rows = student_query.all()

    paged_ids = [student.id for student, _, _ in rows]
    student_user = {student.id: student for student, _, _ in rows}

    # 当前页学生的班级聚合信息
    student_class_ids: dict[str, set[int]] = {sid: set() for sid in paged_ids}
    student_class_names: dict[str, list[str]] = {sid: [] for sid in paged_ids}
    student_first_enrollment: dict[str, StudentClassEnrollment] = {}

    if paged_ids:
        rows_for_aggregation = (
            db.query(User, StudentClassEnrollment, Class)
            .join(StudentClassEnrollment, StudentClassEnrollment.user_id == User.id)
            .join(Class, Class.id == StudentClassEnrollment.class_id)
            .filter(
                User.role == "student",
                User.id.in_(paged_ids),
                StudentClassEnrollment.class_id.in_(class_ids),
            )
            .order_by(Class.id.asc(), StudentClassEnrollment.import_order.asc(), User.id.asc())
            .all()
        )
        for student, enrollment, class_ in rows_for_aggregation:
            student_class_ids.setdefault(student.id, set()).add(class_.id)
            student_class_names.setdefault(student.id, []).append(class_.name)
            student_user[student.id] = student
            if student.id not in student_first_enrollment:
                student_first_enrollment[student.id] = enrollment

    # 任务与完成数据
    course_id_query = db.query(Class.course_id).filter(Class.created_by == teacher_id).distinct()
    if course_id:
        course_id_query = course_id_query.filter(Class.course_id == course_id)
    course_ids = [row.course_id for row in course_id_query.all()]

    class_task_ids: dict[int, set[int]] = {}
    completed_task_ids: dict[str, set[int]] = {sid: set() for sid in paged_ids}
    task_by_id: dict[int, Announcement] = {}
    task_scores: dict[tuple[str, int], int] = {}
    task_titles: dict[int, str] = {}
    ordered_tasks: list[Announcement] = []

    if paged_ids and course_ids:
        task_rows = (
            db.query(Announcement)
            .filter(
                Announcement.teacher_id == teacher_id,
                Announcement.type == "quiz",
                Announcement.course_id.in_(course_ids),
            )
            .order_by(Announcement.created_at.asc(), Announcement.id.asc())
            .all()
        )
        all_task_ids: set[int] = set()
        for task in task_rows:
            task_by_id[task.id] = task
            all_task_ids.add(task.id)

        task_class_rows = (
            db.query(AnnouncementClass.announcement_id, AnnouncementClass.class_id)
            .filter(
                AnnouncementClass.announcement_id.in_(all_task_ids),
                AnnouncementClass.class_id.in_(class_ids),
            )
            .all()
        ) if all_task_ids else []
        for task_id, owned_class_id in task_class_rows:
            class_task_ids.setdefault(owned_class_id, set()).add(task_id)

        if all_task_ids:
            completion_rows = (
                db.query(TaskCompletion.user_id, TaskCompletion.announcement_id)
                .filter(
                    TaskCompletion.user_id.in_(paged_ids),
                    TaskCompletion.announcement_id.in_(all_task_ids),
                )
                .all()
            )
            for user_id, task_id in completion_rows:
                completed_task_ids.setdefault(user_id, set()).add(task_id)

            ordered_tasks = sorted(task_by_id.values(), key=lambda item: (item.created_at, item.id))
            task_titles = _ordered_task_header_titles(ordered_tasks)
            task_question_counts = {
                task.id: len(task.question_ids if isinstance(task.question_ids, list) else [])
                for task in ordered_tasks
            }
            task_scores = _latest_task_scores(db, list(all_task_ids), task_question_counts)

    result = []
    for sid in paged_ids:
        s = student_user[sid]
        enrollment = student_first_enrollment.get(sid)
        class_id_list = list(student_class_ids.get(sid, set()))
        class_name_str = "、".join(student_class_names.get(sid, []))

        assigned_task_ids: set[int] = set()
        for cid in class_id_list:
            assigned_task_ids.update(class_task_ids.get(cid, set()))
        completed_count = len(assigned_task_ids & completed_task_ids.get(sid, set()))
        total_task_count = len(assigned_task_ids)
        incomplete_count = max(total_task_count - completed_count, 0)
        task_completion_rate = int(round(completed_count / total_task_count * 100)) if total_task_count else 0
        score_items = []
        for task in ordered_tasks:
            if task.id not in assigned_task_ids:
                continue
            score_items.append({
                "announcement_id": task.id,
                "title": task_titles.get(task.id, task.title),
                "score": task_scores.get((sid, task.id)),
                "is_completed": task.id in completed_task_ids.get(sid, set()),
            })

        result.append({
            "serial_no": enrollment.import_order if enrollment else 0,
            "id": sid,
            "name": s.name,
            "major": s.major or "",
            "class_id": class_id_list[0] if class_id_list else None,
            "class_name": class_name_str,
            "completed_tasks": completed_count,
            "incomplete_tasks": incomplete_count,
            "task_completion_rate": task_completion_rate,
            "task_scores": score_items,
        })
    return result, total


def _latest_task_scores(db: Session, task_ids: list[int], task_question_counts: dict[int, int]) -> dict[tuple[str, int], int]:
    """按任务上下文计算学生每次作业的最新答题百分制分数。"""
    if not task_ids:
        return {}

    latest_attempt_ids = (
        db.query(func.max(QuizAttempt.id).label("attempt_id"))
        .filter(QuizAttempt.announcement_id.in_(task_ids))
        .group_by(QuizAttempt.user_id, QuizAttempt.announcement_id, QuizAttempt.question_id)
        .subquery()
    )
    attempts = (
        db.query(QuizAttempt.user_id, QuizAttempt.announcement_id, QuizAttempt.is_correct)
        .join(latest_attempt_ids, QuizAttempt.id == latest_attempt_ids.c.attempt_id)
        .all()
    )

    attempted_counts: dict[tuple[str, int], int] = {}
    correct_counts: dict[tuple[str, int], int] = {}
    for user_id, task_id, is_correct in attempts:
        key = (user_id, task_id)
        attempted_counts[key] = attempted_counts.get(key, 0) + 1
        if is_correct:
            correct_counts[key] = correct_counts.get(key, 0) + 1

    scores: dict[tuple[str, int], int] = {}
    for key in attempted_counts:
        _, task_id = key
        total_questions = task_question_counts.get(task_id, 0)
        if total_questions <= 0:
            scores[key] = 0
        else:
            scores[key] = min(100, round(correct_counts.get(key, 0) / total_questions * 100))
    return scores


def _ordered_task_header_titles(tasks: list[Announcement]) -> dict[int, str]:
    """生成同一课程内唯一的作业列名。"""
    title_counts: dict[str, int] = {}
    for task in tasks:
        title_counts[task.title] = title_counts.get(task.title, 0) + 1
    return {
        task.id: f"{task.title} #{task.id}" if title_counts.get(task.title, 0) > 1 else task.title
        for task in tasks
    }


def build_student_task_score_export(
    db: Session,
    teacher_id: str,
    course_id: int = None,
    class_id: int = None,
) -> list[dict]:
    """构建按课程分组的学生作业分数导出数据。"""
    course_query = db.query(Course).filter(Course.created_by == teacher_id)
    if course_id:
        course_query = course_query.filter(Course.id == course_id)
    courses = course_query.order_by(Course.id.asc()).all()

    selected_class: Class | None = None
    if class_id:
        selected_class = db.query(Class).filter(
            Class.id == class_id,
            Class.created_by == teacher_id,
        ).first()
        if not selected_class:
            return []
        if course_id and selected_class.course_id != course_id:
            return []
        courses = [course for course in courses if course.id == selected_class.course_id]

    groups = []
    for course in courses:
        class_query = db.query(Class).filter(
            Class.created_by == teacher_id,
            Class.course_id == course.id,
        )
        if selected_class:
            class_query = class_query.filter(Class.id == selected_class.id)
        classes = class_query.order_by(Class.id.asc()).all()
        class_ids = [cls.id for cls in classes]
        if not class_ids:
            groups.append({
                "course_id": course.id,
                "course_name": course.name,
                "tasks": [],
                "students": [],
            })
            continue

        tasks = (
            db.query(Announcement)
            .filter(
                Announcement.teacher_id == teacher_id,
                Announcement.type == "quiz",
                Announcement.course_id == course.id,
            )
            .order_by(Announcement.created_at.asc(), Announcement.id.asc())
            .all()
        )
        task_ids = [task.id for task in tasks]
        task_class_rows = (
            db.query(AnnouncementClass.announcement_id, AnnouncementClass.class_id)
            .filter(
                AnnouncementClass.announcement_id.in_(task_ids),
                AnnouncementClass.class_id.in_(class_ids),
            )
            .all()
        ) if task_ids else []
        task_class_ids: dict[int, set[int]] = {}
        for task_id, owned_class_id in task_class_rows:
            task_class_ids.setdefault(task_id, set()).add(owned_class_id)
        tasks = [task for task in tasks if task_class_ids.get(task.id)]
        task_ids = [task.id for task in tasks]

        rows = (
            db.query(User, StudentClassEnrollment, Class)
            .join(StudentClassEnrollment, StudentClassEnrollment.user_id == User.id)
            .join(Class, Class.id == StudentClassEnrollment.class_id)
            .filter(User.role == "student", StudentClassEnrollment.class_id.in_(class_ids))
            .order_by(Class.id.asc(), StudentClassEnrollment.import_order.asc(), User.id.asc())
            .all()
        )

        student_class_ids: dict[str, set[int]] = {}
        student_class_names: dict[str, list[str]] = {}
        student_first_enrollment: dict[str, StudentClassEnrollment] = {}
        student_user: dict[str, User] = {}
        for student, enrollment, class_ in rows:
            student_class_ids.setdefault(student.id, set()).add(class_.id)
            names = student_class_names.setdefault(student.id, [])
            if class_.name not in names:
                names.append(class_.name)
            if student.id not in student_first_enrollment:
                student_first_enrollment[student.id] = enrollment
            student_user[student.id] = student

        student_ids = list(student_user.keys())
        completed_rows = (
            db.query(TaskCompletion.user_id, TaskCompletion.announcement_id)
            .filter(
                TaskCompletion.user_id.in_(student_ids),
                TaskCompletion.announcement_id.in_(task_ids),
            )
            .all()
        ) if student_ids and task_ids else []
        completed_task_ids: dict[str, set[int]] = {sid: set() for sid in student_ids}
        for user_id, task_id in completed_rows:
            completed_task_ids.setdefault(user_id, set()).add(task_id)

        task_question_counts = {
            task.id: len(task.question_ids if isinstance(task.question_ids, list) else [])
            for task in tasks
        }
        task_scores = _latest_task_scores(db, task_ids, task_question_counts)
        task_titles = _ordered_task_header_titles(tasks)

        student_ids.sort(key=lambda sid: (
            min(student_class_ids[sid]) if student_class_ids[sid] else 0,
            student_first_enrollment[sid].import_order or 0,
            sid,
        ))

        students = []
        for sid in student_ids:
            student = student_user[sid]
            assigned_task_ids = {
                task.id
                for task in tasks
                if student_class_ids.get(sid, set()).intersection(task_class_ids.get(task.id, set()))
            }
            completed_count = len(assigned_task_ids & completed_task_ids.get(sid, set()))
            total_task_count = len(assigned_task_ids)
            incomplete_count = max(total_task_count - completed_count, 0)
            task_completion_rate = int(round(completed_count / total_task_count * 100)) if total_task_count else 0
            students.append({
                "serial_no": student_first_enrollment[sid].import_order or 0,
                "id": sid,
                "name": student.name,
                "major": student.major or "",
                "class_name": "、".join(student_class_names[sid]),
                "completed_tasks": completed_count,
                "incomplete_tasks": incomplete_count,
                "task_completion_rate": task_completion_rate,
                "scores": {
                    task.id: task_scores.get((sid, task.id)) if task.id in assigned_task_ids else None
                    for task in tasks
                },
            })

        groups.append({
            "course_id": course.id,
            "course_name": course.name,
            "tasks": [
                {"id": task.id, "title": task_titles[task.id]}
                for task in tasks
            ],
            "students": students,
        })

    return groups


def list_all_projects(
    db: Session,
    status: str = None,
    page: int = None,
    page_size: int = None,
    teacher_id: str | None = None,
    keyword: str | None = None,
):
    query = db.query(Project)
    if teacher_id:
        query = _apply_teacher_project_scope(query, db, teacher_id)
    if status:
        query = query.filter(Project.status == status)
    if keyword:
        query = query.filter(Project.title.like(f"%{keyword}%"))
    query = query.order_by(Project.date.desc())
    total = query.count()
    if page and page_size:
        projects = query.offset((page - 1) * page_size).limit(page_size).all()
    else:
        projects = query.all()
    return projects, total
