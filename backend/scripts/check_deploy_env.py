"""部署前环境检查脚本。"""

from __future__ import annotations

import argparse
import socket
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse


@dataclass
class DeployCheckResult:
    """部署检查结果。"""

    ok: bool
    storage_backend: str
    messages: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _parse_env_file(env_file: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_file.exists():
        return values

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _can_connect(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _check_upload_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".deploy-write-check"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _check_mysql_url(database_url: str, result: DeployCheckResult, check_mysql: bool) -> None:
    if not database_url:
        result.errors.append("DATABASE_URL 必须显式配置")
        return
    if "root:123456@" in database_url:
        result.errors.append("DATABASE_URL 不能使用 root:123456 默认账号口令")
    parsed = urlparse(database_url)
    if check_mysql and parsed.hostname and parsed.port:
        if _can_connect(parsed.hostname, parsed.port):
            result.messages.append(f"MySQL 端口可连接: {parsed.hostname}:{parsed.port}")
        else:
            result.errors.append(f"MySQL 端口不可连接: {parsed.hostname}:{parsed.port}")


def check_deploy_env(
    env_file: str | Path,
    *,
    check_mysql: bool = True,
    check_s3: bool = True,
) -> DeployCheckResult:
    """检查部署环境配置，默认执行端口连通性检查。"""

    env_path = Path(env_file)
    values = _parse_env_file(env_path)
    storage_backend = values.get("STORAGE_BACKEND", "local").lower()
    result = DeployCheckResult(ok=True, storage_backend=storage_backend)

    secret_key = values.get("SECRET_KEY", "")
    if len(secret_key) < 32:
        result.errors.append("SECRET_KEY 长度必须至少 32 位")

    allowed_origins = values.get("ALLOWED_ORIGINS", "")
    if not allowed_origins:
        result.errors.append("ALLOWED_ORIGINS 必须显式配置")
    elif allowed_origins.strip() == "*":
        result.errors.append("生产环境 ALLOWED_ORIGINS 不能为 *")

    _check_mysql_url(values.get("DATABASE_URL", ""), result, check_mysql)

    if storage_backend == "local":
        upload_dir = Path(values.get("LOCAL_UPLOAD_DIR", "../uploads")).expanduser()
        if not upload_dir.is_absolute():
            upload_dir = (env_path.parent / upload_dir).resolve()
        if _check_upload_dir(upload_dir):
            result.messages.append(f"本地上传目录可写: {upload_dir}")
        else:
            result.errors.append(f"本地上传目录不可写: {upload_dir}")
    elif storage_backend == "s3":
        endpoint = values.get("S3_ENDPOINT", "")
        if not endpoint:
            result.errors.append("STORAGE_BACKEND=s3 时必须配置 S3_ENDPOINT")
        elif check_s3:
            parsed = urlparse(endpoint)
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            if parsed.hostname and _can_connect(parsed.hostname, port):
                result.messages.append(f"S3 端点可连接: {parsed.hostname}:{port}")
            else:
                result.errors.append(f"S3 端点不可连接: {endpoint}")
    else:
        result.errors.append("STORAGE_BACKEND 只能为 local 或 s3")

    result.ok = not result.errors
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="部署前环境检查")
    parser.add_argument("--env-file", default=str(Path(__file__).resolve().parents[1] / ".env"))
    parser.add_argument("--skip-mysql", action="store_true", help="跳过 MySQL 端口连通性检查")
    parser.add_argument("--skip-s3", action="store_true", help="跳过 S3 端口连通性检查")
    args = parser.parse_args()

    result = check_deploy_env(
        args.env_file,
        check_mysql=not args.skip_mysql,
        check_s3=not args.skip_s3,
    )
    for message in result.messages:
        print(f"[OK] {message}")
    for error in result.errors:
        print(f"[ERROR] {error}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
