from pathlib import Path
import shutil
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_env_example_defaults_to_local_storage():
    """生产示例配置应默认走本地持久化存储，不要求先部署 S3。"""
    content = (REPO_ROOT / "backend" / ".env.example").read_text(encoding="utf-8")

    assert "STORAGE_BACKEND=local" in content
    assert "LOCAL_UPLOAD_DIR=/data/tongshi/uploads" in content
    assert "# STORAGE_BACKEND=s3" in content
    assert "S3_ENDPOINT=http://localhost:8333" not in [
        line.strip() for line in content.splitlines() if not line.strip().startswith("#")
    ]


def test_nginx_config_proxies_api_uploads_and_range_headers():
    """Nginx 示例必须代理 API、兼容 uploads，并透传 Range 头。"""
    content = (REPO_ROOT / "deploy" / "nginx.conf").read_text(encoding="utf-8")

    assert "location /api/" in content
    assert "location /uploads/" in content
    assert "try_files $uri $uri/ /index.html;" in content
    assert "proxy_set_header Range $http_range;" in content
    assert "proxy_set_header If-Range $http_if_range;" in content
    assert "client_max_body_size 1024m;" in content


def test_upload_script_exposes_safe_parameters_and_upload_list():
    """上传脚本应支持可参数化同步，并且不把服务器信息写死。"""
    content = (REPO_ROOT / "deploy" / "upload-local-storage-deploy.ps1").read_text(encoding="utf-8")

    assert '[Alias("Host")]' in content
    assert "$ServerHost" in content
    assert "-DryRun" in content or "DryRun" in content
    assert "ssh" in content
    assert "scp" in content

    for expected_path in [
        "deploy/nginx.conf",
        "backend/scripts/check_deploy_env.py",
        "backend/.env.example",
        "backend/README.md",
        "frontend/.env.production.example",
        "frontend/README.md",
        "docs/superpowers/project-map.md",
    ]:
        assert expected_path in content


def test_upload_script_dry_run_executes_without_contacting_server():
    """DryRun 应能完成参数解析并打印 ssh/scp 命令，不实际连接服务器。"""
    powershell = shutil.which("pwsh") or shutil.which("powershell") or shutil.which("powershell.exe")
    if powershell is None:
        return

    command = [
        powershell,
        "-NoProfile",
    ]
    if Path(powershell).name.lower() in {"powershell", "powershell.exe"}:
        command.extend(["-ExecutionPolicy", "Bypass"])
    command.extend(
        [
            "-File",
            str(REPO_ROOT / "deploy" / "upload-local-storage-deploy.ps1"),
            "-Host",
            "example.com",
            "-User",
            "deploy",
            "-RemoteRoot",
            "/opt/tongshi",
            "-DryRun",
        ]
    )

    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)

    assert result.returncode == 0, result.stderr
    assert "[DryRun] ssh" in result.stdout
    assert "[DryRun] scp" in result.stdout
