"""课程 cleanup MySQL 验证脚本的安全门禁测试。"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "verify_course_cleanup_mysql.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("verify_course_cleanup_mysql_test", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _valid_env() -> dict[str, str]:
    return {
        "MYSQL_VERIFY_URL": "mysql+pymysql://verify_user:secret@127.0.0.1:3306/tongshi_verify_cleanup?charset=utf8mb4",
        "MYSQL_VERIFY_ADMIN_URL": "mysql+pymysql://verify_admin:secret@127.0.0.1:3306/?charset=utf8mb4",
        "MYSQL_VERIFY_ALLOW_RESET": "1",
    }


def test_verify_config_requires_urls_before_any_database_work(monkeypatch):
    module = _load_script_module()
    called = []
    monkeypatch.setattr(module, "run_verification", lambda config: called.append(config))

    exit_code = module.main(["--reset", "--confirm-db", "tongshi_verify_cleanup"], environ={})

    assert exit_code == 1
    assert called == []


def test_verify_script_import_does_not_load_project_dotenv():
    """验证脚本导入时不得触发项目运行时配置或读取 .env。"""
    probe = f"""
import importlib.util
from pathlib import Path
import sys
import dotenv

def reject_dotenv(*args, **kwargs):
    raise AssertionError('验证脚本导入时不应读取项目 .env')

dotenv.load_dotenv = reject_dotenv
script_path = Path({str(SCRIPT_PATH)!r})
spec = importlib.util.spec_from_file_location('verify_course_cleanup_import_probe', script_path)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)
"""
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=SCRIPT_PATH.parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("argv", "env"),
    [
        (
            ["--confirm-db", "tongshi_verify_cleanup"],
            _valid_env(),
        ),
        (
            ["--reset", "--confirm-db", "tongshi_verify_cleanup"],
            {key: value for key, value in _valid_env().items() if key != "MYSQL_VERIFY_ALLOW_RESET"},
        ),
        (
            ["--reset", "--confirm-db", "tongshi"],
            _valid_env(),
        ),
    ],
)
def test_verify_config_rejects_missing_reset_guard_or_formal_database(monkeypatch, argv, env):
    module = _load_script_module()
    called = []
    monkeypatch.setattr(module, "run_verification", lambda config: called.append(config))

    exit_code = module.main(argv, environ=env)

    assert exit_code == 1
    assert called == []


def test_verify_config_uses_only_verified_database_and_redacts_password(tmp_path):
    module = _load_script_module()
    config = module.build_verify_config(
        ["--reset", "--confirm-db", "tongshi_verify_cleanup", "--output-dir", str(tmp_path)],
        environ=_valid_env(),
    )

    assert config.database_name == "tongshi_verify_cleanup"
    assert config.output_dir == tmp_path
    assert "secret" not in module.redact_url(config.verify_url)
    assert "***" in module.redact_url(config.verify_url)


def test_verify_config_rejects_admin_connection_to_another_mysql_instance(monkeypatch):
    """管理连接必须与验证连接指向同一 MySQL 实例，避免跨实例重置。"""
    module = _load_script_module()
    called = []
    monkeypatch.setattr(module, "run_verification", lambda config: called.append(config))
    env = _valid_env()
    env["MYSQL_VERIFY_ADMIN_URL"] = "mysql+pymysql://verify_admin:secret@127.0.0.2:3306/?charset=utf8mb4"

    exit_code = module.main(["--reset", "--confirm-db", "tongshi_verify_cleanup"], environ=env)

    assert exit_code == 1
    assert called == []


@pytest.mark.parametrize(
    ("env_name", "url"),
    [
        (
            "MYSQL_VERIFY_URL",
            "mysql+pymysql://verify_user:secret@127.0.0.1:3306/tongshi_verify_cleanup?host=127.0.0.2",
        ),
        (
            "MYSQL_VERIFY_ADMIN_URL",
            "mysql+pymysql://verify_admin:secret@127.0.0.1:3306/?unix_socket=%2Ftmp%2Fmysql.sock",
        ),
    ],
    ids=("verify_url_host_override", "admin_url_socket_override"),
)
def test_verify_config_rejects_query_connection_overrides(monkeypatch, env_name, url):
    """验证 DSN 不能通过查询参数绕过同实例校验。"""
    module = _load_script_module()
    called = []
    monkeypatch.setattr(module, "run_verification", lambda config: called.append(config))
    env = _valid_env()
    env[env_name] = url

    exit_code = module.main(["--reset", "--confirm-db", "tongshi_verify_cleanup"], environ=env)

    assert exit_code == 1
    assert called == []


def test_redact_url_masks_sensitive_query_parameters():
    """DSN 的 userinfo 和查询参数中的敏感值都不得进入输出。"""
    module = _load_script_module()
    value = (
        "mysql+pymysql://verify_user:login-secret@127.0.0.1:3306/"
        "tongshi_verify_cleanup?password=query-secret&token=query-token&api_key=query-key&charset=utf8mb4"
    )

    redacted = module.redact_url(value)

    assert "login-secret" not in redacted
    assert "query-secret" not in redacted
    assert "query-token" not in redacted
    assert "query-key" not in redacted
    assert "charset=utf8mb4" in redacted
    assert "***" in redacted


def test_verify_config_rejects_non_verification_database(monkeypatch):
    """验证 URL 自身指向非专用库时必须在任何连接前拒绝。"""
    module = _load_script_module()
    called = []
    monkeypatch.setattr(module, "run_verification", lambda config: called.append(config))
    env = _valid_env()
    env["MYSQL_VERIFY_URL"] = "mysql+pymysql://verify_user:secret@127.0.0.1:3306/tongshi?charset=utf8mb4"

    exit_code = module.main(["--reset", "--confirm-db", "tongshi"], environ=env)

    assert exit_code == 1
    assert called == []


def test_fk_matrix_requires_every_declared_course_reference():
    module = _load_script_module()
    expected = module.expected_course_fk_specs()
    matrix = [
        {
            "table_name": table,
            "column_name": column,
            "delete_rule": spec["delete_rule"],
            "is_nullable": spec["is_nullable"],
        }
        for (table, column), spec in expected.items()
    ]

    module.assert_fk_matrix(matrix)

    with pytest.raises(AssertionError, match="缺少|不一致"):
        module.assert_fk_matrix(matrix[:-1])
