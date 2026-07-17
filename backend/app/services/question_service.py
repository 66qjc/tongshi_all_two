"""题库与课程服务。"""
from __future__ import annotations

import re

from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session, joinedload

from app.core.cache import invalidate_cache
from app.core.exceptions import BusinessException
from app.models.entities import Class, Course, Material, Question, StudentClassEnrollment
from app.services.public_course_sync_service import mirror_public_course_content
from app.services.question_bank_service import (
    compute_stem_hash,
    count_all_questions,
    find_duplicate_question,
    find_same_stem_question,
)
from app.services.question_contribution_service import (
    record_question_contribution,
)


def _compute_stem_hash(stem: str) -> str:
    """兼容旧调用，统一委托共享题库哈希实现。"""
    return compute_stem_hash(stem)


def list_questions(
    db: Session,
    course_id: int | None = None,
    type_: str | None = None,
    teacher_id: str | None = None,
    keyword: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
    tag: str | None = None,
):
    # 全站共享题库：所有课程看到同一套活跃题；course_id 入参仅兼容旧调用。
    # teacher_id 仅供路由层标记 is_owner，不参与查询过滤。
    # 活跃性只看题目自身 deleted_at，课程软删不得隐藏题目。
    _ = (course_id, teacher_id)
    query = (
        db.query(Question)
        .options(joinedload(Question.creator), joinedload(Question.course))
        .filter(Question.deleted_at.is_(None))
    )
    if type_ is not None:
        query = query.filter(Question.type == type_)
    if keyword:
        query = query.filter(Question.stem.ilike(f"%{keyword.strip()}%"))
    tag_keyword = (tag or "").strip()
    if tag_keyword:
        # JSON 数组标签：文本包含模糊匹配，必须在分页前过滤以保持 total 正确。
        query = query.filter(cast(Question.tags, String).ilike(f"%{tag_keyword}%"))
    total = query.count()
    if page and page_size:
        questions = query.order_by(Question.id).offset((page - 1) * page_size).limit(page_size).all()
    else:
        questions = query.order_by(Question.id).all()
    return questions, total


def _normalize_tags(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = re.split(r"[,，、|/；;]+", str(value))
    seen = set()
    tags = []
    for item in raw_items:
        tag = str(item).strip()
        if tag and tag not in seen:
            seen.add(tag)
            tags.append(tag)
    return tags


def _row_value(row: dict, *keys: str):
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip() != "":
            return value
    return ""


def get_question(db: Session, question_id: int, teacher_id: str | None = None):
    query = (
        db.query(Question)
        .options(joinedload(Question.creator), joinedload(Question.course))
        .filter(Question.deleted_at.is_(None), Question.id == question_id)
    )
    if teacher_id is not None:
        query = query.filter(Question.created_by == teacher_id)
    return query.first()


def _get_owned_course(db: Session, course_id: int, teacher_id: str):
    return db.query(Course).filter(Course.id == course_id, Course.created_by == teacher_id, Course.deleted_at.is_(None)).first()


def _course_access_filter(teacher_id: str):
    return or_(Course.created_by == teacher_id, Course.is_public.is_(True))


def create_question(db: Session, data: dict, teacher_id: str):
    course = _get_owned_course(db, data["course_id"], teacher_id)
    if not course:
        raise BusinessException(404, "课程不存在")
    data["tags"] = _normalize_tags(data.get("tags"))

    # 计算题干哈希用于防重复
    stem = data.get("stem", "").strip()
    stem_hash = compute_stem_hash(stem)

    # 检查题干是否已存在（全站范围）
    existing = find_same_stem_question(db, stem)
    if existing:
        raise BusinessException(400, f"题库中已存在相同题目（ID: {existing.id}），请勿重复添加")

    # 全站共享题库：查重范围为全站所有题目
    duplicate = find_duplicate_question(
        db,
        data["type"],
        data["stem"],
        data.get("options"),
        data["answer"],
    )
    if duplicate:
        raise BusinessException(400, "题库中已存在相同题目")

    # 创建题目，添加创建人和哈希
    # 先从 data 中移除可能冲突的字段，然后显式设置
    question_data = {
        k: v
        for k, v in data.items()
        if k not in ["created_by", "stem_hash", "star_rating", "mount_course_name_snapshot"]
    }
    q = Question(
        **question_data,
        created_by=teacher_id,
        stem_hash=stem_hash,
        star_rating=data.get("star_rating", 3),  # 默认3星
        mount_course_name_snapshot=course.name or "",
    )
    db.add(q)
    db.flush()
    if course.is_public:
        record_question_contribution(db, course, teacher_id, "teacher", "create", 1)
    db.commit()
    db.refresh(q)
    return q


def update_question(db: Session, question_id: int, data: dict, teacher_id: str):
    q = get_question(db, question_id, teacher_id)
    if not q:
        return None
    if "course_id" in data and data["course_id"] is not None:
        if data["course_id"] != q.course_id and not _get_owned_course(db, data["course_id"], teacher_id):
            raise BusinessException(404, "课程不存在")
    # 全站共享题库：编辑后的内容在全站范围内查重，排除自身
    merged_data = {
        "type": data.get("type", q.type),
        "stem": data.get("stem", q.stem),
        "options": data.get("options", list(q.options or [])),
        "answer": data.get("answer", q.answer),
    }
    stem_hash = compute_stem_hash(str(merged_data["stem"] or ""))
    existing = find_same_stem_question(
        db,
        str(merged_data["stem"] or ""),
        exclude_question_id=q.id,
    )
    if existing:
        raise BusinessException(400, f"题库中已存在相同题目（ID: {existing.id}），请勿重复添加")
    duplicate = find_duplicate_question(
        db,
        merged_data["type"],
        merged_data["stem"],
        merged_data["options"],
        merged_data["answer"],
        exclude_question_id=q.id,
    )
    if duplicate:
        raise BusinessException(400, "题库中已存在相同题目")
    for key, value in data.items():
        if value is not None and hasattr(q, key):
            setattr(q, key, _normalize_tags(value) if key == "tags" else value)
    q.stem_hash = stem_hash
    db.commit()
    return q


def delete_question(db: Session, question_id: int, teacher_id: str):
    q = get_question(db, question_id, teacher_id)
    if not q:
        return False
    if q.source_question_id is not None:
        raise BusinessException(400, "公共课程同步内容不能删除")
    from app.schemas.common import AuthUser
    from app.services.soft_delete_service import soft_delete

    operator = AuthUser(id=teacher_id, name="", role="teacher")
    soft_delete(db, q, operator, action="question.delete")
    db.commit()
    return True


def get_course_questions(db: Session, course_id: int, student_user_id: str | None = None):
    """获取课程练习题目。

    - 教师/管理端：活跃课程入口返回全站活跃题（共享题库）
    - 学生端：仅返回可见题 = 公共课题 + 学生已加入活跃课程下的题
    """
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.deleted_at.is_(None),
    ).first()
    if not course:
        return []

    # 活跃题只看题目自身；学生侧再按挂载课程是否公共或是否在活跃选课中过滤。
    query = db.query(Question).outerjoin(Course, Course.id == Question.course_id).filter(
        Question.deleted_at.is_(None),
    )
    if student_user_id is not None:
        from app.services.access_control_service import student_has_active_course_enrollment
        from app.services.quiz_service import _student_active_course_ids

        if not student_has_active_course_enrollment(db, student_user_id):
            return []
        student_course_ids = _student_active_course_ids(db, student_user_id) or [-1]
        query = query.filter(
            or_(
                Question.course_id.is_(None),
                Course.is_public.is_(True),
                Question.course_id.in_(student_course_ids),
            )
        )
    return query.order_by(Question.id).all()


def can_view_course_questions(db: Session, course_id: int, user_id: str, role: str) -> bool:
    """校验课程题目访问权限：学生限所在活跃课程，教师限自有或公共活跃课程。"""
    if role == "student":
        from app.services.access_control_service import student_can_access_course
        return student_can_access_course(db, user_id, course_id)
    if role == "teacher":
        return db.query(Course).filter(
            Course.id == course_id,
            Course.deleted_at.is_(None),
            _course_access_filter(user_id),
        ).first() is not None
    return db.query(Course).filter(
        Course.id == course_id,
        Course.deleted_at.is_(None),
    ).first() is not None


def list_courses(db: Session, teacher_id: str | None = None, keyword: str | None = None):
    query = db.query(Course).filter(Course.deleted_at.is_(None))
    if teacher_id is not None:
        query = query.filter(_course_access_filter(teacher_id))
    if keyword:
        query = query.filter(Course.name.ilike(f"%{keyword.strip()}%"))
    return query.order_by(Course.is_public.asc(), Course.id.desc()).all()


def create_course(db: Session, name: str, teacher_id: str, description: str = "", is_public: bool = False):
    """创建课程"""
    if db.query(Course).filter(Course.name == name, Course.created_by == teacher_id).first():
        raise BusinessException(400, "课程已存在")
    course = Course(name=name, created_by=teacher_id, description=description, is_public=is_public)
    db.add(course)
    db.commit()
    db.refresh(course)
    # 清除课程列表缓存
    invalidate_cache(f"courses:teacher:{teacher_id}")
    return course


def add_public_course(db: Session, course_id: int, teacher_id: str):
    """添加公共课程到教师课程"""
    source = db.query(Course).filter(
        Course.id == course_id,
        Course.is_public.is_(True),
        Course.deleted_at.is_(None),
    ).first()
    if not source:
        raise BusinessException(404, "公共课程不存在")

    existing = db.query(Course).filter(Course.name == source.name, Course.created_by == teacher_id, Course.deleted_at.is_(None)).first()
    if existing:
        return existing

    course = Course(name=source.name, created_by=teacher_id,
                    description=source.description or "",
                    is_public=False, source_course_id=source.id)
    db.add(course)
    db.flush()

    mirror_public_course_content(db, source, course)

    db.commit()
    db.refresh(course)
    # 清除教师课程列表缓存
    invalidate_cache(f"courses:teacher:{teacher_id}")
    return course


def update_course(db: Session, course_id: int, name: str, teacher_id: str, description: str | None = None, is_public: bool | None = None):
    """更新课程"""
    course = _get_owned_course(db, course_id, teacher_id)
    if not course:
        return None
    if name != course.name:
        duplicate = db.query(Course).filter(
            Course.name == name,
            Course.created_by == teacher_id,
            Course.id != course_id,
        ).first()
        if duplicate:
            raise BusinessException(400, "课程已存在")
    course.name = name
    # 课程改名时同步活跃挂载题名称快照，便于后续脱钩展示
    db.query(Question).filter(
        Question.course_id == course.id,
        Question.deleted_at.is_(None),
    ).update({Question.mount_course_name_snapshot: name}, synchronize_session=False)
    if description is not None:
        course.description = description
    if is_public is not None:
        course.is_public = is_public
    db.commit()
    # 清除缓存
    invalidate_cache(f"course:detail:{course_id}")
    invalidate_cache(f"courses:teacher:{teacher_id}")
    return course


def delete_course(db: Session, course_id: int, teacher_id: str):
    """删除课程（软删除）"""
    course = _get_owned_course(db, course_id, teacher_id)
    if not course:
        return None
    from app.schemas.common import AuthUser
    from app.services.soft_delete_service import soft_delete

    operator = AuthUser(id=teacher_id, name="", role="teacher")
    soft_delete(db, course, operator, action="course.delete")
    db.commit()
    # 清除缓存
    invalidate_cache(f"course:detail:{course_id}")
    invalidate_cache(f"courses:teacher:{teacher_id}")
    return course


def get_course_detail(db: Session, course_id: int, teacher_id: str | None = None):
    """获取课程详情。

    不再缓存 ORM 返回值：实体绑定 Session，JSON 缓存无效且键不稳定。
    """
    query = db.query(Course).filter(Course.id == course_id, Course.deleted_at.is_(None))
    if teacher_id is not None:
        query = query.filter(_course_access_filter(teacher_id))
    course = query.first()
    if not course:
        return None
    material_count = db.query(Material).filter(Material.course_id == course_id, Material.deleted_at.is_(None)).count()
    # 全站共享题库：题目数为全站题目总数
    question_count = count_all_questions(db)
    class_count = db.query(Class).filter(Class.course_id == course_id, Class.deleted_at.is_(None)).count()
    return course, material_count, question_count, class_count


def import_questions_from_excel(db: Session, rows: list[dict], teacher_id: str, role: str = "teacher"):
    success_count = 0
    fail_count = 0
    skip_count = 0
    errors = []
    skips = []
    contribution_counts: dict[int, tuple[Course, int]] = {}
    for idx, row in enumerate(rows, start=2):
        try:
            course_name = str(_row_value(row, "课程名称", "课程", "course", "course_name")).strip()
            query = db.query(Course).filter(
                Course.name == course_name,
                Course.deleted_at.is_(None),
            )
            if role != "admin":
                query = query.filter(Course.created_by == teacher_id)
            course = query.first()
            if not course:
                raise BusinessException(400, f"未找到课程: {course_name}")
            q_type = str(_row_value(row, "题型", "type")).strip()
            stem = str(_row_value(row, "题干", "stem")).strip()
            if not stem:
                raise BusinessException(400, "题干为空")
            options = str(_row_value(row, "选项（选择题用 | 分隔）", "选项", "options")).strip()
            option_list = [x.strip() for x in options.split("|") if x.strip()] if options else []
            answer = str(_row_value(row, "答案", "answer")).strip()
            explanation = str(_row_value(row, "解析", "explanation")).strip()
            tags = _normalize_tags(_row_value(row, "标签", "课程标签", "tags", "course_tags"))
            if q_type not in {"choice", "fill", "multi_choice"}:
                raise BusinessException(400, "题型必须为 choice、fill 或 multi_choice")
            if q_type in {"choice", "multi_choice"} and not option_list:
                raise BusinessException(400, "选择题必须填写选项")
            # 与手工新增一致：先用题干 hash 做全站同题干拦截，再做完整指纹查重。
            stem_hash = compute_stem_hash(stem)
            existing = find_same_stem_question(db, stem)
            if existing:
                skip_count += 1
                skips.append({"row": idx, "reason": f"题库中已存在相同题目（题干: {stem[:50]}），已跳过"})
                continue
            # 全站共享题库：查重范围为全站所有题目
            duplicate = find_duplicate_question(
                db,
                q_type,
                stem,
                option_list,
                answer,
            )
            if duplicate:
                skip_count += 1
                skips.append({"row": idx, "reason": f"题库中已存在相同题目（题干: {stem[:50]}），已跳过"})
                continue
            # 题目原地保存，course_id 保留为匹配到的课程
            q = Question(
                type=q_type,
                course_id=course.id,
                stem=stem,
                options=option_list,
                answer=answer,
                explanation=explanation,
                tags=tags,
                created_by=teacher_id,
                stem_hash=stem_hash,
                star_rating=3,
                mount_course_name_snapshot=course.name or "",
            )
            db.add(q)
            db.flush()
            if course.is_public:
                _, count = contribution_counts.get(course.id, (course, 0))
                contribution_counts[course.id] = (course, count + 1)
            success_count += 1
        except Exception as exc:
            fail_count += 1
            errors.append({"row": idx, "reason": str(exc)})
    for public_course, count in contribution_counts.values():
        record_question_contribution(db, public_course, teacher_id, role, "import", count)
    db.commit()
    return {"success_count": success_count, "fail_count": fail_count, "skip_count": skip_count, "errors": errors, "skips": skips}
