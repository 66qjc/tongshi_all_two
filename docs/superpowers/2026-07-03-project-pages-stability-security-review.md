# 2026-07-03 项目页面完成度、代码稳定性与安全性审查报告

## 一、结论摘要

本次审查按只读方式完成，未修改业务代码，未回滚当前工作区已有改动。审查覆盖当前工作树可见源码、前端页面、后端路由与服务、测试、部署配置和项目文档。当前项目功能完整度整体较高，教师端、学生端和管理员端主流程已经成型；主要短板集中在安全边界、文件访问权限、密码重置授权、部署配置一致性和部分分页/错误态稳定性。

当前最高优先级风险为 3 个 P0：

1. `/api/files/{file_id}` 通用文件接口无鉴权，任意未登录用户可按自增 `file_id` 枚举读取 StoredFile。
2. 公开注册接口允许创建教师账号，访客可自助获得教师权限。
3. 教师端密码重置审批接口未校验申请人是否属于当前教师班级，教师可跨班级审批或驳回密码重置申请。

需要优先修复 P0，再处理 P1 中的明文临时密码、教师批量删除学生、文件路径边界、JWT 查询参数、外链校验、Nginx 上传目录不一致等问题。

## 二、审查范围与方法

### 2.1 使用的审查方式

- 使用 `dispatching-parallel-agents` 分为学生端、教师/管理员端、后端权限安全、部署测试文档 4 个独立区域并行审查。
- 使用 `graphify query` 获取项目图谱上下文，再以当前磁盘源码为准逐项核对。
- 使用 `rg --files`、`rg`、`Select-String`、路由表和关键源码读取进行文件级覆盖。
- 不运行会写入产物的构建、测试或部署命令。
- 不修改业务代码、不清理未提交文件、不回滚已有删除项。

### 2.2 当前工作区状态

审查开始时 `git status --short` 显示当前工作区已有大量未提交修改、删除和未跟踪文件，涉及后端路由/服务、前端页面、文档和测试。本文结论基于 2026-07-03 当前磁盘内容，不代表某个干净提交。

已观察到的工作区特征：

- 当前可见文件约 255 个。
- `frontend/src` 约 90 个文件。
- `frontend/tests` 约 20 个文件。
- `backend/app` 约 68 个文件。
- `backend/tests` 约 30 个文件。
- `docs` 与 `backend/docs` 约 15 个文件。
- 部署、构建、根配置和其他文件合计约 28 个。

说明：运行期上传目录、缓存、`.git`、`node_modules`、虚拟环境和构建产物不属于本次源码审查对象。

### 2.3 评分口径

- 完成度：业务功能是否成型，页面/接口是否覆盖目标流程。
- 稳定性：分页、错误态、空态、异步状态、测试与部署可复现性。
- 安全性：鉴权、越权、文件访问、输入校验、XSS、密码和令牌处理。

评分为 1-5 分：

- 5：成熟，只有低风险改进。
- 4：基本可靠，有少量可控缺口。
- 3：可用但存在明显稳定性或体验债务。
- 2：关键边界不足，需要优先治理。
- 1：存在高危风险或核心安全边界缺失。

## 三、全局风险清单

### P0-1 通用文件接口无鉴权，任意用户可读取 StoredFile

证据：

- `backend/app/api/v1/routes/file_routes.py:74` 定义 `GET /files/{file_id}`。
- `backend/app/api/v1/routes/file_routes.py:75-78` 只有 `Request` 和 `db` 依赖，没有 `get_current_user` 或业务授权依赖。
- `backend/app/services/file_service.py:78` 通过 `file_id` 读取 `StoredFile`。
- `backend/app/api/v1/__init__.py:38` 已挂载 `file_router`。
- `backend/main.py:103` 仍公开挂载 `/uploads` 静态目录。

影响：

- 私有课程资料、作品报告、项目图片、后台上传图片等只要进入 `StoredFile`，都可能被枚举读取。
- `security.py` 中的 query token 回退对该路由没有实际保护，因为该路由没有调用 `get_current_user`。
- 资料专用 `/api/materials/{id}/file` 有鉴权，但如果前端或数据中仍暴露 `/api/files/{file_id}`，会绕开业务归属控制。

建议：

- 为 `/api/files/{file_id}` 增加鉴权和业务归属授权，至少区分公开文件、本人上传、课程资料、作品附件、后台图文资源。
- 对无法判定归属的历史文件默认拒绝，必要时新增 `StoredFile.visibility` 或 `biz_type/biz_id` 授权矩阵。
- 生产环境移除或限制 `/uploads` 静态挂载，保留 Nginx `internal` 方式。
- 增加测试：未登录不能访问任意 `/api/files/{id}`；非课程成员不能访问私有课程资料文件；公开学习资料仅通过公开资料接口访问。

### P0-2 公开注册允许创建教师账号

证据：

- `frontend/src/views/RegisterView.vue:15` 前端注册表单允许 `student | teacher`。
- `frontend/src/views/RegisterView.vue:97-99` 页面暴露“教师”注册选项。
- `backend/app/api/v1/routes/auth_routes.py:30` `/register` 为公开接口。
- `backend/app/services/auth_service.py:36-48` 后端允许 `{"student", "teacher"}` 并按请求体写入 `role`。
- `backend/app/schemas/common.py:30` `RegisterRequest.role` 由请求体传入。

影响：

- 访客可自建教师账号，再访问教师工作台。
- 可创建课程、上传资料、发布题目、导入学生，扩大攻击面。

建议：

- 公开注册仅允许学生。
- 教师账号只允许管理员创建或批量导入。
- 后端必须强制拒绝 `role=teacher` 的公开注册请求；前端只隐藏选项不够。
- 增加测试：`POST /api/register` 传 `role=teacher` 必须失败。

### P0-3 教师可跨班级审批或驳回密码重置申请

证据：

- `backend/app/api/v1/routes/teacher_routes.py:483` 教师端审批密码重置接口只要求教师角色。
- `backend/app/api/v1/routes/teacher_routes.py:489` 直接调用 `approve_reset_request(db, request_id, current_user.id)`。
- `backend/app/api/v1/routes/teacher_routes.py:492-499` 驳回同理。
- `backend/app/services/auth_service.py:260` `approve_reset_request` 只按 `request_id` 查询。
- `backend/app/services/auth_service.py:286` `reject_reset_request` 只按 `request_id` 查询。

影响：

- 教师只要猜到或拿到其他班级学生的申请 ID，就能审批或驳回该申请。
- 审批通过会直接重置学生密码。

建议：

- 为教师审批/驳回增加“申请人属于当前教师任一班级”的服务层校验。
- 管理员审批可以保留全局权限，但应与教师路径分开。
- 增加测试：教师不能审批/驳回非本班学生的重置申请。

### P1-1 临时密码明文持久化并在列表返回

证据：

- `backend/app/services/auth_service.py:279` 将 `req.temp_password = new_pwd` 写入数据库。
- `backend/app/services/auth_service.py:283` 审批响应返回临时密码。
- `backend/app/services/auth_service.py:318` 列表输出继续返回 `temp_password`。

影响：

- 数据库泄漏、接口越权、前端缓存或截图都可能暴露可用密码。
- 与“首次登录强制改密”相比，明文长期保存仍然扩大风险。

建议：

- 只在审批响应中一次性返回临时密码，不在列表长期返回。
- 数据库只保存密码哈希和审批状态。
- 前端用一次性弹窗展示并提醒教师立即复制。

### P1-2 教师批量删除学生会删除全站学生账号和数据

证据：

- `backend/app/api/v1/routes/teacher_routes.py:68` 教师批量删除学生接口只校验学生属于当前教师任一班级。
- `backend/app/services/class_service.py:92` `_delete_student_data` 删除学生所有关联数据。
- `backend/app/services/class_service.py:109-110` 删除所有班级关系并删除 `User`。

影响：

- 多教师、多课程、多班级场景下，一个教师可以删除其他教师课程中的学生账号和作品/答题/任务数据。

建议：

- 教师端“删除学生”默认改为从当前教师班级移除，而不是删除全站账号。
- 若确需删除账号，应仅管理员可执行，并做依赖确认。
- 增加测试：同一学生属于两个教师班级时，教师操作不能破坏其他教师班级数据。

### P1-3 通用文件流和预览生成未统一做目录边界校验

证据：

- `backend/app/services/file_service.py:88` 仅兼容性剥离 `/uploads/`。
- `backend/app/services/storage_local.py:60` 直接以 `root_dir / object_key` 打开文件。
- `backend/app/services/material_preview_service.py:71` 也只处理 `/uploads/` 前缀。
- `backend/app/services/file_service.py:114-127` 已有 `normalize_local_object_key` 和 `build_x_accel_redirect_path`，但通用文件流没有复用。

影响：

- 正常上传生成随机文件名可降低风险。
- 但历史数据、异常写入或被污染的 `StoredFile.object_key` 可能导致路径穿越读取。

建议：

- 所有本地文件读取统一使用 `normalize_local_object_key`。
- `LocalStorageAdapter` 内部也应校验 resolve 后路径必须位于 `root_dir` 下。
- 增加 `object_key="../x"` 的回归测试。

### P1-4 JWT 被追加到文件预览查询参数，且默认配置不接受 query token

证据：

- `frontend/src/utils/url.ts:15-19` 对 `/api/files/` 和 `/api/materials/` 自动追加 `?token=`。
- `frontend/src/api/material.ts:70` 登录资料预览使用 `/api/materials/{id}/file`。
- `backend/app/core/config.py:40` `ALLOW_QUERY_TOKEN_FOR_FILES` 默认 `false`。

影响：

- Token 可能进入浏览器历史、代理日志、服务器访问日志、Referer 或被复制分享。
- 站内 `<video>`、`<object>` 无法携带 Authorization 时，登录态资料预览依赖服务器环境变量，配置不一致会导致预览失败。

建议：

- 优先改为短期一次性文件访问票据，或后端设置同站 Cookie 鉴权。
- 若短期内继续使用 query token，必须明确部署配置和日志脱敏策略。
- 前端公开资料继续走 `/api/public/learning/materials/{id}/file`，登录资料走专用授权文件接口。

### P1-5 作品和活动外链缺少 URL scheme 校验

证据：

- `frontend/src/views/ProjectUploadView.vue:183` 直接提交 `link_url`。
- `frontend/src/views/ProjectDetailView.vue:140` 直接绑定外链 `href`。
- `frontend/src/views/ActDetailView.vue:142` 直接绑定图文链接。

影响：

- `javascript:`、异常协议或恶意跳转链接可能被写入后在前端点击执行或误导用户。

建议：

- 前后端同时限制外链 scheme 为 `http` 或 `https`。
- 后端 Schema 或服务层规范化 URL。
- 前端渲染前再次过滤异常链接。

### P1-6 管理员删除教师的前端依赖确认漏判

证据：

- `frontend/src/views/admin/AdminTeachers.vue:72` `hasDeps` 只判断课程、班级、公告。
- `frontend/src/views/admin/AdminTeachers.vue:80-81` 依赖说明中其实包含作品和图文内容。

影响：

- 当教师只有作品或图文内容依赖时，前端可能不走强制删除确认路径。

建议：

- 将 `project_count`、`showcase_count` 纳入 `hasDeps`。
- 删除确认文案展示所有依赖项。
- 补静态或组件测试。

### P1-7 Nginx 受保护上传目录与后端文档示例不一致

证据：

- `deploy/nginx.conf:6` 说明上传目录由 `.env` 的 `LOCAL_UPLOAD_DIR` 控制。
- `deploy/nginx.conf:71` 实际写死 `alias /var/www/tongshi/uploads/;`。
- `backend/.env.example:23` 和 `backend/README.md:52` 建议 `/data/tongshi/uploads`。

影响：

- 后端鉴权通过并返回 `X-Accel-Redirect` 后，Nginx 可能从错误目录取文件，导致预览 404。
- 测试若固化错误 alias，会让部署偏差长期存在。

建议：

- 明确服务器真实上传目录，并同步 `nginx.conf`、`.env.example`、README 和测试。
- 部署检查脚本应验证 Nginx alias 与 `LOCAL_UPLOAD_DIR` 一致。

### P1-8 运行时仍保留弱默认配置

证据：

- `backend/app/core/config.py:34` `ALLOWED_ORIGINS` 默认 `*`。
- `backend/app/core/config.py:35` `DATABASE_URL` 默认包含 `root:123456`。
- `backend/main.py:96-99` 直接启用 CORS，并允许 credentials。

影响：

- 如果生产只配置 `SECRET_KEY` 而跳过部署检查，服务仍可能以弱默认数据库和宽 CORS 启动。

建议：

- 生产环境启动时强校验：禁止默认数据库口令、禁止 `ALLOWED_ORIGINS=*`。
- 区分开发和生产配置，生产缺项直接拒绝启动。

## 四、页面完成度、稳定性与安全性评分

### 4.1 学生端与公共页面

| 路由 | 页面文件 | 完成度 | 稳定性 | 安全性 | 说明 |
|---|---|---:|---:|---:|---|
| `/` | `frontend/src/views/HomeView.vue` | 4 | 4 | 4 | 首页主流程完整，主要为静态展示，风险低。 |
| `/login` | `frontend/src/views/LoginView.vue` | 4 | 4 | 3 | 登录、找回密码、首次改密齐全，安全依赖后端限流与重置流程。 |
| `/register` | `frontend/src/views/RegisterView.vue` | 3 | 4 | 1 | 暴露教师注册，且后端允许教师自注册。 |
| `/learn` | `frontend/src/views/LearnView.vue` | 4 | 3 | 4 | 公开学习馆和已加入课程合并可用，加载失败页内错误态偏弱。 |
| `/learn/course/:courseId` | `frontend/src/views/CourseDetailView.vue` | 4 | 3 | 3 | 阅读、资料、进度完整；资料预览和 HTML 渲染依赖后端安全边界。 |
| `/practice` | `frontend/src/views/PracticeView.vue` | 4 | 3 | 3 | 练习入口完整，加载异常容易落为空态。 |
| `/practice/assignments` | `frontend/src/views/PracticeAssignments.vue` | 4 | 3 | 3 | 作业筛选和状态展示可用，失败态需加强。 |
| `/practice/quiz/:courseId` | `frontend/src/views/PracticeQuizView.vue` | 4 | 3 | 3 | 答题、草稿、多选完整；提交缺少 loading 锁和局部异常处理。 |
| `/practice/announcement/:announcementId` | `frontend/src/views/PracticeQuizView.vue` | 4 | 3 | 3 | 作业模式复用合理，完成状态依赖后端兜底。 |
| `/create` | `frontend/src/views/CreateView.vue` | 4 | 3 | 3 | 作品列表与分页可用，失败态主要靠 Toast。 |
| `/create/project/:id` | `frontend/src/views/ProjectDetailView.vue` | 4 | 3 | 2 | 展示完整；外链 scheme 与文件访问安全需补强。 |
| `/create/upload` | `frontend/src/views/ProjectUploadView.vue` | 4 | 3 | 2 | 新增/重提完整；链接和上传前端二次校验不足。 |
| `/portfolio` | `frontend/src/views/PortfolioView.vue` | 3 | 3 | 3 | 档案展示可用，失败和空态偏弱。 |
| `/profile` | `frontend/src/views/ProfileView.vue` | 4 | 4 | 3 | 密码、密保、错题、收藏较完整；路由未显式限制学生角色。 |
| `/inbox` | `frontend/src/views/InboxView.vue` | 4 | 3 | 3 | 消息和任务入口可用；未开始任务按钮前端限制不足。 |
| `/act` | `frontend/src/views/ActView.vue` | 4 | 3 | 3 | 公开活动展示可用，图片 URL 统一处理仍需检查。 |
| `/act/showcase/:id` | `frontend/src/views/ActDetailView.vue` | 4 | 4 | 3 | 图文块按文本渲染较安全，外链需 scheme 校验。 |
| `/change-password` | `frontend/src/views/ChangePasswordView.vue` | 4 | 4 | 3 | 改密与密保引导可用。 |
| `/about` | `frontend/src/views/AboutView.vue` | 4 | 5 | 5 | 静态页面，风险低。 |
| `/privacy` | `frontend/src/views/PrivacyView.vue` | 4 | 5 | 5 | 静态页面，风险低。 |
| `/contact` | `frontend/src/views/ContactView.vue` | 2 | 4 | 4 | 表单仅本地提示成功，未见真实提交链路。 |
| `/:pathMatch(.*)*` | `frontend/src/views/NotFoundView.vue` | 5 | 5 | 5 | 简单 404 页面。 |

学生端补充风险：

- `router/index.ts:16-23` 学生业务前缀未包含 `/profile`。
- `router/index.ts:293-299` 当前只重点拦截教师访问学生业务路径，管理员访问部分学生路径的边界不够清晰。
- `LessonReader.vue` 使用 `v-html`，后端 `html_sanitizer.py` 已做白名单清洗，但建议增加 XSS 回归测试，防止未来接口绕过清洗。

### 4.2 教师端与管理员端

| 路由 | 页面文件 | 完成度 | 稳定性 | 安全性 | 说明 |
|---|---|---:|---:|---:|---|
| `/teacher` | `TeacherDashboard.vue` | 4 | 4 | 4 | 概览、近期作业、待审作品可用。 |
| `/teacher/courses` | `TeacherCourses.vue` | 5 | 4 | 4 | 课程分页搜索、公共课程添加、删除确认较完整。 |
| `/teacher/courses/:courseId` | `TeacherCourseDetail.vue` | 4 | 4 | 4 | 课程、阶段、资料、课时管理完整，危险操作有确认。 |
| `/teacher/classes` | `TeacherClasses.vue` | 4 | 3 | 4 | 班级增删改可用，列表分页不足。 |
| `/teacher/publish` | `TeacherAnnouncements.vue` | 4 | 3 | 4 | 发布流程完整，发布记录和选题列表存在全量加载倾向。 |
| `/teacher/grades` | `TeacherStudents.vue` | 5 | 4 | 4 | 学生成绩分页、筛选、导出较完整。 |
| `/teacher/task-report` | `TeacherTaskReport.vue` | 4 | 3 | 4 | 作业概览可用，任务列表无分页。 |
| `/teacher/task-report/:taskId` | `TeacherTaskReportDetail.vue` | 4 | 3 | 4 | 完成/未完成列表可用，搜索和导出存在当前页/上限问题。 |
| `/teacher/reviews` | `TeacherReviews.vue` | 5 | 4 | 4 | 审核、驳回、删除、下载较完整。 |
| `/teacher/materials` | `TeacherMaterials.vue` | 5 | 4 | 4 | 资料分页、上传、预览、重建、删除确认完整。 |
| `/teacher/student-admin` | `TeacherStudentAdmin.vue` | 4 | 3 | 3 | 学生导入/移出/批删可用，但密码重置无事前确认，后端批删语义过重。 |
| `/teacher/questions` | `TeacherQuestions.vue` | 4 | 3 | 4 | 教师无删除入口，编辑按归属禁用；分页搜索一致性不足。 |
| `/admin` | `AdminLayout.vue` | 4 | 4 | 4 | 管理后台框架和角色守卫可用。 |
| `/admin/teachers` | `AdminTeachers.vue` | 4 | 3 | 3 | 教师管理和导入可用，删除依赖确认漏判作品/图文。 |
| `/admin/public-courses` | `AdminPublicCourses.vue` | 4 | 3 | 4 | 公共课程、资料、题库、同步状态完整，全量加载需治理。 |
| `/admin/showcase` | `AdminShowcase.vue` | 4 | 4 | 4 | 图文内容管理完整，危险操作有确认。 |
| `/admin/password-reset` | `AdminPasswordReset.vue` | 3 | 3 | 3 | 能处理申请，但重置无确认、驳回原因未提交、失败提示不足。 |

教师/管理员端补充风险：

- `AdminTeachers.vue:72` 删除教师依赖判断漏掉作品和图文内容。
- `AdminPasswordReset.vue:42`、`AdminPasswordReset.vue:56` 空 `catch` 吞掉失败。
- `TeacherStudentAdmin.vue:203` 重置操作无事前确认。
- `TeacherQuestions.vue` 标签/题干搜索与后端分页口径不完全一致。
- `TeacherTaskReportDetail.vue:129-131` CSV 导出用固定 `page_size: 9999`，大班级可能截断。

### 4.3 内容查看组件

| 文件 | 完成度 | 稳定性 | 安全性 | 说明 |
|---|---:|---:|---:|---|
| `frontend/src/views/content/PdfViewer.vue` | 3 | 3 | 3 | 作为内容查看器存在，但当前主流程主要走资料预览弹窗。 |
| `frontend/src/views/content/VideoPlayer.vue` | 3 | 3 | 3 | 作为内容查看器存在，主流程需统一文件授权策略。 |
| `frontend/src/components/common/MaterialPreviewDialog.vue` | 4 | 3 | 3 | PDF/视频站内预览完整，但授权 URL 依赖 query token 或公开接口。 |
| `frontend/src/components/lesson/LessonReader.vue` | 4 | 4 | 3 | 能解析课时富文本和资料占位；安全依赖后端白名单清洗。 |

## 五、后端模块稳定性与安全性评分

| 业务域 | 主要文件 | 完成度 | 稳定性 | 安全性 | 说明 |
|---|---|---:|---:|---:|---|
| 认证/用户/密码重置 | `auth_routes.py`、`auth_service.py`、`security.py`、`User`、`SecurityQuestion`、`PasswordResetRequest` | 4 | 3 | 2 | 登录、密保、人工重置完整，但教师自注册、跨班级审批、明文临时密码风险高。 |
| 课程/班级/学生/进度 | `course_routes.py`、`class_routes.py`、`lesson_service.py`、`progress_service.py`、`access_control_service.py` | 4 | 4 | 3 | 学生课程访问校验较完整，教师批量删除学生语义过重。 |
| 资料/文件/上传/预览 | `material_routes.py`、`upload_routes.py`、`file_routes.py`、`file_service.py`、`material_preview_service.py` | 4 | 3 | 1 | 专用资料预览有鉴权，通用文件接口无鉴权是最大风险。 |
| 题库/作业/练习 | `question_routes.py`、`quiz_routes.py`、`announcement_routes.py`、`task_service.py` | 4 | 4 | 4 | 作业读取、提交、完成窗口和课程归属校验较完整。 |
| 作品/通知/档案 | `project_routes.py`、`teacher_routes.py`、`notification_service.py`、`portfolio_service.py` | 4 | 4 | 3 | 作品审核范围较好，但附件最终受通用文件接口影响。 |
| 管理员/公共课程 | `admin_routes.py`、`admin_public_course_routes.py`、`admin_public_course_service.py` | 4 | 3 | 3 | 管理接口基本有 admin 限制，教师导入上传校验薄弱。 |
| 公开学习/图文展示 | `public_learning_routes.py`、`showcase_routes.py`、`public_learning_service.py` | 4 | 3 | 3 | 公开课程筛 `is_public`，课时内容经后端清洗。 |
| 基础设施/迁移 | `main.py`、`config.py`、`schema_compat.py`、`migrations/*` | 3 | 2 | 3 | `create_all + schema_compat` 与 Alembic 并存，长期漂移风险高。 |

## 六、测试、构建、部署和文档质量

### 6.1 当前质量评价

| 区域 | 评分 | 说明 |
|---|---:|---|
| 前端构建 | 7/10 | 有 lockfile，`build` 包含 type-check；但静态测试没有统一入口。 |
| 后端测试 | 7/10 | 后端测试覆盖面较宽；但 fresh clone/CI 依赖 `SECRET_KEY` 配置。 |
| 部署配置 | 5/10 | 有 Nginx 和部署检查说明；上传目录、脚本版本化和运行时强校验不足。 |
| 文档同步 | 5/10 | 近期记录包含服务器部署影响；但存在已删除文档引用、乱码段和陈旧文件名。 |

### 6.2 主要问题

- `frontend/package.json:11-12` 只挂了 2 个专项测试脚本，`frontend/tests/` 下约 20 个 `.mjs` 静态测试没有统一 `test` 入口。
- `backend/tests/conftest.py` 导入后端配置时需要 `SECRET_KEY`，fresh clone 或 CI 未配置会失败。
- `backend/requirements.txt` 未固定版本，且 `moto` 测试依赖放在运行依赖中。
- `.gitignore:23` 忽略 `scripts/`，但 `backend/README.md` 要求运行 `scripts/create_admin.py`，存在部署不可复现风险。
- `backend/docs/项目修改记录.md` 存在历史乱码段；`docs/superpowers/project-map.md` 读取时也出现乱码显示，建议统一检查编码。
- `AGENTS.md` 当前引用多份已删除的计划/报告文档，说明文档同步链路不稳定。

## 七、建议修复顺序

### 7.1 第一优先级：立即修复 P0

1. 锁住 `/api/files/{file_id}`：新增鉴权、归属授权和公开文件白名单。
2. 禁止公开教师注册：前端移除教师选项，后端拒绝 `role=teacher`。
3. 修复教师密码重置授权：教师审批/驳回必须校验申请人属于当前教师班级。

### 7.2 第二优先级：补齐核心安全边界

1. 移除临时密码长期明文保存。
2. 统一本地文件路径边界校验。
3. 将教师批量删除学生改为“解除本教师班级关系”或改由管理员执行。
4. 外链 URL 前后端双重校验。
5. 统一文件预览授权方式，减少 query token 暴露。
6. 修正 Nginx alias 和 `LOCAL_UPLOAD_DIR` 文档/测试一致性。

### 7.3 第三优先级：提高稳定性和可维护性

1. 为前端静态测试增加统一入口。
2. 后端测试提供测试默认 `SECRET_KEY` 或测试专用配置加载方式。
3. 将导入类接口统一使用 `validate_upload`、大小限制和魔数校验。
4. 统一分页搜索语义，避免“只搜索当前页”。
5. 清理已删除文档引用和乱码文档。
6. 明确 Alembic 与 `schema_compat` 的职责边界，逐步减少运行时结构补丁。

## 八、建议验证清单

### 8.1 后端安全回归

```powershell
cd backend
py -m pytest tests/test_auth.py tests/test_material_file_acceleration.py tests/test_project_course_scope.py tests/test_public_learning.py tests/test_integration_bugfixes.py -q
py -m pytest tests/ -q
```

建议新增后再验证：

- 未登录访问 `/api/files/{id}` 必须失败。
- 非课程成员不能访问私有资料文件。
- 公开资料只能通过公开资料接口访问。
- 公开注册 `role=teacher` 必须失败。
- 教师不能审批/驳回非本班学生密码重置申请。
- `object_key="../x"` 在通用文件访问和预览生成中均拒绝。
- 教师批量删除学生不能删除其他教师班级数据。
- 管理员教师导入接口拒绝超大文件和伪 `.xlsx`。

### 8.2 前端构建与静态测试

```powershell
cd frontend
npm run build
Get-ChildItem tests -Filter *.mjs | ForEach-Object { node $_.FullName }
```

建议新增或补充：

- 注册页不能出现教师注册选项。
- 资料预览不在 URL 中泄露 JWT。
- 教师/管理员访问学生端路由的边界符合预期。
- 管理员删除教师依赖判断包含作品和图文。
- 密码重置必须有确认弹窗并显示失败提示。
- 题库搜索和任务完成搜索不只过滤当前页。

### 8.3 部署验证

```powershell
cd backend
py scripts/check_deploy_env.py --skip-mysql --skip-s3
nginx -t -c /path/to/deploy/nginx.conf
```

部署前必须人工确认：

- `LOCAL_UPLOAD_DIR` 与 Nginx `/_protected_uploads/` alias 指向同一目录。
- 生产环境 `ALLOWED_ORIGINS` 不是 `*`。
- 生产 `DATABASE_URL` 不使用默认 `root:123456`。
- `SECRET_KEY` 已配置且足够长。
- 管理员初始化脚本已纳入版本管理或部署包。

## 九、覆盖说明

本次审查按文件类型覆盖：

- 前端页面：`frontend/src/views` 下学生端、教师端、管理员端、内容查看器均已纳入页面或组件评分。
- 前端组件：`frontend/src/components/common`、`frontend/src/components/home`、`frontend/src/components/lesson` 已按公共渲染、资料预览和课时阅读重点抽查。
- 前端 API 与状态：`frontend/src/api`、`frontend/src/stores/auth.ts`、`frontend/src/composables`、`frontend/src/utils` 已按鉴权、文件 URL、上传、练习和课程数据流抽查。
- 后端路由：`backend/app/api/v1/routes/*.py` 全部纳入路由级审查。
- 后端服务：`backend/app/services/*.py` 全部纳入服务级审查。
- 后端基础设施：`backend/app/core`、`backend/app/db`、`backend/app/models/entities.py`、`backend/app/schemas/common.py`、`backend/migrations` 已纳入安全和稳定性审查。
- 测试与部署：`backend/tests`、`frontend/tests`、`deploy`、`frontend/package.json`、`backend/requirements.txt`、README 和 `docs/superpowers` 已纳入覆盖质量审查。

没有逐行执行每一个测试断言，也没有启动浏览器做真实页面视觉验收；本报告是源码级和配置级审查。运行期上传文件、缓存、构建产物和虚拟环境不属于项目源码，不纳入覆盖。

## 十、服务器部署影响

本次工作只新增审查报告文档，不修改业务代码、不修改接口、不修改数据库结构、不修改前端构建产物。

服务器当前不需要拉代码、重启服务、重新构建前端、执行数据库迁移、调整环境变量或修改 Nginx 配置。

但如果后续按本文修复 P0/P1，预计会涉及：

- 后端代码更新和服务重启。
- 前端代码更新和重新构建部署。
- 可能需要调整 Nginx `/uploads` 与 `/_protected_uploads/` 配置。
- 可能需要新增或变更文件授权字段、迁移历史文件归属数据。
- 可能需要清理历史明文临时密码字段或停止返回该字段。
