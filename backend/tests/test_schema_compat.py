"""数据库结构兼容修复测试"""
from sqlalchemy import create_engine, inspect, text

from app.db.schema_compat import ensure_schema_compatibility


def test_ensure_schema_compatibility_adds_chapter_schedule_columns():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE chapters (
                id INTEGER PRIMARY KEY,
                num VARCHAR(8) NOT NULL,
                title VARCHAR(64) NOT NULL
            )
        """))

    ensure_schema_compatibility(engine)

    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("chapters")}

    assert {"day_of_week", "class_periods", "schedule_note"}.issubset(columns)
