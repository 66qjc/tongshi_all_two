"""Seed data for the tongshi AI course platform"""
from datetime import datetime, timedelta, timezone

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.entities import Course, User


def seed():
    db = SessionLocal()

    # 创建默认管理员账号（若不存在）
    admin_user = db.query(User).filter(User.id == "admin").first()
    if not admin_user:
        admin = User(
            id="admin",
            name="系统管理员",
            role="admin",
            hashed_password=get_password_hash("admin123456"),
            needs_password_change=False,
        )
        db.add(admin)
        db.commit()
        print("已创建默认管理员账号: admin / admin123456")
    else:
        print("  管理员账号已存在，跳过")

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
