"""Seed data for the tongshi AI course platform"""

from app.db.session import SessionLocal
from app.models.entities import Course, User


# 仅保留非敏感共享种子，禁止在此处创建默认管理员或其他默认账号。
_SEED_USERS: list[tuple[str, str, str, str]] = []


def seed():
    db = SessionLocal()

    for uid, name, role, pwd in _SEED_USERS:
        existing = db.query(User).filter(User.id == uid).first()
        if existing:
            print(f"  {role} {uid} 已存在，跳过")
            continue
        print(f"  跳过敏感账号创建: {uid}")

    public_course_names: list[str] = []
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
