"""真实 MySQL：课程引用脱钩与 cleanup 验收脚本。

完整验证只允许操作名称符合 ``tongshi_verify_*`` 的专用数据库，且必须
显式开启重置开关。脚本不会读取项目 ``.env``，避免误用正式库连接。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

# 允许直接 python scripts/xxx.py
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import sessionmaker

from app.core.timezone_utils import BEIJING_TZ
from app.db.schema_compat import ensure_schema_compatibility
from app.db.base import Base
from app.models.entities import (
    Announcement,
    Class,
    Course,
    HistorySnapshot,
    Material,
    Project,
    Question,
    QuestionContributionLog,
    User,
)
from app.services.soft_delete_cleanup_service import cleanup_expired_resources


VERIFY_DATABASE_PATTERN = re.compile(r"^tongshi_verify_[a-z0-9_]+$")
SENSITIVE_QUERY_PARAMETER_NAMES = {
    "access_token",
    "api_key",
    "apikey",
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
}
CONNECTION_OVERRIDE_QUERY_PARAMETER_NAMES = {
    "host",
    "port",
    "read_default_file",
    "read_default_group",
    "unix_socket",
}
FIXED_SUNDAY = datetime(2026, 2, 15, 3, 0, tzinfo=BEIJING_TZ)


@dataclass(frozen=True)
class VerifyConfig:
    """已通过安全校验的 MySQL 验证配置。"""

    verify_url: str
    admin_url: str
    database_name: str
    output_dir: Path
    scenario: str


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="课程 cleanup MySQL 验证（仅限专用验证库）")
    parser.add_argument("--reset", action="store_true", help="允许重置专用验证库")
    parser.add_argument("--confirm-db", default="", help="必须精确填写验证库名称")
    parser.add_argument(
        "--scenario",
        choices=("fresh", "legacy-upgrade", "all"),
        default="all",
        help="fresh 验证全新库；legacy-upgrade 验证旧结构升级；默认执行两者",
    )
    parser.add_argument("--output-dir", default="", help="矩阵报告输出目录，默认使用系统临时目录")
    return parser.parse_args(argv)


def _parse_mysql_url(name: str, value: str) -> URL:
    if not value:
        raise ValueError(f"{name} 未配置")
    try:
        url = make_url(value)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"{name} 格式无效") from exc
    if url.get_backend_name() != "mysql":
        raise ValueError(f"{name} 必须使用 mysql+pymysql 连接")
    return url


def redact_url(value: str) -> str:
    """隐藏 DSN 中的口令，供控制台和 JSON 报告使用。"""
    url = make_url(value)
    safe_query = {
        key: "***" if key.lower() in SENSITIVE_QUERY_PARAMETER_NAMES else item
        for key, item in url.query.items()
    }
    return url.set(query=safe_query).render_as_string(hide_password=True)


def _mysql_instance_identity(url: URL) -> tuple[str, int]:
    """返回用于重置前安全比对的 MySQL 实例地址。"""
    return ((url.host or "").lower(), url.port or 3306)


def _reject_connection_override_query_parameters(name: str, url: URL) -> None:
    """禁止用查询参数改变连接实例，保证重置前的地址比对可信。"""
    overrides = sorted(
        key
        for key in url.query
        if key.lower() in CONNECTION_OVERRIDE_QUERY_PARAMETER_NAMES
    )
    if overrides:
        raise ValueError(f"{name} 不允许通过查询参数指定连接地址: {', '.join(overrides)}")


def build_verify_config(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> VerifyConfig:
    """在任何数据库连接前完成全部安全门禁校验。"""
    args = parse_args(argv)
    env = os.environ if environ is None else environ
    verify_url = str(env.get("MYSQL_VERIFY_URL", "")).strip()
    admin_url = str(env.get("MYSQL_VERIFY_ADMIN_URL", "")).strip()
    verify = _parse_mysql_url("MYSQL_VERIFY_URL", verify_url)
    _reject_connection_override_query_parameters("MYSQL_VERIFY_URL", verify)
    database_name = str(verify.database or "")
    if not VERIFY_DATABASE_PATTERN.fullmatch(database_name):
        raise ValueError("MYSQL_VERIFY_URL 只能指向 tongshi_verify_* 专用验证库")
    if not args.reset:
        raise ValueError("完整验证必须显式传入 --reset")
    if str(env.get("MYSQL_VERIFY_ALLOW_RESET", "")) != "1":
        raise ValueError("必须设置 MYSQL_VERIFY_ALLOW_RESET=1 才能重置验证库")
    if args.confirm_db != database_name:
        raise ValueError("--confirm-db 必须与 MYSQL_VERIFY_URL 的验证库名完全一致")

    admin = _parse_mysql_url("MYSQL_VERIFY_ADMIN_URL", admin_url)
    _reject_connection_override_query_parameters("MYSQL_VERIFY_ADMIN_URL", admin)
    if admin.database not in (None, "", database_name):
        raise ValueError("MYSQL_VERIFY_ADMIN_URL 只能不指定数据库或指向同一验证库")
    if _mysql_instance_identity(admin) != _mysql_instance_identity(verify):
        raise ValueError("MYSQL_VERIFY_ADMIN_URL 必须与 MYSQL_VERIFY_URL 指向同一 MySQL 实例")

    output_dir = (
        Path(args.output_dir).expanduser()
        if args.output_dir
        else Path(tempfile.gettempdir()) / "tongshi-mysql-verify" / uuid.uuid4().hex
    )
    return VerifyConfig(
        verify_url=verify_url,
        admin_url=admin_url,
        database_name=database_name,
        output_dir=output_dir,
        scenario=args.scenario,
    )


def _as_utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def reset_database(config: VerifyConfig) -> None:
    """仅在已经验证过的专用库上执行 DROP/CREATE。"""
    admin = create_engine(config.admin_url, pool_pre_ping=True)
    try:
        with admin.begin() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS `{config.database_name}`"))
            conn.execute(text(
                f"CREATE DATABASE `{config.database_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            ))
    finally:
        admin.dispose()


def export_fk_matrix(engine) -> list[dict[str, str]]:
    sql = text(
        """
        SELECT
            k.TABLE_NAME AS table_name,
            k.COLUMN_NAME AS column_name,
            k.CONSTRAINT_NAME AS constraint_name,
            r.DELETE_RULE AS delete_rule,
            r.UPDATE_RULE AS update_rule,
            c.IS_NULLABLE AS is_nullable
        FROM information_schema.KEY_COLUMN_USAGE k
        JOIN information_schema.REFERENTIAL_CONSTRAINTS r
          ON k.CONSTRAINT_SCHEMA = r.CONSTRAINT_SCHEMA
         AND k.CONSTRAINT_NAME = r.CONSTRAINT_NAME
         AND k.TABLE_NAME = r.TABLE_NAME
        JOIN information_schema.COLUMNS c
          ON c.TABLE_SCHEMA = k.TABLE_SCHEMA
         AND c.TABLE_NAME = k.TABLE_NAME
         AND c.COLUMN_NAME = k.COLUMN_NAME
        WHERE k.TABLE_SCHEMA = DATABASE()
          AND k.REFERENCED_TABLE_NAME = 'courses'
          AND k.REFERENCED_COLUMN_NAME = 'id'
        ORDER BY k.TABLE_NAME, k.COLUMN_NAME, k.CONSTRAINT_NAME
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().all()
    return [dict(row) for row in rows]


def _normalize_delete_rule(value: str | None) -> str:
    rule = (value or "RESTRICT").upper()
    return "RESTRICT" if rule == "NO ACTION" else rule


def expected_course_fk_specs() -> dict[tuple[str, str], dict[str, str]]:
    """从 ORM 元数据导出所有应指向 courses.id 的外键约束。"""
    specs: dict[tuple[str, str], dict[str, str]] = {}
    for table in Base.metadata.tables.values():
        for constraint in table.foreign_key_constraints:
            for element in constraint.elements:
                target_column = element.column
                if target_column.table.name != "courses" or target_column.name != "id":
                    continue
                local_column = element.parent
                specs[(table.name, local_column.name)] = {
                    "delete_rule": _normalize_delete_rule(element.ondelete),
                    "is_nullable": "YES" if local_column.nullable else "NO",
                }
    return specs


def assert_fk_matrix(matrix: list[dict[str, str]]) -> None:
    """矩阵必须覆盖全部已声明课程引用，不能遗漏或混入未知引用。"""
    expected = expected_course_fk_specs()
    actual: dict[tuple[str, str], dict[str, str]] = {}
    duplicates: list[tuple[str, str]] = []
    for row in matrix:
        key = (row["table_name"], row["column_name"])
        if key in actual:
            duplicates.append(key)
        actual[key] = {
            "delete_rule": _normalize_delete_rule(row.get("delete_rule")),
            "is_nullable": str(row.get("is_nullable", "")).upper(),
        }

    missing = sorted(set(expected) - set(actual))
    unexpected = sorted(set(actual) - set(expected))
    mismatches = [
        (key, expected[key], actual[key])
        for key in sorted(set(expected) & set(actual))
        if expected[key] != actual[key]
    ]
    if missing or unexpected or duplicates or mismatches:
        raise AssertionError(
            "课程外键矩阵不一致: "
            f"缺少={missing}; 多余={unexpected}; 重复={duplicates}; 规则不符={mismatches}"
        )


def _drop_and_add_legacy_restrict_foreign_key(conn, row: dict[str, str]) -> None:
    """将可脱钩外键暂时模拟为旧库的 RESTRICT 规则。"""
    table = row["table_name"]
    column = row["column_name"]
    constraint = row["constraint_name"]
    conn.execute(text(f"ALTER TABLE `{table}` DROP FOREIGN KEY `{constraint}`"))
    conn.execute(text(
        f"ALTER TABLE `{table}` ADD CONSTRAINT `legacy_{table}_{column}` "
        f"FOREIGN KEY (`{column}`) REFERENCES courses(id) ON DELETE RESTRICT"
    ))


def seed_legacy_upgrade_state(engine) -> dict[str, int | str]:
    """构造带有旧课程引用和空快照的非空数据库，用于升级验证。"""
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    try:
        operator = User(id="MYSQL_LEG", name="旧库验证教师", hashed_password="hash", role="teacher")
        student = User(id="MYSQL_LEG_STU", name="旧库验证学生", hashed_password="hash", role="student")
        session.add_all([operator, student])
        session.flush()
        source = Course(name="MySQL旧结构课程", created_by=operator.id, is_public=True)
        session.add(source)
        session.flush()
        copy = Course(
            name="MySQL旧结构副本",
            created_by=operator.id,
            source_course_id=source.id,
            question_bank_root_course_id=source.id,
        )
        question = Question(
            course_id=source.id,
            type="fill",
            stem="旧结构题目快照回填",
            options=[],
            answer="答案",
            created_by=operator.id,
            mount_course_name_snapshot="",
        )
        material = Material(
            course_id=source.id,
            type="link",
            title="旧结构资料",
            url="https://example.com/legacy-material",
        )
        project = Project(
            title="旧结构作品",
            description="用于验证旧结构升级",
            author_id=student.id,
            course_id=source.id,
            status="approved",
        )
        session.add_all([copy, question, material, project])
        session.commit()
        return {
            "source_course_id": source.id,
            "copy_course_id": copy.id,
            "question_id": question.id,
            "source_course_name": source.name,
        }
    finally:
        session.close()


def simulate_legacy_course_references(engine) -> None:
    """模拟旧库的 NOT NULL 列和 RESTRICT 外键，交给兼容逻辑修复。"""
    matrix = export_fk_matrix(engine)
    expected = expected_course_fk_specs()
    with engine.begin() as conn:
        for row in matrix:
            key = (row["table_name"], row["column_name"])
            if expected.get(key, {}).get("delete_rule") == "SET NULL":
                _drop_and_add_legacy_restrict_foreign_key(conn, row)
        conn.execute(text("ALTER TABLE questions MODIFY course_id INTEGER NOT NULL"))
        conn.execute(text("ALTER TABLE materials MODIFY course_id INTEGER NOT NULL"))
        conn.execute(text("ALTER TABLE question_contribution_logs MODIFY public_course_id INTEGER NOT NULL"))


def assert_legacy_upgrade_state(engine, state: Mapping[str, int | str]) -> None:
    """验证兼容逻辑已恢复可空约束、快照及历史 root 语义。"""
    inspector = inspect(engine)
    for table, column in (
        ("questions", "course_id"),
        ("materials", "course_id"),
        ("question_contribution_logs", "public_course_id"),
    ):
        columns = {item["name"]: item for item in inspector.get_columns(table)}
        assert columns[column]["nullable"], f"{table}.{column} 应升级为可空"

    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    try:
        question = session.get(Question, int(state["question_id"]))
        copy = session.get(Course, int(state["copy_course_id"]))
        assert question is not None
        assert question.mount_course_name_snapshot == state["source_course_name"]
        assert copy is not None
        assert copy.question_bank_root_course_id is None
    finally:
        session.close()


def run_cleanup_scenario(SessionLocal) -> dict[str, Any]:
    """构造到期课程及其引用，验证 cleanup 后的脱钩和快照行为。"""
    session = SessionLocal()
    try:
        operator = User(
            id="MYSQL_CLN",
            name="MySQL清理教师",
            hashed_password="hash",
            role="teacher",
        )
        student = User(
            id="MYSQL_STU",
            name="MySQL学生",
            hashed_password="hash",
            role="student",
        )
        session.add_all([operator, student])
        session.flush()

        deleted_at = datetime(2026, 1, 15, 3, 0, tzinfo=BEIJING_TZ)
        course = Course(
            name="MySQL到期清理课程",
            created_by="MYSQL_CLN",
            is_public=True,
            deleted_at=_as_utc_naive(deleted_at),
            deleted_by="MYSQL_CLN",
        )
        session.add(course)
        session.flush()

        teacher_copy = Course(
            name="教师副本课",
            created_by="MYSQL_CLN",
            source_course_id=course.id,
            question_bank_root_course_id=course.id,
        )
        cls = Class(
            name="同批班级",
            course_id=course.id,
            created_by="MYSQL_CLN",
            deleted_at=_as_utc_naive(deleted_at),
            deleted_by="MYSQL_CLN",
        )
        material = Material(
            course_id=course.id,
            type="link",
            title="同批资料",
            url="https://example.com/mysql-batch",
            deleted_at=_as_utc_naive(deleted_at),
            deleted_by="MYSQL_CLN",
        )
        separate_material = Material(
            course_id=course.id,
            type="link",
            title="独立软删资料",
            url="https://example.com/mysql-separate",
            deleted_at=_as_utc_naive(deleted_at - timedelta(days=1)),
            deleted_by="MYSQL_CLN",
        )
        announcement = Announcement(
            course_id=course.id,
            teacher_id="MYSQL_CLN",
            type="quiz",
            title="同批作业",
            question_ids=[],
            deleted_at=_as_utc_naive(deleted_at),
            deleted_by="MYSQL_CLN",
        )
        question = Question(
            course_id=course.id,
            type="choice",
            stem="MySQL共享题应脱钩保留",
            options=["A", "B"],
            answer="A",
            created_by="MYSQL_CLN",
            mount_course_name_snapshot="",
        )
        project = Project(
            title="MySQL作品应脱钩保留",
            description="cleanup 后 course_id 置空",
            author_id="MYSQL_STU",
            course_id=course.id,
            status="approved",
        )
        session.add_all([teacher_copy, cls, material, separate_material, announcement, question, project])
        session.commit()

        course_id = course.id
        question_id = question.id
        project_id = project.id
        separate_id = separate_material.id
        copy_id = teacher_copy.id
        course_name = course.name

        result = cleanup_expired_resources(session, now=FIXED_SUNDAY)
        assert result["cleaned_count"] >= 1, f"期望至少清理 1 项，实际 {result}"
        assert session.get(Course, course_id) is None, "课程应被物理删除"

        surviving_q = session.get(Question, question_id)
        assert surviving_q is not None and surviving_q.deleted_at is None
        assert surviving_q.course_id is None
        assert surviving_q.mount_course_name_snapshot == course_name

        surviving_p = session.get(Project, project_id)
        assert surviving_p is not None and surviving_p.course_id is None

        detached_m = session.get(Material, separate_id)
        assert detached_m is not None and detached_m.course_id is None
        assert detached_m.deleted_at is not None

        copy = session.get(Course, copy_id)
        assert copy is not None
        assert copy.source_course_id is None
        assert copy.question_bank_root_course_id is None

        child_snapshot_count = (
            session.query(HistorySnapshot)
            .filter(HistorySnapshot.resource_type.in_(["classes", "materials", "announcements"]))
            .count()
        )
        assert child_snapshot_count >= 1, "同批子资源应产生历史快照"
        return {
            "cleanup_result": result,
            "history_snapshot_child_count": child_snapshot_count,
        }
    finally:
        session.close()


def _mysql_version(engine) -> str:
    with engine.connect() as conn:
        return str(conn.execute(text("SELECT VERSION()")).scalar_one())


def run_scenario(config: VerifyConfig, scenario: str) -> dict[str, Any]:
    reset_database(config)
    engine = create_engine(config.verify_url, pool_pre_ping=True, pool_recycle=3600)
    try:
        Base.metadata.create_all(bind=engine)
        legacy_state: dict[str, int | str] | None = None
        if scenario == "legacy-upgrade":
            legacy_state = seed_legacy_upgrade_state(engine)
            simulate_legacy_course_references(engine)

        ensure_schema_compatibility(engine)
        matrix = export_fk_matrix(engine)
        assert_fk_matrix(matrix)
        if legacy_state is not None:
            assert_legacy_upgrade_state(engine, legacy_state)

        SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        cleanup = run_cleanup_scenario(SessionLocal)
        return {
            "scenario": scenario,
            "mysql_version": _mysql_version(engine),
            "matrix": matrix,
            **cleanup,
        }
    finally:
        engine.dispose()


def _write_report(config: VerifyConfig, result: Mapping[str, Any]) -> Path:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    path = config.output_dir / f"{result['scenario']}-fk-matrix.json"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verify_url": redact_url(config.verify_url),
        "database": config.database_name,
        **result,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path


def run_verification(config: VerifyConfig) -> list[Path]:
    """执行已通过安全校验的真实 MySQL 场景。"""
    scenarios = ("fresh", "legacy-upgrade") if config.scenario == "all" else (config.scenario,)
    paths: list[Path] = []
    for scenario in scenarios:
        print(f"== 验证场景: {scenario} ==")
        result = run_scenario(config, scenario)
        path = _write_report(config, result)
        paths.append(path)
        print(f"matrix_snapshot={path}")
        print(f"cleanup_result={result['cleanup_result']}")
    return paths


def main(argv: Sequence[str] | None = None, *, environ: Mapping[str, str] | None = None) -> int:
    try:
        config = build_verify_config(argv, environ=environ)
        print(f"验证库={config.database_name}")
        print(f"验证连接={redact_url(config.verify_url)}")
        run_verification(config)
    except Exception as exc:  # noqa: BLE001
        print("MYSQL_VERIFY_FAILED:", type(exc).__name__, exc)
        return 1
    print("ALL_MYSQL_VERIFY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
