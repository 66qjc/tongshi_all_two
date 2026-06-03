"""Seed data for the tongshi AI course platform"""
from datetime import datetime, timedelta, timezone

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.entities import Course, User


# 测试用种子账号：id, name, role, password（需要时取消注释）
_SEED_USERS: list[tuple[str, str, str, str]] = [
    # ("admin", "系统管理员", "admin", "admin123456"),
    # ("T001", "测试教师", "teacher", "abc123456"),
    # ("2025001", "测试学生一", "student", "abc123456"),
    # ("2025002", "测试学生二", "student", "abc123456"),
    # ("2025003", "测试学生三", "student", "abc123456"),
]


def seed():
    db = SessionLocal()

    for uid, name, role, pwd in _SEED_USERS:
        existing = db.query(User).filter(User.id == uid).first()
        if existing:
            print(f"  {role} {uid} 已存在，跳过")
            continue
        db.add(User(
            id=uid,
            name=name,
            role=role,
            hashed_password=get_password_hash(pwd),
            needs_password_change=False,
        ))
        db.commit()
        print(f"  已创建 {role}: {uid} / {pwd}")

    public_course_names = [
        "人工智能通识基础",
        "提示词工程入门",
        "数据素养与智能分析",
        "生成式 AI 应用实践",
        "AI 伦理与安全",
        "思想道德与法治",
        "中国近现代史纲要",
        "马克思主义基本原理",
        "毛泽东思想和中国特色社会主义理论体系概论",
        "形势与政策",
        "大学英语",
        "大学体育",
        "大学计算机基础",
        "高等数学",
        "线性代数",
        "概率论与数理统计",
        "大学物理",
        "军事理论",
        "劳动教育",
        "心理健康教育",
        "大学语文",
    ]
    for name in public_course_names:
        course = db.query(Course).filter(
            Course.name == name,
            Course.created_by == "admin",
        ).first()
        if course:
            course.is_public = True
        else:
            db.add(Course(name=name, created_by="admin", is_public=True))
    db.commit()

    db.close()
    print("Seed complete!")


if __name__ == "__main__":
    seed()
