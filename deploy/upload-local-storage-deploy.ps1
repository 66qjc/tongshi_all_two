[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [Alias("Host")]
    [ValidateNotNullOrEmpty()]
    [string]$ServerHost,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$User,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$RemoteRoot,

    [ValidateRange(1, 65535)]
    [int]$Port = 22,

    [ValidateNotNullOrEmpty()]
    [string]$IdentityFile,

    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$UploadItems = @(
    @{ Source = "deploy/nginx.conf"; Target = "tongshi.nginx.conf.candidate" }
)

function Get-RepoRoot {
    $scriptDir = Split-Path -Parent $PSCommandPath
    return (Resolve-Path -LiteralPath (Join-Path $scriptDir "..")).Path
}

function Join-RemotePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root,

        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $cleanRoot = $Root.TrimEnd("/")
    $cleanRelative = ($RelativePath -replace "\\", "/").TrimStart("/")

    if ([string]::IsNullOrWhiteSpace($cleanRelative)) {
        return $cleanRoot
    }

    return "$cleanRoot/$cleanRelative"
}

function Protect-RemoteShellArg {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    if ($Value.Contains("'") -or $Value.Contains("`n") -or $Value.Contains("`r")) {
        throw "Remote path cannot contain single quotes or newlines: $Value"
    }

    return "'$Value'"
}

function Get-NormalizedRemotePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    if (-not $Value.StartsWith("/")) {
        throw "候选目录必须是绝对 Linux 路径：$Value"
    }

    if ($Value.Contains("'") -or $Value.Contains("`n") -or $Value.Contains("`r") -or $Value.Contains("\")) {
        throw "候选目录包含不支持的字符：$Value"
    }

    $normalized = $Value.TrimEnd("/")
    if ([string]::IsNullOrWhiteSpace($normalized) -or $normalized -eq "/") {
        throw "候选目录不能是根目录：$Value"
    }

    if ($normalized -notmatch "^/[A-Za-z0-9._/-]+$") {
        throw "候选目录包含不支持的字符：$Value"
    }

    $segments = $normalized.Substring(1).Split("/")
    if ($segments | Where-Object { [string]::IsNullOrWhiteSpace($_) -or $_ -eq "." -or $_ -eq ".." }) {
        throw "候选目录不能包含空路径段、`.` 或 `..`：$Value"
    }

    return $normalized
}

function Invoke-ExternalCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [Parameter(Mandatory = $true)]
        [string[]]$ArgumentList
    )

    $displayArgs = ($ArgumentList | ForEach-Object {
        if ($_ -match "\s") {
            '"' + $_ + '"'
        } else {
            $_
        }
    }) -join " "

    if ($DryRun) {
        Write-Host "[DryRun] $FilePath $displayArgs"
        return
    }

    & $FilePath @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw "命令执行失败：$FilePath $displayArgs"
    }
}

function Get-SshBaseArgs {
    $baseArgs = @()

    if (-not [string]::IsNullOrWhiteSpace($IdentityFile)) {
        if (-not (Test-Path -LiteralPath $IdentityFile -PathType Leaf)) {
            throw "SSH identity file does not exist: $IdentityFile"
        }

        $baseArgs += @("-i", $IdentityFile)
    }

    $baseArgs += @("-p", [string]$Port)
    return $baseArgs
}

function Get-ScpBaseArgs {
    $baseArgs = @()

    if (-not [string]::IsNullOrWhiteSpace($IdentityFile)) {
        if (-not (Test-Path -LiteralPath $IdentityFile -PathType Leaf)) {
            throw "SSH identity file does not exist: $IdentityFile"
        }

        $baseArgs += @("-i", $IdentityFile)
    }

    $baseArgs += @("-P", [string]$Port)
    return $baseArgs
}

if ([string]::IsNullOrWhiteSpace($ServerHost)) {
    throw "Server host cannot be empty."
}

if ([string]::IsNullOrWhiteSpace($User)) {
    throw "User cannot be empty."
}

$RemoteRoot = Get-NormalizedRemotePath -Value $RemoteRoot

$RepoRoot = Get-RepoRoot
$ResolvedItems = foreach ($item in $UploadItems) {
    $sourceRelative = [string]$item["Source"]
    $targetRelative = [string]$item["Target"]
    $sourcePath = Join-Path $RepoRoot $sourceRelative

    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        throw "Local file does not exist: $sourceRelative"
    }

    [pscustomobject]@{
        Source = (Resolve-Path -LiteralPath $sourcePath).Path
        Target = $targetRelative
    }
}

if (-not $DryRun) {
    foreach ($commandName in @("ssh", "scp")) {
        if (-not (Get-Command $commandName -ErrorAction SilentlyContinue)) {
            throw "Command not found: $commandName"
        }
    }
}

$SshBaseArgs = Get-SshBaseArgs
$ScpBaseArgs = Get-ScpBaseArgs
$RemoteUserHost = "${User}@${ServerHost}"
$QuotedRemoteRoot = Protect-RemoteShellArg -Value $RemoteRoot
$RemotePreflightCommand = @'
set -eu
CandidateDirectory=__CANDIDATE_DIRECTORY__
GitProbe="$CandidateDirectory"
while [ ! -e "$GitProbe" ]; do
    ParentDirectory="$(dirname -- "$GitProbe")"
    if [ "$ParentDirectory" = "$GitProbe" ]; then
        printf '%s\n' '无法找到候选目录的已存在祖先，已停止上传。' >&2
        exit 1
    fi
    GitProbe="$ParentDirectory"
done
if ! command -v git >/dev/null 2>&1; then
    printf '%s\n' '服务器缺少 git，无法验证候选目录是否安全。' >&2
    exit 1
fi
if git -C "$GitProbe" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    printf '%s\n' '候选目录位于 Git 工作区中，已停止上传。' >&2
    exit 1
fi
mkdir -p -- "$CandidateDirectory"
'@.Replace("__CANDIDATE_DIRECTORY__", $QuotedRemoteRoot)

Write-Host "检查 Nginx 候选目录：$RemoteRoot"
Invoke-ExternalCommand -FilePath "ssh" -ArgumentList ($SshBaseArgs + @($RemoteUserHost, $RemotePreflightCommand))

foreach ($item in $ResolvedItems) {
    $remoteTarget = Join-RemotePath -Root $RemoteRoot -RelativePath $item.Target
    $destination = "${RemoteUserHost}:$remoteTarget"
    Write-Host "Upload: $($item.Target)"
    Invoke-ExternalCommand -FilePath "scp" -ArgumentList ($ScpBaseArgs + @($item.Source, $destination))
}

Write-Host "Upload completed."
