# 单机服务器资源与部署稳定性改进实施计划

> **给执行代理：** 必须使用 `subagent-driven-development` 或 `executing-plans` 按任务逐项执行。步骤使用复选框跟踪。

**目标：** 在只有一台 2 核、3.4GB 内存、40GB 系统盘的服务器条件下，降低磁盘和内存压力，固化 Tongshi 的单机部署流程，并补齐本机备份与运维检查能力。

**架构：** 保持现有单机架构：Nginx 提供前端静态文件并代理 API，FastAPI 由 systemd 管理，MySQL 和 Redis 仅监听本机，上传文件保存在 `/data/tongshi/uploads`。本阶段不引入第二台服务器、不改数据库业务结构、不直接启用多 worker；先让单 worker、单机部署可重复、可验证、可回退。

**技术栈：** Ubuntu、systemd、Nginx、FastAPI、Uvicorn、SQLAlchemy、MySQL、Redis、Vue 3、Vite、PowerShell、rsync。

---

## 一、现状与范围

### 1. 已核实的服务器事实

- 服务器地址：`8.136.35.215`，登录用户：`ubuntu`。
- CPU：2 核；内存：3.4GB；Swap：现有 `/swapfile` 4GB，已启用并写入 `/etc/fstab`。
- 根分区：40GB，已用约 33GB，剩余约 4.5GB，使用率约 89%。
- 主要占用：`/var/log/journal` 约 4GB，`/var/lib/docker` 约 3.5GB，`/root/.trae-cn-server` 约 2.7GB，`/root/.vscode-server` 约 2.2GB，`/home/ubuntu/.vscode-server` 约 2.9GB。
- Tongshi 后端目录：`/home/ubuntu/tongshi_all_two/backend`。
- 前端发布目录：`/var/www/tongshi`。
- 上传目录：`/data/tongshi/uploads`。
- 后端服务：`tongshi-backend.service`，当前是单个 Uvicorn 进程，命令没有 `--reload`、没有 `--workers`，配置了 `Restart=always` 和 `RestartSec=5`。
- 当前后端服务命令监听 `0.0.0.0:8050`，Nginx 代理目标为 `127.0.0.1:8050`。
- 服务器 `.env` 未显式配置 `REDIS_*` 和数据库连接池字段，代码默认使用本机 Redis 和 SQLAlchemy 默认配置值。
- `backend/requirements.txt` 已声明 `redis>=5.0.0`；此前服务器虚拟环境缺少该包，已补装并恢复服务。
- 当前没有 Tongshi 专用备份定时任务；`/var/backups` 主要是系统包管理备份，现有数据库压缩备份时间较早。

### 2. 本阶段范围

- 资源控制：journal 日志限额、Swap 使用策略、磁盘阈值检查、Docker 可回收空间分析。
- 部署稳定性：显式配置 Redis 和数据库连接池、补齐依赖检查、固化拉取、构建、同步、重启、健康检查流程。
- 运维保障：MySQL 和上传文件的本机备份、保留策略、备份结果检查、磁盘空间保护。

### 3. 本阶段明确不做

- 不修改防火墙、HTTPS、域名和公网端口策略；这些属于后续安全专项。
- 不删除 Docker 数据卷、运行中容器、数据库文件或上传文件。
- 不删除 `.vscode-server`、`.trae-cn-server` 和旧项目目录，除非逐项确认不再使用。
- 不开启多 worker。当前 `backend/main.py` 启动时会执行建表和 schema 兼容逻辑，需先完成启动锁设计后再评估多 worker。
- 不修改业务接口、数据库表结构和前端业务代码。
- 不把备份上传到外部存储；本阶段只做单机本地备份，并明确其不能抵御整机或磁盘损坏。

## 二、文件与配置边界

### 服务器上创建或修改

- Create: `/etc/systemd/journald.conf.d/tongshi.conf`，限制 Tongshi 所在服务器的 journal 使用量。
- Create: `/etc/sysctl.d/99-tongshi.conf`，设置 Swap 使用倾向。
- Create: `/usr/local/sbin/tongshi-disk-check`，检查磁盘、Swap、journal、上传目录和后端健康状态。
- Create: `/etc/systemd/system/tongshi-disk-check.service`。
- Create: `/etc/systemd/system/tongshi-disk-check.timer`。
- Modify: `/home/ubuntu/tongshi_all_two/backend/.env`，只补充已被代码支持的 Redis 和连接池配置，不改密钥和数据库密码。
- Modify: `/etc/systemd/system/tongshi-backend.service`，补充 Redis 服务依赖；保留单 worker 和 `Restart=always`。
- Create: `/usr/local/sbin/tongshi-backup`，执行 MySQL 和上传文件本机备份。
- Create: `/etc/systemd/system/tongshi-backup.service`。
- Create: `/etc/systemd/system/tongshi-backup.timer`。
- Create: `/data/tongshi/backups/`，保存压缩备份和备份状态文件。

### 仓库中可选创建

- Create: `deploy/redeploy-server.ps1`，将服务器部署流程固化为可重复执行的 PowerShell 入口。
- Modify: `backend/docs/项目修改记录.md`，实施完成后记录服务器部署影响、备份策略和验证结果。
- Modify: `docs/superpowers/project-map.md`，仅在部署脚本或长期服务器目录成为稳定项目事实时更新。

## 三、实施任务

### Task 1：建立服务器现状快照和变更保护

**目标：** 在任何服务器配置变更前保存当前服务、环境文件权限、Nginx、磁盘和 Swap 状态，确保后续可以对比和恢复。

**Files:**
- Create: `/data/tongshi/backups/pre-hardening-$(date +%Y%m%d-%H%M%S)/`，保存脱敏配置和命令输出。
- Read: `/etc/systemd/system/tongshi-backend.service`。
- Read: `/home/ubuntu/tongshi_all_two/backend/.env`，只记录键名和权限，不记录密钥值。

- [ ] **Step 1：记录当前服务状态**

```bash
systemctl status tongshi-backend.service --no-pager -l
systemctl status nginx mysql redis-server --no-pager -l
systemctl list-timers --all --no-pager
```

预期：Tongshi、Nginx、MySQL、Redis 均能明确显示 `active` 或明确记录异常原因。

- [ ] **Step 2：记录资源和监听端口**

```bash
free -h
swapon --show
df -hT /
ss -lntp
```

预期：记录 2 核、内存、Swap、根分区、监听端口，作为后续验收基线。

- [ ] **Step 3：备份当前服务单元和 Nginx 配置**

```bash
SNAPSHOT_DIR="/data/tongshi/backups/pre-hardening-$(date +%Y%m%d-%H%M%S)"
sudo install -d -o root -g root -m 700 "$SNAPSHOT_DIR"
sudo cp -a /etc/systemd/system/tongshi-backend.service "$SNAPSHOT_DIR/"
sudo cp -a /etc/nginx/conf.d/tongshi.conf "$SNAPSHOT_DIR/"
sudo chmod 600 "$SNAPSHOT_DIR"/*
```

不复制 `.env` 内容到普通日志；如必须留档，只保存路径、权限和键名。

### Task 2：限制 journal 日志并设置 Swap 使用策略

**目标：** 将当前约 4GB 的 systemd journal 限制在 512MB 到 1GB 范围内，保留现有 4GB Swap，避免日志继续挤占系统盘。

**Files:**
- Create: `/etc/systemd/journald.conf.d/tongshi.conf`。
- Create: `/etc/sysctl.d/99-tongshi.conf`。

- [ ] **Step 1：创建 journal 限额配置**

```ini
[Journal]
SystemMaxUse=512M
SystemKeepFree=1G
RuntimeMaxUse=128M
MaxRetentionSec=14day
```

- [ ] **Step 2：设置 Swap 使用倾向**

```ini
vm.swappiness=10
```

Swap 只作为内存峰值缓冲，不把它当作扩大并发容量的替代品。

- [ ] **Step 3：加载配置并限制已有日志**

```bash
sudo systemctl daemon-reload
sudo systemctl restart systemd-journald
sudo journalctl --vacuum-size=512M
```

该步骤会删除超过保留上限的旧 journal 文件。执行前需确认不需要保留更久的历史日志。

- [ ] **Step 4：验证日志和 Swap**

```bash
journalctl --disk-usage
sysctl vm.swappiness
swapon --show
free -h
df -h /
```

预期：journal 占用不超过约 512MB，Swap 为 4GB，系统盘可用空间明显增加，Tongshi 服务不中断或仅出现 systemd 日志服务的短暂重载。

- [ ] **Step 5：创建磁盘和健康检查脚本**

`/usr/local/sbin/tongshi-disk-check` 使用以下逻辑：

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

free_kb="$(df -Pk / | awk 'NR == 2 { print $4 }')"
if [ "$free_kb" -lt 2097152 ]; then
  logger -t tongshi-disk-check "root filesystem free space is below 2GB: ${free_kb}KB"
  exit 1
fi

if ! swapon --show=NAME --noheadings | grep -qx /swapfile; then
  logger -t tongshi-disk-check "expected /swapfile is not active"
  exit 1
fi

if [ ! -d /data/tongshi/uploads ] || [ ! -w /data/tongshi/uploads ]; then
  logger -t tongshi-disk-check "Tongshi upload directory is missing or not writable"
  exit 1
fi

if ! curl -fsS --max-time 5 http://127.0.0.1:8050/health >/dev/null; then
  logger -t tongshi-disk-check "Tongshi health check failed"
  exit 1
fi

logger -t tongshi-disk-check "ok: root_free_kb=${free_kb}"
```

设置权限并先手动执行：

```bash
sudo chown root:root /usr/local/sbin/tongshi-disk-check
sudo chmod 755 /usr/local/sbin/tongshi-disk-check
sudo /usr/local/sbin/tongshi-disk-check
```

- [ ] **Step 6：创建磁盘检查 systemd timer**

`/etc/systemd/system/tongshi-disk-check.service`：

```ini
[Unit]
Description=Check Tongshi disk, swap and backend health
After=network-online.target tongshi-backend.service
Wants=network-online.target

[Service]
Type=oneshot
User=root
ExecStart=/usr/local/sbin/tongshi-disk-check
```

`/etc/systemd/system/tongshi-disk-check.timer`：

```ini
[Unit]
Description=Run Tongshi disk and health check periodically

[Timer]
OnBootSec=5min
OnUnitActiveSec=15min
Persistent=true

[Install]
WantedBy=timers.target
```

启用并验证：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now tongshi-disk-check.timer
systemctl list-timers tongshi-disk-check.timer --no-pager
sudo systemctl start tongshi-disk-check.service
sudo systemctl status tongshi-disk-check.service --no-pager -l
```

预期：检查任务成功退出；空间不足、Swap 未启用或后端健康检查失败时，任务以非零状态退出并写入 journal。

### Task 3：分析并处理 Docker 与开发工具占用

**目标：** 在不影响其他应用的前提下释放可回收空间；无法确认归属的目录只记录，不删除。

**Files:**
- Read: `/var/lib/docker`。
- Read: `/root/.trae-cn-server`。
- Read: `/root/.vscode-server`。
- Read: `/home/ubuntu/.vscode-server`。

- [ ] **Step 1：用 root 查看 Docker 可回收空间**

```bash
sudo docker system df -v
sudo docker ps -a --no-trunc
sudo docker volume ls
```

预期：分别得到镜像、容器、构建缓存和数据卷的实际占用；不得只根据 `/var/lib/docker` 总量直接执行清理。

- [ ] **Step 2：确认开发工具目录是否仍被使用**

```bash
ps -ef | grep -E 'vscode-server|trae-cn-server' | grep -v grep
sudo du -xhd1 /root/.trae-cn-server /root/.vscode-server /home/ubuntu/.vscode-server 2>/dev/null | sort -h
```

预期：明确运行中进程和最近使用目录。正在使用的目录不得清理。

- [ ] **Step 3：只清理已确认可回收的 Docker 缓存**

仅在确认没有其他业务依赖后执行：

```bash
sudo docker image prune
sudo docker builder prune
```

禁止执行以下命令：

```bash
sudo docker system prune -a
sudo docker volume prune
```

- [ ] **Step 4：再次确认磁盘**

```bash
sudo du -xhd1 /var /root /home /data 2>/dev/null | sort -h
df -h /
```

预期：只报告已确认安全的空间回收结果；未确认的旧工具和业务目录保留。

### Task 4：显式配置 Redis、数据库连接池和服务依赖

**目标：** 消除运行环境依赖漂移，确保单 worker 服务启动时 Redis 已就绪，并为后续多 worker 评估保留清晰边界。

**Files:**
- Modify: `/home/ubuntu/tongshi_all_two/backend/.env`。
- Modify: `/etc/systemd/system/tongshi-backend.service`。

- [x] **Step 1：补充已被代码支持的配置键**（已于 2026-07-19 在服务器执行）

在 `.env` 中补充以下配置；现有 `SECRET_KEY`、`DATABASE_URL`、`MYSQL_PASSWORD` 等值不得改变：

```env
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0
REDIS_POOL_SIZE=5
REDIS_SOCKET_TIMEOUT=5
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=5
DB_POOL_RECYCLE=1800
DB_POOL_TIMEOUT=30
```

当前代码支持 `REDIS_HOST`、`REDIS_PORT`、`REDIS_DB`、`REDIS_POOL_SIZE` 和 `REDIS_SOCKET_TIMEOUT`，没有 `REDIS_ENABLED` 配置；本任务不自行添加不存在的开关。

- [x] **Step 2：补充 systemd 服务依赖**（已于 2026-07-19 在服务器执行）

将服务单元的 `[Unit]` 调整为：

```ini
[Unit]
Description=Tongshi FastAPI Backend
After=network.target mysql.service redis-server.service
Wants=mysql.service redis-server.service
```

保留以下运行策略：

```ini
Restart=always
RestartSec=5
```

`ExecStart` 继续使用单 worker 的生产命令，不加入 `--reload`：

```ini
ExecStart=/home/ubuntu/tongshi_all_two/backend/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8050
```

- [x] **Step 3：重载并验证依赖顺序**（已于 2026-07-19 在服务器执行）

```bash
sudo systemctl daemon-reload
sudo systemctl restart tongshi-backend.service
systemctl is-active tongshi-backend.service
redis-cli -h 127.0.0.1 ping
curl -fsS http://127.0.0.1:8050/health
journalctl -u tongshi-backend.service -n 40 --no-pager
```

预期：服务为 `active`，Redis 返回 `PONG`，健康接口返回 `{"status":"ok","version":"1.0.0"}`，日志显示数据库初始化完成和应用启动完成。

- [ ] **Step 4：保留多 worker 决策门槛**

在 `main.py` 的 `Base.metadata.create_all()` 和 schema 兼容逻辑补齐 MySQL 启动锁、并完成并发启动测试前，不修改 `ExecStart` 为多 worker。当前服务器优先保证单 worker 稳定运行。

#### Task 4 实际执行记录（2026-07-19）

- 已在修改前创建仅 root 可读的配置快照：`/data/tongshi/config-snapshots/redis-db-pool-20260719-162347/`；其中包含修改前的后端 `.env` 与 `tongshi-backend.service`，未将敏感内容写入项目仓库或命令输出。
- 已在服务器 `.env` 仅新增本任务约定的 9 个 Redis / 数据库连接池键：Redis 指向 `127.0.0.1:6379`、DB `0`、连接池 `5`、socket 超时 `5` 秒；数据库连接池为 `5 + 5`、连接回收 `1800` 秒、获取超时 `30` 秒。既有 `DATABASE_URL`、`SECRET_KEY`、MySQL 凭据均未改动。
- 已将 `tongshi-backend.service` 的 `After` 与 `Wants` 同时补为 `mysql.service redis-server.service`；保留单 worker、`Restart=always` 与 `RestartSec=5`，实际 `ExecStart` 继续监听 `127.0.0.1:8050`，不向公网直接开放后端端口。
- 已执行 `systemctl daemon-reload` 和 `systemctl restart tongshi-backend.service`。2026-07-19 16:24（Asia/Shanghai）二次复核：Tongshi 后端与 Redis 均为 `active`，`/health` 返回 200，Redis 返回 `PONG`，应用实际加载的全部 9 项参数与目标值一致，启动日志无异常。
- 未执行数据库迁移、Nginx 重载、MySQL / Redis 重启或前端构建。服务器 `.env` 当前仍为 `664`，其凭据文件权限收紧应作为独立安全变更另行评估，不在本任务中混改。

### Task 5：固化单机部署流程

**目标：** 把本次已经验证过的部署步骤固化为可重复执行的流程，避免再次出现“代码已构建但静态文件未同步”或“requirements 未安装”的半部署状态。

**Files:**
- Create: `deploy/redeploy-server.ps1`。
- Modify: `backend/docs/项目修改记录.md`，实施完成后记录服务器影响。

- [x] **Step 1：定义部署前检查**

部署脚本必须在远端执行以下检查，任一项失败立即退出：

```bash
test -d /home/ubuntu/tongshi_all_two/.git
test -x /home/ubuntu/tongshi_all_two/backend/.venv/bin/python
test -f /home/ubuntu/tongshi_all_two/backend/.env
test -f /home/ubuntu/tongshi_all_two/frontend/.env.production
df -Pk / | awk 'NR==2 { if ($4 < 2097152) exit 1 }'
```

最后一条要求至少保留约 2GB 可用空间，避免构建过程中把系统盘写满。

- [x] **Step 2：定义后端依赖同步**

```bash
cd /home/ubuntu/tongshi_all_two
git pull --ff-only origin main
backend/.venv/bin/python -m pip install -r backend/requirements.txt
```

脚本必须保留并校验未跟踪的 `frontend/.env.production`，不得执行 `git clean -fd` 或覆盖 `.env`。

- [x] **Step 3：定义前端构建和静态同步**

```bash
cd /home/ubuntu/tongshi_all_two/frontend
npm run build </dev/null
rsync -a --delete /home/ubuntu/tongshi_all_two/frontend/dist/ /var/www/tongshi/
```

使用 `</dev/null`，避免 npm 子进程吞掉后续 SSH 脚本输入。同步前后记录 `index.html` 时间戳。

- [x] **Step 4：定义服务重启和健康检查**

```bash
sudo systemctl restart tongshi-backend.service
for i in $(seq 1 12); do
  if systemctl is-active --quiet tongshi-backend.service && curl -fsS http://127.0.0.1:8050/health >/dev/null; then
    exit 0
  fi
  sleep 2
done
journalctl -u tongshi-backend.service -n 80 --no-pager
exit 1
```

脚本只有在服务健康检查成功后才返回成功；失败时输出日志，不宣称部署完成。当前单 worker 方案允许重启期间出现短暂 API 不可用，前端静态文件仍由 Nginx 提供。

- [x] **Step 5：验证部署脚本的保留项**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy\redeploy-server.ps1 -DryRun
```

预期：DryRun 只打印 SSH、拉取、构建、同步、重启和验证步骤，不连接服务器、不修改本地和远端文件。

本地已完成：`deploy/redeploy-server.ps1` 已创建并通过静态契约测试与 Windows PowerShell DryRun 验证。服务器真实部署、systemd、journal、Swap、Docker 和备份相关步骤尚未执行。

### Task 6：建立本机 MySQL 与上传文件备份

**目标：** 在没有外部存储的前提下，提供最低限度的误操作恢复能力，并避免备份任务把 40GB 系统盘写满。

**Files:**
- Create: `/usr/local/sbin/tongshi-backup`。
- Create: `/etc/systemd/system/tongshi-backup.service`。
- Create: `/etc/systemd/system/tongshi-backup.timer`。
- Create: `/data/tongshi/backups/mysql/`。
- Create: `/data/tongshi/backups/uploads/`。

- [ ] **Step 1：创建备份目录并限制权限**

```bash
sudo install -d -o root -g root -m 700 /data/tongshi/backups/mysql /data/tongshi/backups/uploads
```

- [ ] **Step 2：实现数据库备份**

备份脚本必须从 `/home/ubuntu/tongshi_all_two/backend/.env` 读取 `MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_DATABASE`，生成权限为 `600` 的临时 MySQL option 文件，执行：

```bash
mysqldump --defaults-extra-file="$MYSQL_OPT_FILE" \
  --single-transaction --routines --events "$MYSQL_DATABASE" \
  | gzip -c > "/data/tongshi/backups/mysql/tongshi-$(date +%Y%m%d-%H%M%S).sql.gz"
```

临时 option 文件必须在成功和失败路径都删除，密码不得出现在命令日志、systemd 状态或备份文件名中。

- [ ] **Step 3：实现上传文件备份和保留策略**

对 `/data/tongshi/uploads` 创建按日期命名的压缩快照，保留最近 3 份；删除前先确认文件属于 Tongshi 上传目录，不处理其他 `/data` 内容。

- [ ] **Step 4：加入磁盘保护**

备份开始前检查根分区剩余空间至少 2GB；不足时记录错误并退出，不继续生成备份。备份结束后执行：

```bash
gzip -t /data/tongshi/backups/mysql/tongshi-*.sql.gz
tar -tf /data/tongshi/backups/uploads/tongshi-*.tar.gz >/dev/null
```

- [ ] **Step 5：创建 systemd timer**

`/etc/systemd/system/tongshi-backup.service`：

```ini
[Unit]
Description=Tongshi local backup
After=mysql.service
Wants=mysql.service

[Service]
Type=oneshot
User=root
ExecStart=/usr/local/sbin/tongshi-backup
```

`/etc/systemd/system/tongshi-backup.timer`：

```ini
[Unit]
Description=Run Tongshi local backup daily

[Timer]
OnCalendar=*-*-* 03:30:00
Persistent=true

[Install]
WantedBy=timers.target
```

- [ ] **Step 6：启用并验证备份任务**

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now tongshi-backup.timer
systemctl list-timers tongshi-backup.timer --no-pager
sudo systemctl start tongshi-backup.service
sudo systemctl status tongshi-backup.service --no-pager -l
find /data/tongshi/backups -type f -maxdepth 3 -printf '%p %s bytes\n'
```

预期：手动备份成功，MySQL 压缩文件和上传文件快照均存在，备份脚本没有输出密码，磁盘剩余空间仍高于 2GB。

### Task 7：阶段验收与文档同步

**Files:**
- Modify: `backend/docs/项目修改记录.md`。
- Modify: `docs/superpowers/project-map.md`，仅当新增部署脚本成为稳定入口时修改。

- [ ] **Step 1：执行服务验收**

```bash
systemctl is-active tongshi-backend.service
systemctl is-active nginx.service
systemctl is-active mysql.service
systemctl is-active redis-server.service
curl -fsS http://127.0.0.1:8050/health
curl -fsSI http://127.0.0.1/
redis-cli -h 127.0.0.1 ping
```

- [ ] **Step 2：执行资源验收**

```bash
df -h /
free -h
swapon --show
journalctl --disk-usage
sudo du -xhd1 /var /root /home /data 2>/dev/null | sort -h
```

- [ ] **Step 3：执行项目回归验证**

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests -q
cd ..\frontend
npm run build
```

如服务器只做运维配置而未同步本地代码，应在报告中明确区分“服务器健康检查通过”和“完整业务测试未在服务器执行”。

- [ ] **Step 4：同步修改记录**

修改记录必须写明：

- 服务器新增或修改了哪些 systemd、journal、备份和环境配置。
- 是否重启后端、Nginx、MySQL 或 Redis。
- 数据库是否执行迁移；本计划默认不执行数据库迁移。
- 服务器部署影响：本阶段只使用单机本地备份，未改变外部基础设施；若后续前端或后端代码再次发布，需重新执行部署脚本。

## 四、风险与决策门槛

| 风险 | 影响 | 控制方式 |
|---|---|---|
| journal 清理删除旧日志 | 历史排障信息减少 | 先保存当前日志占用，限额前确认保留周期 |
| Docker 清理误伤其他系统 | 其他应用停止或数据丢失 | 先用 root 查看 `docker system df -v`，禁止清理数据卷 |
| 备份占用本机磁盘 | 系统盘再次写满 | 备份前检查剩余空间，限制保留数量 |
| 单 worker 重启短暂不可用 | API 在重启窗口失败 | 健康检查轮询，失败不报告成功；多 worker 延后到启动锁完成后 |
| requirements 与虚拟环境漂移 | 部署后服务启动失败 | 每次部署执行 `pip install -r backend/requirements.txt` 并验证 import |
| 本机备份无法抵御整机故障 | 服务器损坏时备份同时丢失 | 在本阶段报告中明确限制，未来接入外部存储后再升级 |

## 五、完成标准

- journal 占用不超过设定上限，磁盘剩余空间至少 2GB。
- Swap 保持 4GB 且重启后仍自动启用。
- `tongshi-backend.service`、Nginx、MySQL、Redis 均可正常启动。
- `/health` 返回 200，Redis 返回 `PONG`，Nginx 能返回最新前端静态文件。
- 部署流程包含依赖安装、前端构建、静态同步、服务重启和健康检查。
- 本机 MySQL 和上传文件备份任务可手动成功执行，并有每日 timer。
- 不删除未确认的 Docker 卷、旧开发工具和业务数据。
- 修改记录明确写出服务器部署影响和未验证路径。
