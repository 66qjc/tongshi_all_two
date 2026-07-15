"""Portfolio service"""
import re
from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.entities import User, QuizAttempt, Project, StudentClassEnrollment, Class
from app.services.history_snapshot_service import history_attempt_totals, history_project_rows


def _derive_grade(db: Session, user_id: str) -> str:
    """从学生所属班级名中解析年级，例如 '2025级1班' → '2025 级'。

    无班级或无法解析时返回空字符串。
    """
    class_names = (
        db.query(Class.name)
        .join(StudentClassEnrollment, StudentClassEnrollment.class_id == Class.id)
        .filter(
            StudentClassEnrollment.user_id == user_id,
            Class.deleted_at.is_(None),
        )
        .all()
    )
    for (name,) in class_names:
        # 匹配 "20XX级" 或 "20XX" 开头
        m = re.search(r"(20\d{2})\s*级", name)
        if m:
            return f"{m.group(1)} 级"
        m = re.search(r"^(20\d{2})", name)
        if m:
            return f"{m.group(1)} 级"
    return ""


def get_portfolio(db: Session, user_id: str):
    user = db.query(User).filter(
        User.id == user_id,
        User.deleted_at.is_(None),
    ).first()
    if not user:
        return None

    live_attempts = db.query(QuizAttempt).filter(QuizAttempt.user_id == user_id).count()
    live_correct = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == user_id, QuizAttempt.is_correct == True,
    ).count()
    history_totals = history_attempt_totals(db, user_ids=[user_id]).get("totals", {})
    history_bucket = history_totals.get(user_id, {"attempts": 0, "correct": 0})
    attempts = live_attempts + int(history_bucket.get("attempts") or 0)
    correct = live_correct + int(history_bucket.get("correct") or 0)
    accuracy = int(correct / attempts * 100) if attempts > 0 else 0

    live_projects = db.query(Project).filter(
        Project.author_id == user_id,
        Project.status == "approved",
        Project.deleted_at.is_(None),
    ).all()
    history_projects = history_project_rows(db, user_ids=[user_id], approved_only=True)
    live_ids = {p.id for p in live_projects}
    merged_history = [item for item in history_projects if item["id"] not in live_ids]
    project_count = len(live_projects) + len(merged_history)

    # 作品平均点赞
    all_likes = [p.likes for p in live_projects] + [item.get("likes", 0) for item in merged_history]
    project_avg_likes = int(sum(all_likes) / len(all_likes)) if all_likes else 0
    # 精选/展示作品数
    featured_projects = sum(1 for p in live_projects if p.featured) + sum(
        1 for item in merged_history if item.get("featured")
    )
    # 学习持续天数（答题记录覆盖的 distinct 日期数）
    participation_days = 0
    earliest_attempt = (
        db.query(func.min(QuizAttempt.answered_at))
        .filter(QuizAttempt.user_id == user_id)
        .scalar()
    )
    if earliest_attempt:
        distinct_dates = (
            db.query(func.date(QuizAttempt.answered_at))
            .filter(QuizAttempt.user_id == user_id)
            .distinct()
            .count()
        )
        participation_days = distinct_dates

    # 雷达图六维数据
    radar = {
        "理论基础": min(100, attempts // 10),                      # 答题总量
        "实践能力": accuracy,                                       # 答题正确率
        "创新思维": min(100, project_count * 25),                  # 作品数量
        "团队协作": min(100, project_avg_likes * 10),              # 作品平均点赞数
        "社会传播": min(100, featured_projects * 33),              # 精选/展示作品数
        "伦理意识": min(100, int(participation_days / 180 * 100)), # 学习持续天数 / 180 天
    }

    timeline = []
    project_items = []
    for p in live_projects:
        timeline.append({
            "type": "create",
            "title": f"提交作品「{p.title}」",
            "date": p.date,
        })
        project_items.append({
            "id": p.id,
            "title": p.title,
            "author_id": p.author_id,
            "author_name": user.name,
            "major": p.major,
            "description": p.description,
            "tags": p.tags,
            "likes": p.likes,
            "featured": p.featured,
            "video_url": p.video_url,
            "report_url": p.report_url,
            "image_url": p.image_url,
            "status": p.status,
            "reject_reason": p.reject_reason,
            "date": p.date,
            "source": "live",
        })
    for item in merged_history:
        timeline.append({
            "type": "create",
            "title": f"提交作品「{item['title']}」",
            "date": item.get("date") or "",
        })
        project_items.append({
            "id": item["id"],
            "title": item["title"],
            "author_id": item.get("author_id") or user_id,
            "author_name": item.get("author_name") or user.name,
            "major": item.get("major") or "",
            "description": item.get("description") or "",
            "tags": item.get("tags") or [],
            "likes": item.get("likes") or 0,
            "featured": bool(item.get("featured")),
            # 清理后不返回可跳转详情 URL
            "video_url": "",
            "report_url": "",
            "image_url": "",
            "status": item.get("status") or "approved",
            "reject_reason": "",
            "date": item.get("date") or "",
            "source": "history_snapshot",
        })

    return {
        "user": {"id": user.id, "name": user.name, "role": user.role, "major": user.major, "grade": _derive_grade(db, user_id)},
        "stats": {
            "study_hours": int(attempts * 0.1),  # 估算：每次答题约 0.1 小时
            "total_exercises": attempts,
            "accuracy": accuracy,
            "project_count": project_count,
        },
        "radar": radar,
        "timeline": timeline,
        "projects": project_items,
    }
