"""数据库结构兼容修复"""
from sqlalchemy import inspect, text


def ensure_schema_compatibility(engine) -> None:
    """补齐旧数据库缺少的业务字段。"""
    with engine.begin() as conn:
        inspector = inspect(conn)
        table_names = set(inspector.get_table_names())
        if "chapters" not in table_names:
            return

        columns = {column["name"] for column in inspector.get_columns("chapters")}
        required_columns = [
            ("day_of_week", "VARCHAR(16)", "''"),
            ("class_periods", "VARCHAR(32)", "''"),
            ("schedule_note", "VARCHAR(128)", "''"),
        ]

        for name, column_type, default_value in required_columns:
            if name not in columns:
                conn.execute(text(
                    f"ALTER TABLE chapters ADD COLUMN {name} {column_type} DEFAULT {default_value}"
                ))
