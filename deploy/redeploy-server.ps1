[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [Alias("Host")]
    [ValidateNotNullOrEmpty()]
    [string]$ServerHost,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$User,

    [ValidateNotNullOrEmpty()]
    [string]$RemoteRoot = "/home/ubuntu/tongshi_all_two",

    [ValidateNotNullOrEmpty()]
    [string]$StaticRoot = "/var/www/tongshi",

    [ValidateRange(1, 65535)]
    [int]$Port = 22,

    [ValidateNotNullOrEmpty()]
    [string]$IdentityFile,

    [string]$ExpectedCommit,

    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Protect-RemotePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        throw "远端路径不能为空。"
    }

    if (-not $Value.StartsWith("/")) {
        throw "远端路径必须是绝对路径：$Value"
    }

    if ($Value.Contains("`n") -or $Value.Contains("`r")) {
        throw "远端路径不能包含换行符。"
    }

    if ($Value.Contains("'")) {
        throw "远端路径不能包含单引号。"
    }

    return "'" + $Value + "'"
}

function Get-NormalizedRemotePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    $normalized = $Value.TrimEnd("/")
    if ([string]::IsNullOrWhiteSpace($normalized)) {
        throw "远端路径不能是根目录：$Value"
    }

    if ($normalized -notmatch "^/[A-Za-z0-9._/-]+$") {
        throw "远端路径包含不支持的字符：$Value"
    }

    $segments = $normalized.Substring(1).Split("/")
    if ($segments | Where-Object { [string]::IsNullOrWhiteSpace($_) -or $_ -eq "." -or $_ -eq ".." }) {
        throw "远端路径不能包含空路径段、`.` 或 `..`：$Value"
    }

    return $normalized
}

function Get-SshArguments {
    param(
        [switch]$ValidateIdentityFile
    )

    $arguments = @(
        "-o", "BatchMode=yes",
        "-p", [string]$Port
    )

    if (-not [string]::IsNullOrWhiteSpace($IdentityFile)) {
        if ($ValidateIdentityFile -and -not (Test-Path -LiteralPath $IdentityFile -PathType Leaf)) {
            throw "SSH identity file does not exist: $IdentityFile"
        }

        $arguments += @("-i", $IdentityFile)
    }

    return $arguments
}

if ($User -notmatch "^[A-Za-z0-9._-]+$") {
    throw "SSH 用户名包含不支持的字符：$User"
}

if ($ServerHost.Contains("`n") -or $ServerHost.Contains("`r") -or $ServerHost.Contains(" ")) {
    throw "服务器地址不能包含空格或换行符：$ServerHost"
}

$normalizedExpectedCommit = ""
if (-not [string]::IsNullOrWhiteSpace($ExpectedCommit)) {
    if ($ExpectedCommit -notmatch "^[0-9a-fA-F]{7,64}$") {
        throw "ExpectedCommit 必须是 7-64 位十六进制提交 SHA：$ExpectedCommit"
    }

    $normalizedExpectedCommit = $ExpectedCommit.ToLowerInvariant()
}

if (-not $DryRun -and [string]::IsNullOrWhiteSpace($normalizedExpectedCommit)) {
    throw "真实部署必须提供 -ExpectedCommit（7-64 位十六进制提交 SHA）。"
}

$normalizedRemoteRoot = Get-NormalizedRemotePath -Value $RemoteRoot
$normalizedStaticRoot = Get-NormalizedRemotePath -Value $StaticRoot
if ($normalizedStaticRoot -eq "/") {
    throw "静态发布目录不能是根目录。"
}
if (
    $normalizedStaticRoot -eq $normalizedRemoteRoot -or
    $normalizedStaticRoot.StartsWith("$normalizedRemoteRoot/") -or
    $normalizedRemoteRoot.StartsWith("$normalizedStaticRoot/")
) {
    throw "静态发布目录不能与项目根目录重叠：$StaticRoot / $RemoteRoot"
}

$quotedRemoteRoot = Protect-RemotePath -Value $normalizedRemoteRoot
$quotedStaticRoot = Protect-RemotePath -Value $normalizedStaticRoot

$remoteScriptBody = @'

test -d "$PROJECT_ROOT/.git"
test -x "$PROJECT_ROOT/backend/.venv/bin/python"
test -f "$PROJECT_ROOT/backend/.env"
test -f "$PROJECT_ROOT/frontend/.env.production"
test -d "$STATIC_ROOT"

PROJECT_ROOT_REAL="$(readlink -f "$PROJECT_ROOT")"
STATIC_ROOT_REAL="$(readlink -f "$STATIC_ROOT")"
if [ -z "$PROJECT_ROOT_REAL" ] || [ -z "$STATIC_ROOT_REAL" ] || [ "$PROJECT_ROOT_REAL" = "/" ] || [ "$STATIC_ROOT_REAL" = "/" ]; then
  printf '%s\n' "项目目录或静态目录解析到了不安全路径。" >&2
  exit 1
fi
case "$PROJECT_ROOT_REAL/" in
  "$STATIC_ROOT_REAL/"*)
    printf '%s\n' "项目目录与静态目录存在重叠。" >&2
    exit 1
    ;;
esac
case "$STATIC_ROOT_REAL/" in
  "$PROJECT_ROOT_REAL/"*)
    printf '%s\n' "静态目录与项目目录存在重叠。" >&2
    exit 1
    ;;
esac

free_kb="$(df -Pk / | awk 'NR == 2 { print $4 }')"
if ! printf '%s\n' "$free_kb" | grep -Eq '^[0-9]+$'; then
  printf '%s\n' "无法读取根分区剩余空间。" >&2
  exit 1
fi
if [ "$free_kb" -lt 2097152 ]; then
  printf '根分区剩余空间不足 2GB：%sKB\n' "$free_kb" >&2
  exit 1
fi

cd "$PROJECT_ROOT"
if ! printf '%s\n' "$REQUESTED_COMMIT" | grep -Eq '^[0-9a-f]{7,64}$'; then
  printf '%s\n' "ExpectedCommit 格式无效，已停止部署。" >&2
  exit 1
fi

if ! WORKTREE_STATUS="$(git status --porcelain=v1 --untracked-files=all)"; then
  printf '%s\n' "无法检查服务器工作区状态，已停止部署。" >&2
  exit 1
fi
if [ -n "$WORKTREE_STATUS" ]; then
  printf '%s\n' "服务器工作区存在未提交内容，已停止部署且不会覆盖文件：" >&2
  printf '%s\n' "$WORKTREE_STATUS" >&2
  exit 1
fi

if ! CURRENT_BRANCH="$(git branch --show-current)"; then
  printf '%s\n' "无法读取服务器当前分支，已停止部署。" >&2
  exit 1
fi
if [ "$CURRENT_BRANCH" != "main" ]; then
  printf '服务器当前分支不是 main（实际：%s），已停止部署。\n' "$CURRENT_BRANCH" >&2
  exit 1
fi

if ! sudo -n true; then
  printf '%s\n' "当前服务器用户无法无交互执行 sudo，已停止部署。" >&2
  exit 1
fi

if ! env GIT_TERMINAL_PROMPT=0 GIT_SSH_COMMAND='ssh -o BatchMode=yes' git fetch --no-tags origin refs/heads/main; then
  printf '%s\n' "无法无交互拉取 origin/main 提交，已停止部署。" >&2
  exit 1
fi
if ! FETCHED_COMMIT="$(git rev-parse FETCH_HEAD)"; then
  printf '%s\n' "无法读取已拉取的 origin/main 提交，已停止部署。" >&2
  exit 1
fi
if ! printf '%s\n' "$FETCHED_COMMIT" | grep -Eq '^[0-9a-f]{40,64}$'; then
  printf '%s\n' "已拉取的 origin/main 没有返回有效提交 SHA，已停止部署。" >&2
  exit 1
fi
case "$FETCHED_COMMIT" in
  "$REQUESTED_COMMIT"*)
    EXPECTED_COMMIT="$FETCHED_COMMIT"
    ;;
  *)
    printf '已拉取的 main 提交与 ExpectedCommit 不一致（预期：%s，实际：%s），已停止部署。\n' "$REQUESTED_COMMIT" "$FETCHED_COMMIT" >&2
    exit 1
    ;;
esac

if ! git merge-base --is-ancestor HEAD "$EXPECTED_COMMIT"; then
  printf '当前 HEAD 不是 ExpectedCommit 的祖先，拒绝非快进部署（当前：%s，目标：%s）。\n' "$(git rev-parse HEAD)" "$EXPECTED_COMMIT" >&2
  exit 1
fi

if ! git merge --ff-only "$EXPECTED_COMMIT"; then
  printf '%s\n' "从已验证提交执行本地快进失败，已停止部署。" >&2
  exit 1
fi
if ! HEAD_COMMIT="$(git rev-parse HEAD)"; then
  printf '%s\n' "无法读取拉取后的 HEAD 提交，已停止部署。" >&2
  exit 1
fi
if [ "$HEAD_COMMIT" != "$EXPECTED_COMMIT" ]; then
  printf '拉取后 HEAD 与 ExpectedCommit 不一致（预期：%s，实际：%s），已停止部署。\n' "$EXPECTED_COMMIT" "$HEAD_COMMIT" >&2
  exit 1
fi

backend/.venv/bin/python -m pip install -r backend/requirements.txt

BUILD_INDEX="$PROJECT_ROOT/frontend/dist/index.html"
if [ -f "$BUILD_INDEX" ]; then
  BEFORE_INDEX_MTIME="$(stat -c '%y' "$BUILD_INDEX")"
else
  BEFORE_INDEX_MTIME="missing"
fi

cd "$PROJECT_ROOT/frontend"
npm run build </dev/null
test -f "$BUILD_INDEX"
AFTER_INDEX_MTIME="$(stat -c '%y' "$BUILD_INDEX")"
printf 'frontend dist/index.html 构建前时间：%s\n' "$BEFORE_INDEX_MTIME"
printf 'frontend dist/index.html 构建后时间：%s\n' "$AFTER_INDEX_MTIME"

rsync -a --delete "$PROJECT_ROOT/frontend/dist/" "$STATIC_ROOT/"

if ! sudo systemctl restart tongshi-backend.service; then
  if ! sudo journalctl -u tongshi-backend.service -n 80 --no-pager; then
    printf '%s\n' "无法读取 Tongshi 后端 journal。" >&2
  fi
  printf '%s\n' "Tongshi 后端重启失败。" >&2
  exit 1
fi

for attempt in $(seq 1 12); do
  if sudo systemctl is-active --quiet tongshi-backend.service && curl -fsS --max-time 5 http://127.0.0.1:8050/health >/dev/null; then
    printf 'Tongshi 后端健康检查通过。\n'
    exit 0
  fi
  sleep 2
done

if ! sudo journalctl -u tongshi-backend.service -n 80 --no-pager; then
  printf '%s\n' "无法读取 Tongshi 后端 journal。" >&2
fi
printf '%s\n' "Tongshi 后端健康检查失败。" >&2
exit 1
'@

$remoteScript = @"
set -Eeuo pipefail

PROJECT_ROOT=$quotedRemoteRoot
STATIC_ROOT=$quotedStaticRoot
REQUESTED_COMMIT='$normalizedExpectedCommit'
$remoteScriptBody
"@
$remoteShellCommand = "bash -o pipefail -c 'tr -d '\''\r'\'' | bash -se'"
$remoteUserHost = "${User}@${ServerHost}"
$sshArguments = Get-SshArguments -ValidateIdentityFile:(-not $DryRun)

if ($DryRun) {
    $displayArguments = ($sshArguments | ForEach-Object {
        if ($_ -match "\s") { '"' + $_ + '"' } else { $_ }
    }) -join " "

    Write-Host "[DryRun] ssh $displayArguments $remoteUserHost $remoteShellCommand"
    Write-Host $remoteScript
    exit 0
}

if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
    throw "找不到 ssh 命令。"
}

Write-Host "开始部署到 $remoteUserHost。"
$previousOutputEncoding = $OutputEncoding
try {
    $OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $remoteScript | & ssh @sshArguments $remoteUserHost $remoteShellCommand
}
finally {
    $OutputEncoding = $previousOutputEncoding
}
if ($LASTEXITCODE -ne 0) {
    throw "远端部署失败，退出码：$LASTEXITCODE"
}

Write-Host "部署完成，后端健康检查已通过。"
