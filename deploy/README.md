# 部署上传脚本

这个目录放的是上线辅助文件，不是完整发布系统。

## 单机完整部署（提交锁定）

`redeploy-server.ps1` 用于服务器已有工作区的可重复部署。真实部署必须显式传入 `-ExpectedCommit`，脚本会先确认服务器工作区没有未提交或未跟踪文件、当前分支为 `main`、`sudo -n true` 可用，再通过一次无交互 `git fetch` 获取确定提交并验证本地可快进；任一检查失败都会以非零状态停止，且不会执行依赖安装、前端构建、静态文件同步或服务重启。

脚本保留现有 `RemoteRoot` 与 `StaticRoot` 默认值以兼容既有调用，但正式发布不得盲用 `StaticRoot` 默认值：它必须显式等于当前生效 Nginx server 块中的 `root` 目录。脚本会将 `frontend/dist/` 的内容同步到 `StaticRoot`，若两者不一致，浏览器仍会读取旧静态资源。

### 1. 本地确认待发布提交

在已切换到待发布分支且本地工作区干净时执行。先记录完整 SHA，再将该提交推送到 `origin/main`；不要用未推送的本地 SHA 部署。

```powershell
git branch --show-current
git status --short
$expectedCommit = (git rev-parse HEAD).Trim()
$expectedCommit
git push origin main
git ls-remote origin refs/heads/main
```

上述最后一条命令返回的 SHA 必须与 `$expectedCommit` 一致；分支不是 `main`、工作区有输出或 SHA 不一致时先停止处理，不要继续部署。

### 2. 先核对活动 Nginx root，再执行 DryRun

先登录服务器并执行 `sudo nginx -T`，在输出中找到**当前生效**站点的 server 块及其 `root`。不要根据发行版惯例猜测 Nginx 配置文件路径，也不要把 `deploy/nginx.conf` 当作已生效配置。将该 `root` 的绝对路径填入 `$staticRoot`，它就是传给 `-StaticRoot` 的值。

```powershell
$serverHost = Read-Host '服务器地址'
$serverUser = Read-Host '服务器用户'
$remoteRoot = Read-Host '服务器项目工作区绝对路径'
$staticRoot = Read-Host '当前生效 Nginx root 的绝对路径'
$identityFile = Read-Host 'SSH 私钥文件路径'

powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy\redeploy-server.ps1 `
  -Host $serverHost `
  -User $serverUser `
  -RemoteRoot $remoteRoot `
  -StaticRoot $staticRoot `
  -IdentityFile $identityFile `
  -ExpectedCommit $expectedCommit `
  -DryRun
```

DryRun 只打印将发送给服务器的脚本，不会建立 SSH 连接；它可以省略 `-ExpectedCommit` 以查看门禁逻辑，但真实部署绝不能省略。

### 3. 远端预检由部署脚本执行

不要手工把 `$remoteRoot` 拼接到远端 shell 命令中。真实部署会在任何工作区变更前使用与发布相同的 SSH 用户执行 `git status --porcelain=v1 --untracked-files=all`、分支、无交互 `sudo`、目标提交和快进关系检查；DryRun 会打印该预检脚本，便于先核对参数和流程。

服务器出现脏工作区时必须停止：不要执行 `git clean`、`git reset`、强制覆盖或真实部署。先由服务器维护者确认未提交文件的来源，并通过提交、备份或人工合并妥善处理后重新预检。

### 4. 真实部署

仅在本地 SHA、DryRun 和远端预检全部符合预期后，去掉 `-DryRun`：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy\redeploy-server.ps1 `
  -Host $serverHost `
  -User $serverUser `
  -RemoteRoot $remoteRoot `
  -StaticRoot $staticRoot `
  -IdentityFile $identityFile `
  -ExpectedCommit $expectedCommit
```

脚本不会执行 `git clean -fd`，不会覆盖服务器 `.env`。后端健康检查失败时会输出最近 80 行日志并以非零状态退出。真实部署要求远端用户具备无交互执行 `sudo` 的权限。

该脚本只负责代码发布，不负责服务器 journal、Swap、Docker、备份和磁盘清理；这些运维动作仍按 `docs/superpowers/plans/2026-07-14-single-server-ops-hardening.md` 逐项执行并单独验收。

## 本地文件预览与 Nginx 安全发布

生产环境的 `LOCAL_UPLOAD_DIR` 应为 `/data/tongshi/uploads`。Nginx 必须保留 `/_protected_uploads/` 的 `internal` 映射，并使用同一目录作为 `alias`；该路径不能配置为普通公网静态目录。Vite 生成的 `pdf.worker.min-*.mjs` 需要在 `/assets/` 专用 location 内以 `application/javascript` MIME 返回。

`redeploy-server.ps1` 不会安装 Nginx 配置，因为只有服务器上的 `nginx -T` 能确认实际生效的配置文件。需要更新 Nginx 时，先把 `deploy/nginx.conf` 上传到仓库外的候选目录，然后在服务器 shell 中将下列两个变量替换为实际路径；不要猜测站点文件位置：

```bash
NGINX_SITE_FILE='/从 nginx -T 确认的当前生效站点配置绝对路径'
NEW_NGINX_CONF='/已上传的 tongshi.nginx.conf.candidate 绝对路径'
BACKUP_FILE="${NGINX_SITE_FILE}.bak.$(date +%Y%m%d%H%M%S)"

sudo cp -- "$NGINX_SITE_FILE" "$BACKUP_FILE"
if ! sudo install -m 0644 -- "$NEW_NGINX_CONF" "$NGINX_SITE_FILE"; then
  printf '%s\n' '安装 Nginx 配置失败，原配置未替换。' >&2
  exit 1
fi
if ! sudo nginx -t; then
  sudo cp -- "$BACKUP_FILE" "$NGINX_SITE_FILE"
  sudo nginx -t
  printf '%s\n' 'Nginx 配置校验失败，已回退备份；请不要 reload。' >&2
  exit 1
fi
if ! sudo systemctl reload nginx; then
  sudo cp -- "$BACKUP_FILE" "$NGINX_SITE_FILE"
  sudo nginx -t
  sudo systemctl reload nginx
  printf '%s\n' 'Nginx reload 失败，已回退备份并尝试恢复。' >&2
  exit 1
fi
```

保留 `$BACKUP_FILE` 直到页面和 PDF 预览验证完成；若发现异常，使用该备份执行回退、`nginx -t`，再 `systemctl reload nginx`。Nginx 配置变更不替代后端发布；若后端的 X-Accel 逻辑有改动，仍需通过上述提交锁定流程重启 `tongshi-backend.service`。

## 上传 Nginx 候选文件到服务器

`upload-local-storage-deploy.ps1` 只上传 `deploy/nginx.conf`，并在候选目录中命名为 `tongshi.nginx.conf.candidate`。`-RemoteRoot` 必须是仓库外的候选目录，例如 `/var/tmp/tongshi-nginx-candidates`；脚本会先检查该目录最近的已存在祖先，发现它位于 Git 工作区时立即停止，随后才会创建目录或上传文件。

该脚本不能更新服务器代码、仓库内配置、说明文件或 `.env`。完整代码发布只能使用上文的 `redeploy-server.ps1` 提交锁定流程。

PowerShell 7：

```powershell
pwsh -File .\deploy\upload-local-storage-deploy.ps1 `
  -Host 1.2.3.4 `
  -User deploy `
  -RemoteRoot /var/tmp/tongshi-nginx-candidates `
  -IdentityFile C:\Users\ASUS\.ssh\id_rsa `
  -DryRun
```

Windows PowerShell：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy\upload-local-storage-deploy.ps1 `
  -Host 1.2.3.4 `
  -User deploy `
  -RemoteRoot /var/tmp/tongshi-nginx-candidates `
  -IdentityFile C:\Users\ASUS\.ssh\id_rsa `
  -DryRun
```

去掉 `-DryRun` 后执行真实上传。

## 会上传哪个文件

- `deploy/nginx.conf` -> `$RemoteRoot/tongshi.nginx.conf.candidate`

## 说明

- 候选文件上传成功后，仍须按上文执行备份、`nginx -t`、安装和 reload；上传本身不会使配置生效。
- 如果要更新完整代码，先将目标提交推送到 `origin/main`，再使用 `redeploy-server.ps1`。
