from pathlib import Path
import os
import shutil
import subprocess

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


def _require_powershell() -> str:
    """返回可执行的 PowerShell；本机没有 PowerShell 时显式跳过依赖该环境的回归。"""
    powershell = shutil.which("pwsh") or shutil.which("powershell") or shutil.which("powershell.exe")
    if powershell is None:
        pytest.skip("本机未安装 PowerShell，无法运行部署脚本回归。")
    return powershell


def _extract_nginx_location_block(content: str, location_header: str) -> str:
    """返回指定 Nginx location 的完整花括号块，避免全文件字符串误判。"""
    start = content.index(location_header)
    opening_brace = content.index("{", start)
    depth = 0

    for index in range(opening_brace, len(content)):
        character = content[index]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return content[start : index + 1]

    raise AssertionError(f"Nginx location 块未闭合：{location_header}")


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
    assert "client_max_body_size 1050m;" in content


def test_nginx_config_streams_large_uploads_with_dedicated_timeouts_and_logs():
    """精确上传路由必须禁用请求缓冲并保留独立诊断日志。"""
    content = (REPO_ROOT / "deploy" / "nginx.conf").read_text(encoding="utf-8")
    upload_block = _extract_nginx_location_block(content, "location = /api/upload")

    assert "proxy_request_buffering off;" in upload_block
    assert "client_body_timeout 3600s;" in upload_block
    assert "proxy_read_timeout 3600s;" in upload_block
    assert "proxy_send_timeout 3600s;" in upload_block
    assert "access_log /var/log/nginx/tongshi.access.log combined;" in content
    assert "error_log /var/log/nginx/tongshi.error.log warn;" in content


def test_nginx_config_keeps_accel_uploads_internal_and_points_to_runtime_storage():
    """X-Accel 文件只能由内部跳转访问，并且必须映射到生产上传目录。"""
    content = (REPO_ROOT / "deploy" / "nginx.conf").read_text(encoding="utf-8")
    location_block = _extract_nginx_location_block(content, "location /_protected_uploads/")

    assert "internal;" in location_block
    assert "alias /data/tongshi/uploads/;" in location_block


def test_nginx_config_serves_es_module_workers_with_javascript_mime():
    """Vite 的 .mjs worker 配置必须完整限制在 /assets/ 专用 location 内。"""
    content = (REPO_ROOT / "deploy" / "nginx.conf").read_text(encoding="utf-8")
    location_block = _extract_nginx_location_block(content, r"location ~* ^/assets/.*\.mjs$")

    assert "types {" in location_block
    assert "application/javascript mjs;" in location_block
    assert "try_files $uri =404;" in location_block
    assert "expires 30d;" in location_block
    assert 'add_header Cache-Control "public, immutable";' in location_block
    assert r"location ~* \.mjs$" not in content


def test_redeploy_script_fetches_locked_commit_before_local_fast_forward():
    """真实部署必须只拉取一次确定对象，并从该对象本地快进。"""
    content = (REPO_ROOT / "deploy" / "redeploy-server.ps1").read_text(encoding="utf-8")

    assert "[string]$ExpectedCommit" in content
    assert "^[0-9a-fA-F]{7,64}$" in content
    assert "git status --porcelain=v1 --untracked-files=all" in content
    assert "git branch --show-current" in content
    assert "sudo -n true" in content
    assert "git pull" not in content
    assert "git ls-remote origin refs/heads/main" not in content
    assert content.count("git fetch --no-tags origin refs/heads/main") == 1
    assert "GIT_TERMINAL_PROMPT=0" in content
    assert "GIT_SSH_COMMAND=" in content
    assert 'FETCHED_COMMIT="$(git rev-parse FETCH_HEAD)"' in content
    assert 'EXPECTED_COMMIT="$FETCHED_COMMIT"' in content
    assert 'git merge-base --is-ancestor HEAD "$EXPECTED_COMMIT"' in content
    assert 'git merge --ff-only "$EXPECTED_COMMIT"' in content

    status_index = content.index("git status --porcelain=v1 --untracked-files=all")
    branch_index = content.index("git branch --show-current")
    sudo_index = content.index("sudo -n true")
    fetch_index = content.index("git fetch --no-tags origin refs/heads/main")
    fetched_commit_index = content.index('FETCHED_COMMIT="$(git rev-parse FETCH_HEAD)"')
    fast_forward_check_index = content.index('git merge-base --is-ancestor HEAD "$EXPECTED_COMMIT"')
    fast_forward_index = content.index('git merge --ff-only "$EXPECTED_COMMIT"')

    assert status_index < branch_index < sudo_index < fetch_index < fetched_commit_index
    assert fetched_commit_index < fast_forward_check_index < fast_forward_index

    for mutating_command in [
        "backend/.venv/bin/python -m pip install",
        "npm run build",
        "rsync -a --delete",
        "sudo systemctl restart tongshi-backend.service",
    ]:
        assert fast_forward_index < content.index(mutating_command)


def test_redeploy_script_dry_run_displays_preflight_gates_without_contacting_server():
    """DryRun 不要求提交参数，但必须展示真实部署前会执行的所有安全门禁。"""
    powershell = _require_powershell()

    command = [powershell, "-NoProfile"]
    if Path(powershell).name.lower() in {"powershell", "powershell.exe"}:
        command.extend(["-ExecutionPolicy", "Bypass"])
    command.extend(
        [
            "-File",
            str(REPO_ROOT / "deploy" / "redeploy-server.ps1"),
            "-Host",
            "example.invalid",
            "-User",
            "deploy",
            "-DryRun",
        ]
    )

    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)

    assert result.returncode == 0, result.stderr
    assert "[DryRun] ssh" in result.stdout
    assert "ExpectedCommit" in result.stdout
    assert "git status --porcelain=v1 --untracked-files=all" in result.stdout
    assert "git branch --show-current" in result.stdout
    assert "sudo -n true" in result.stdout
    assert "git fetch --no-tags origin refs/heads/main" in result.stdout
    assert 'git merge-base --is-ancestor HEAD "$EXPECTED_COMMIT"' in result.stdout
    assert 'git merge --ff-only "$EXPECTED_COMMIT"' in result.stdout
    assert "git ls-remote origin refs/heads/main" not in result.stdout
    assert "GIT_SSH_COMMAND=" in result.stdout


def test_redeploy_script_normalizes_crlf_before_remote_bash(tmp_path):
    """Windows PowerShell 的尾部 CRLF 必须在远端 Bash 读取前被清除。"""
    powershell = _require_powershell()

    capture_path = tmp_path / "remote-script.sh"
    capture_arguments_path = tmp_path / "ssh-arguments.txt"
    capture_script = tmp_path / "capture-stdin.ps1"
    capture_script.write_text(
        """$destination = [System.IO.File]::Open(
    $env:TONGSHI_DEPLOY_CAPTURE_PATH,
    [System.IO.FileMode]::Create,
    [System.IO.FileAccess]::Write,
    [System.IO.FileShare]::None
)
try {
    [Console]::OpenStandardInput().CopyTo($destination)
}
finally {
    $destination.Dispose()
}
[System.IO.File]::WriteAllText(
    $env:TONGSHI_DEPLOY_CAPTURE_ARGUMENTS_PATH,
    [string]::Join("`n", $args),
    [System.Text.UTF8Encoding]::new($false)
)
""",
        encoding="utf-8",
    )
    fake_ssh = tmp_path / "ssh.cmd"
    fake_ssh.write_text(
        f'@echo off\r\n"{powershell}" -NoProfile -ExecutionPolicy Bypass -File "%~dp0capture-stdin.ps1" %*\r\nexit /b %ERRORLEVEL%\r\n',
        encoding="utf-8",
    )

    command = [powershell, "-NoProfile"]
    if Path(powershell).name.lower() in {"powershell", "powershell.exe"}:
        command.extend(["-ExecutionPolicy", "Bypass"])
    command.extend(
        [
            "-File",
            str(REPO_ROOT / "deploy" / "redeploy-server.ps1"),
            "-Host",
            "example.invalid",
            "-User",
            "deploy",
            "-ExpectedCommit",
            "0123456",
        ]
    )
    environment = os.environ.copy()
    environment["PATH"] = f"{tmp_path}{os.pathsep}{environment['PATH']}"
    environment["TONGSHI_DEPLOY_CAPTURE_PATH"] = str(capture_path)
    environment["TONGSHI_DEPLOY_CAPTURE_ARGUMENTS_PATH"] = str(capture_arguments_path)

    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False, env=environment)

    assert result.returncode == 0, result.stderr
    remote_script = capture_path.read_bytes()
    remote_command = capture_arguments_path.read_text(encoding="utf-8")
    assert b"git status --porcelain=v1 --untracked-files=all" in remote_script
    assert b"\r\n" in remote_script
    assert not remote_script.startswith(b"\xef\xbb\xbf")
    assert "bash -o pipefail -c 'tr -d '\\''\\r'\\'' | bash -se'" in remote_command

    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("本机未安装 Bash，无法执行 CRLF 过滤回归。")
    bash_probe = subprocess.run(
        [bash, "--version"],
        capture_output=True,
        check=False,
    )
    if bash_probe.returncode != 0:
        # Windows 的 WSL 占位 bash.exe 可能存在，但未安装发行版时并不可执行。
        pytest.skip("本机 Bash 不可用，无法执行 CRLF 过滤回归。")
    filtered = subprocess.run(
        [bash, "-o", "pipefail", "-c", "tr -d '\\r' | bash -se"],
        input=b"printf 'crlf-filter-ok\\n'\r\n",
        capture_output=True,
        check=False,
    )
    assert filtered.returncode == 0, filtered.stderr.decode("utf-8", errors="replace")
    assert filtered.stdout == b"crlf-filter-ok\n"


@pytest.mark.parametrize("expected_commit", [None, "not-a-sha"])
def test_redeploy_script_rejects_missing_or_invalid_commit_before_ssh(tmp_path, expected_commit):
    """真实部署的缺失或非法 SHA 必须在调用 SSH 前失败。"""
    powershell = _require_powershell()
    marker = tmp_path / "ssh-was-called.txt"
    fake_ssh = tmp_path / "ssh.cmd"
    fake_ssh.write_text(
        '@echo off\r\necho invoked>"%TONGSHI_DEPLOY_SSH_MARKER%"\r\nexit /b 0\r\n',
        encoding="utf-8",
    )
    command = [
        powershell,
        "-NoProfile",
    ]
    if Path(powershell).name.lower() in {"powershell", "powershell.exe"}:
        command.extend(["-ExecutionPolicy", "Bypass"])
    command.extend(
        [
            "-File",
            str(REPO_ROOT / "deploy" / "redeploy-server.ps1"),
            "-Host",
            "example.invalid",
            "-User",
            "deploy",
        ]
    )
    if expected_commit is not None:
        command.extend(["-ExpectedCommit", expected_commit])

    environment = os.environ.copy()
    environment["PATH"] = f"{tmp_path}{os.pathsep}{environment['PATH']}"
    environment["TONGSHI_DEPLOY_SSH_MARKER"] = str(marker)
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False, env=environment)

    assert result.returncode != 0
    assert not marker.exists()


def test_deploy_readme_documents_safe_commit_and_nginx_release_sequence():
    """部署说明必须覆盖提交锁定、脏工作区止损和可回退的 Nginx 生效步骤。"""
    content = (REPO_ROOT / "deploy" / "README.md").read_text(encoding="utf-8")

    for expected_text in [
        "git rev-parse HEAD",
        "-ExpectedCommit",
        "-DryRun",
        "git status --porcelain=v1 --untracked-files=all",
        "脏工作区",
        "StaticRoot",
        "Nginx root",
        "nginx -t",
        "systemctl reload nginx",
        "回退",
    ]:
        assert expected_text in content


def test_upload_script_only_stages_nginx_candidate_outside_git_worktree():
    """上传脚本只能写入非 Git 工作区的 Nginx 候选目录。"""
    content = (REPO_ROOT / "deploy" / "upload-local-storage-deploy.ps1").read_text(encoding="utf-8")

    assert '[Alias("Host")]' in content
    assert "$ServerHost" in content
    assert "-DryRun" in content or "DryRun" in content
    assert "ssh" in content
    assert "scp" in content
    assert "deploy/nginx.conf" in content
    assert "tongshi.nginx.conf.candidate" in content
    assert 'git -C "$GitProbe" rev-parse --is-inside-work-tree' in content
    assert "候选目录位于 Git 工作区中" in content
    assert '$destination = "${RemoteUserHost}:$remoteTarget"' in content
    assert '$(Protect-RemoteShellArg -Value $remoteTarget)' not in content
    assert "backend/scripts/check_deploy_env.py" not in content
    assert "backend/.env.example" not in content
    assert "frontend/.env.production.example" not in content

    git_worktree_check_index = content.index('git -C "$GitProbe" rev-parse --is-inside-work-tree')
    mkdir_index = content.index('mkdir -p -- "$CandidateDirectory"')
    scp_index = content.index('Invoke-ExternalCommand -FilePath "scp"')
    assert git_worktree_check_index < mkdir_index < scp_index


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


def test_upload_script_passes_unquoted_candidate_path_to_scp(tmp_path):
    """默认 SFTP 模式下传给 scp 的远端路径不能带 shell 单引号。"""
    powershell = _require_powershell()
    capture_path = tmp_path / "scp-arguments.txt"
    capture_script = tmp_path / "capture-scp.ps1"
    capture_script.write_text(
        """[System.IO.File]::WriteAllText(
    $env:TONGSHI_UPLOAD_SCP_CAPTURE_PATH,
    [string]::Join("`n", $args),
    [System.Text.UTF8Encoding]::new($false)
)
""",
        encoding="utf-8",
    )
    fake_ssh = tmp_path / "ssh.cmd"
    fake_ssh.write_text("@echo off\r\nexit /b 0\r\n", encoding="utf-8")
    fake_scp = tmp_path / "scp.cmd"
    fake_scp.write_text(
        f'@echo off\r\n"{powershell}" -NoProfile -ExecutionPolicy Bypass -File "%~dp0capture-scp.ps1" %*\r\nexit /b %ERRORLEVEL%\r\n',
        encoding="utf-8",
    )

    command = [powershell, "-NoProfile"]
    if Path(powershell).name.lower() in {"powershell", "powershell.exe"}:
        command.extend(["-ExecutionPolicy", "Bypass"])
    command.extend(
        [
            "-File",
            str(REPO_ROOT / "deploy" / "upload-local-storage-deploy.ps1"),
            "-Host",
            "example.invalid",
            "-User",
            "deploy",
            "-RemoteRoot",
            "/var/tmp/tongshi-candidates",
        ]
    )
    environment = os.environ.copy()
    environment["PATH"] = f"{tmp_path}{os.pathsep}{environment['PATH']}"
    environment["TONGSHI_UPLOAD_SCP_CAPTURE_PATH"] = str(capture_path)

    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False, env=environment)

    assert result.returncode == 0, result.stderr
    arguments = capture_path.read_text(encoding="utf-8").splitlines()
    assert arguments[-1] == "deploy@example.invalid:/var/tmp/tongshi-candidates/tongshi.nginx.conf.candidate"
    assert "'" not in arguments[-1]


def test_deploy_readme_does_not_recommend_remote_git_pull_or_interpolate_remote_path():
    """部署文档不能引导绕过提交锁定，也不能拼接远端 shell 路径。"""
    content = (REPO_ROOT / "deploy" / "README.md").read_text(encoding="utf-8")

    assert "更稳妥的做法还是合回 `main` 后在服务器执行 `git pull`" not in content
    assert "cd '$remoteRoot'" not in content
    assert "Nginx 候选文件" in content
