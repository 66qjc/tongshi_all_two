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
    @{ Source = "deploy/nginx.conf"; Target = "deploy/nginx.conf" },
    @{ Source = "deploy/README.md"; Target = "deploy/README.md" },
    @{ Source = "backend/scripts/check_deploy_env.py"; Target = "backend/scripts/check_deploy_env.py" },
    @{ Source = "backend/.env.example"; Target = "backend/.env.example" },
    @{ Source = "backend/README.md"; Target = "backend/README.md" },
    @{ Source = "frontend/.env.production.example"; Target = "frontend/.env.production.example" },
    @{ Source = "frontend/README.md"; Target = "frontend/README.md" },
    @{ Source = "docs/superpowers/project-map.md"; Target = "docs/superpowers/project-map.md" }
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

if ([string]::IsNullOrWhiteSpace($RemoteRoot)) {
    throw "Remote root cannot be empty."
}

if ($RemoteRoot.Contains('\')) {
    throw "Remote root must use a Linux path, for example /opt/tongshi."
}

$RemoteRoot = $RemoteRoot.TrimEnd("/")
if ([string]::IsNullOrWhiteSpace($RemoteRoot)) {
    throw "Remote root cannot be empty."
}

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
$RemoteDirs = $ResolvedItems |
    ForEach-Object { Split-Path -Path $_.Target -Parent } |
    Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
    Sort-Object -Unique

$MkdirPaths = @($RemoteRoot) + ($RemoteDirs | ForEach-Object { Join-RemotePath -Root $RemoteRoot -RelativePath $_ })
$MkdirCommand = "mkdir -p " + (($MkdirPaths | ForEach-Object { Protect-RemoteShellArg -Value $_ }) -join " ")
$RemoteUserHost = "${User}@${ServerHost}"

Write-Host "Prepare remote directories: $RemoteRoot"
Invoke-ExternalCommand -FilePath "ssh" -ArgumentList ($SshBaseArgs + @($RemoteUserHost, $MkdirCommand))

foreach ($item in $ResolvedItems) {
    $remoteTarget = Join-RemotePath -Root $RemoteRoot -RelativePath $item.Target
    $destination = "${RemoteUserHost}:$(Protect-RemoteShellArg -Value $remoteTarget)"
    Write-Host "Upload: $($item.Target)"
    Invoke-ExternalCommand -FilePath "scp" -ArgumentList ($ScpBaseArgs + @($item.Source, $destination))
}

Write-Host "Upload completed."
