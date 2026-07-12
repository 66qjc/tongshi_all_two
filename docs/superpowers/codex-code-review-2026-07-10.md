# 2026-07-10 多角度代码审查报告

## 一、审查结论

当前工作区包含 134 项已修改、删除或未跟踪内容；已跟踪 diff 涉及 82 个文件，约 4880 行新增、4041 行删除。本轮从后端权限与数据一致性、前端流程与接口契约、缓存与数据库兼容、测试与部署可靠性四个角度复核。

结论：当前改动不能直接部署。审查确认存在权限越界、完成状态误判、共享题库误删、密码变更后旧 JWT 未统一失效、软删除关系丢失、私有文件长效 Token 暴露、并发进度丢失、Redis 缓存实际不可用、旧 MySQL 缺索引等高风险问题。此前报告中“严重缺陷已修复”“兼容性优秀”的判断不再成立，必须以本报告和 2026-07-10 修复设计为准。

本轮只完成审查、设计和实施计划，没有修改业务代码，也没有执行 Git 暂存、提交或推送。

## 二、验证基线

- 前端 `npm run build`：通过，仅有既有大 chunk 警告。
- 前端静态测试：4 项失败，分别为 `copy-consistency-static.test.mjs`、`course-detail-layout-static.test.mjs`、`home-branding-static.test.mjs`、`message-refresh-static.test.mjs`。
- 后端全量测试：曾得到 `226 passed, 2 failed, 3 errors`。
- 后端业务失败：多题作业只答一题即出现完成记录；重复题目错误文案与断言不一致。
- 后端 3 个 error：Windows pytest 系统临时目录 `PermissionError`，后续验收必须使用工作区 `tmp/` 下的显式 `--basetemp`。
- 定向后端测试曾得到 76 passed，但没有覆盖真实失败用例，不能作为全量通过证据。

## 三、高风险问题

### 1. 作业答一题即创建正式完成记录

`backend/app/services/quiz_service.py` 的 `_update_assignment_score()` 在存在任意答题记录时创建 `TaskCompletion`，使教师完成报告和学生完成状态失真。`submit_answer()` 还分两次提交，答题与计分不是单事务；并发最后一题可能撞上完成记录唯一约束。

目标：部分答题只保留 `QuizAttempt`；全部题目答完后才创建一条完成记录；答题、评分、完成记录在最外层业务服务中只提交一次，并用保存点处理并发唯一键竞争。

### 2. 教师通知接口可跨班发送

`backend/app/api/v1/routes/notification_routes.py` 丢弃当前操作人，`notification_service.py` 只校验目标是学生，没有验证学生是否属于教师创建的班级。教师可向其他教师班级学生发送单条或批量通知。

目标：教师只通知自己班级中的未删除学生；管理员可通知任意未删除学生；批量接口返回实际发送和跳过数量；`action_url` 只允许站内单斜杠路径。

### 3. 密码变更与 Token 失效路径不完整

登录态改密已递增 `token_version`，但当前响应不返回新 Token，前端随后用旧 Token 设置密保会收到 401。密保答案重置、教师/管理员审批重置、管理员直接重置教师密码没有全部递增版本。软删除用户仍可能登录或复用旧 JWT；密码与审计日志存在分两次提交的半完成状态。

目标：所有密码写入路径统一轮换版本；登录态改密返回并立即保存新 JWT；登录、普通 API 和文件 API都过滤软删除用户；密码与审计同事务。

### 4. 课程删除会误伤共享题库并转移编辑权限

课程软删除级联包含 `Question`；公共课程删除无承接课程时会让题目随课程消失。现有转挂按任意课程选择目标，而教师编辑权限又按目标课程所有者判断，会把编辑权从贡献教师转给其他教师。

目标：题目先转挂到未删除共享根或其他外键锚点，课程级联不包含题目；无承接目标时拒绝删除；教师编辑权限依据 `Question.created_by`，不能随 `course_id` 转移。

### 5. 七类软删除入口不完整且提前物理删除关联

当前只有部分课程删除进入回收站。班级删除会清理公告关联、已读和完成记录，作品删除会清理图片和点赞，管理员删除教师会清理大量业务数据；即使把最后一个 `db.delete()` 替换成软删除，恢复后关联仍无法找回。作品真实删除逻辑位于 `project_service.py`，旧计划曾错误指向 `teacher_service.py`。

目标：用户、课程、班级、公告、作品、资料、题目正式删除都调用软删除；软删除前不物理清理关联；题目被未删除作业引用时拒绝删除；回收站支持字符串用户 ID；彻底删除仅从回收站执行。

### 6. 软删除资源的文件仍可读取

`backend/app/services/file_service.py` 的项目、资料、预览和课程权限查询没有统一过滤 `deleted_at`。软删除资料或作品后，旧 URL 或旧签名仍可能继续读取原文件。

目标：文件授权链过滤软删除用户、课程、资料、作品和预览；删除后旧凭据立即失去业务访问权，恢复后重新可访问。

### 7. 私有大文件预览依赖长效 JWT 查询参数和完整 Blob 下载

`frontend/src/utils/url.ts` 把普通登录 JWT 追加到 `/api/files` 与 `/api/materials` URL；`useAuthenticatedFileUrl.ts` 又完整下载大文件再创建 Blob。这样既暴露长效 Token，也破坏 PDF/视频 Range 流式读取。受影响的不只是课程资料，还包括作品图片、报告、教师审核和管理员 PDF。

目标：普通 Bearer Token 只申请 5 分钟文件级 URL；Token 限定 `scope` 和 `file_id`；全部私有文件消费者迁移到签名 URL；取消旧请求并提前续签；通用 URL 工具不再读取 localStorage 或拼接登录 Token。

### 8. 课时进度并发写入丢失且浏览次数口径错误

`progress_service.py` 先读 ORM 再在 Python 累加时长和次数，首次并发可能撞唯一约束，既有记录并发会丢失更新；每个 30 秒心跳都增加 `view_count`。课程页还以 `viewRoute.fullPath` 为 key，切换 `lesson_id` 查询参数会重建页面，导致一次切课可能重复计算访问。

目标：SQLite/MySQL 方言 upsert 与数据库原子累加；新增 `visit_started`；心跳不增加访问次数；路由组件 key 排除查询参数；隐藏、`pagehide`、卸载共用一次最终补报。

### 9. 非视频课时无法完成，课程分析加载全量 ORM

没有视频的课时只能维持 10%，学生无法主动完成。教师课程分析一次加载全部 `LessonProgress` 并在 Python 计算，还把完整学生数组返回前端，不满足 100 名学生 × 20 课时的规模要求。

目标：无视频课时提供“完成本课”；课程分析使用数据库聚合，学生明细服务端分页，查询数不随学生课时笛卡尔积增长。

### 10. Redis 缓存键、序列化和权限边界均不可靠

缓存默认键包含 SQLAlchemy Session 地址；公共课程列表和课程详情缓存 ORM/ORM 元组，无法稳定 JSON 序列化；失效使用 `KEYS`；Redis 未启动时每个请求重复连接并记录告警。课程详情若只按 `course_id` 缓存，还可能由所有者预热后让其他教师命中私有 DTO。

目标：默认关闭 Redis；显式稳定键；只缓存最终 JSON DTO；课程详情键包含角色与用户且命中前完成授权；连接失败冷却；模式失效使用 `SCAN`。

### 11. 题干哈希存在 MD5/SHA-256 双轨风险

当前 `question_service.py` 使用 32 位 MD5；新计划改 SHA-256。如果兼容层只处理空值，历史非空 MD5 会永久保留，新查询无法命中旧题。题目编辑和部分管理员/导入路径也没有统一更新哈希。

目标：提取唯一规范化与 SHA-256 函数；创建、编辑、管理员新增、导入统一调用；兼容层至少重算 NULL、空值和长度不为 64 的全部旧记录；哈希保持普通索引。

### 12. 既有 MySQL 不会自动获得 ORM 新索引，启动锁覆盖不完整

`Base.metadata.create_all()` 不会为已存在表补新索引；当前 `schema_compat.py` 主要补表和列。若只在兼容函数中加锁，`main.py` 先执行的 `create_all()` 仍在锁外，多 worker 首次启动可能竞争 DDL。

目标：命名锁在 `create_all()` 前获取；同一连接执行建表、兼容 DDL、哈希升级和索引补齐；释放锁覆盖成功与异常路径；真实 MySQL 测试库验证并发初始化。

## 四、前端流程与可靠性问题

- 随机点名读取不存在的 `classData.students`，动画期间切班或卸载没有清理 interval，旧请求可能覆盖新班级。
- `/create` 当前标为公开，但页面请求受保护接口，与首页“登录后查看作品展示”矛盾。
- 通知中心首屏任一请求失败会永久 loading；缺 15 秒刷新、可见性刷新和跨组件刷新。
- 如果把偏好加载放进消息轮询，15 秒刷新会覆盖用户尚未保存的偏好表单；消息轮询应与偏好加载分开。
- 页头最近通知直接跳转，没有先标记已读；失败时也没有中文提示。
- 作品审核通知使用 `/projects/{id}`，前端真实路由是 `/create/project/{id}`。
- 公开课程资料在已登录状态下会因 `file_id` 优先级错误改走私有接口。
- 当前 4 个静态测试失败中，消息刷新和文案是真实回归；课程布局与品牌测试含过期断言，应更新为当前已确认的 `booksite-layout` 和学校徽标契约，不能简单删除测试。

## 五、测试与部署风险

- SQLite 内存库和单 Session 不能证明 MySQL 唯一键竞争与行级并发；并发用例必须使用独立 Session，并在真实 MySQL 测试库重复验证。
- PowerShell `ForEach-Object { node test }` 会吞掉中途失败，必须汇总 `$LASTEXITCODE` 后显式退出 1。
- Windows pytest 临时目录权限问题必须用 `--basetemp=tmp/...` 规避，不能把环境 error 与业务失败混为一谈。
- 本地 Uvicorn 不执行 Nginx `X-Accel-Redirect`，不能在本地声称公开 PDF 文件体或公开 Range 已验证；服务器 Nginx 需要单独证据。
- 忘记密码失败计数当前是进程内字典，多 worker 会放大尝试次数；Redis 开启时必须改为共享原子计数。多 worker 关闭 Redis 不能验收为安全通过。
- 当前工作区存在大量用户改动，目录级 `git add backend frontend docs` 会混入无关文件；所有计划都已取消自动提交步骤。

## 六、修复拆分

1. 阶段 A：作业完成与事务、密码/JWT/前端续签、教师通知、课程删除与共享题库。
2. 阶段 B：随机点名、作品入口、通知中心、课时进度、非视频完成、课程分析分页。
3. 阶段 C：文件专用 Token、签名 URL、全部私有文件消费者迁移、Range 与取消/续签。
4. 阶段 D：七类软删除、文件权限过滤、题干哈希、Redis 缓存、跨 worker 限流、索引与启动锁。

对应文档：

- `docs/superpowers/specs/2026-07-10-code-review-remediation-design.md`
- `docs/superpowers/plans/2026-07-10-remediation-phase-a-security-correctness.md`
- `docs/superpowers/plans/2026-07-10-remediation-phase-b-frontend-progress.md`
- `docs/superpowers/plans/2026-07-10-remediation-phase-c-file-preview.md`
- `docs/superpowers/plans/2026-07-10-remediation-phase-d-soft-delete-cache-db.md`

## 七、服务器部署影响

本轮只更新审查、设计和实施计划，不需要服务器拉代码、重启服务、重新构建前端、执行数据库迁移、调整环境变量、Redis 或 Nginx。

未来实施全部阶段后，预计需要备份 MySQL 与上传目录、拉取代码、重启后端、重新构建前端、按 worker 数配置 Redis，并由单实例先完成兼容升级。真实操作以各阶段验证记录为准。
