# 项目地图

## 当前架构

- 前端：`frontend/`，Vue 3 + TypeScript + Vite + Element Plus
- 后端：`backend/`，FastAPI + SQLAlchemy
- 部署：`deploy/nginx.conf` 负责生产 Nginx 示例，代理 `/api/` 和 `/uploads/` 到后端；`deploy/redeploy-server.ps1` 固化单机代码发布、前端构建同步和后端健康检查流程
- 存储：第一阶段默认本地上传目录，后续再接入 S3 / SeaweedFS / MinIO
- 测试：`backend/tests/`，以 SQLite 内存库为主

## 核心业务结构

```text
User(teacher) -> Course -> Class -> StudentClassEnrollment -> User(student)
User(teacher) -> Course -> CourseStage -> Material
User(teacher) -> Course -> Question -> QuizAttempt
User(teacher) -> Course -> Project
Announcement -> AnnouncementClass -> Class
Announcement -> QuizAttempt(announcement_id) -> TaskCompletion
# 历史保留（产品与 API 已下线，表/ORM/迁移仍在）：
# Lesson / LessonProgress / CourseProgress
```

## 后端主要文件

- ORM：`backend/app/models/entities.py`
- Schema：`backend/app/schemas/common.py`
- 兼容层：`backend/app/db/schema_compat.py`
- 班级服务：`backend/app/services/class_service.py`
- 资料服务：`backend/app/services/material_service.py`
- 资料预览服务：`backend/app/services/material_preview_service.py`
- 公开学习服务：`backend/app/services/public_learning_service.py`
- 题库服务：`backend/app/services/question_service.py`
- 公共课程题库贡献记录：`backend/app/services/question_contribution_service.py`
- 公告服务：`backend/app/services/announcement_service.py`
- 任务服务：`backend/app/services/task_service.py`
- 教师统计/成绩/作品审核：`backend/app/services/teacher_service.py`

## 教师端页面

- `/teacher`
- `/teacher/courses`（课程列表：添加/新建/切换课程；详情页「返回课程管理」进入）
- `/teacher/courses/:courseId`（管理课程详情：课程信息 + 阶段与资料管理；无课时/学习分析；教师维护课程资料的唯一入口；左侧导航「管理课程」默认直达此页）
- `/teacher/classes`
- `/teacher/publish`
- `/teacher/grades`
- `/teacher/task-report`
- `/teacher/reviews`
- `/teacher/student-admin`
- `/teacher/questions`

## 学生端页面

- `/learn`（公开教程卡片；只展示资料数，进入课程资料）
- `/learn/course/:courseId`（资料直读唯一主路径；旧 `lesson_id`/`tab=lessons` 查询参数忽略）
- `/practice`
- `/practice/quiz/:courseId`
- `/practice/announcement/:announcementId`
- `/inbox`

## 长期约定

- 不再使用独立章节表、章节 API 或章节页面
- **课程「课时」产品与 API 已全链路下线（2026-07-16）**：前端无课时 CRUD/阅读/进度；后端课时与课时进度路由返回 HTTP 404 且不在 OpenAPI 中；公开课程响应不再返回 `lesson_count`
- **历史数据只读保留**：`lessons`、`lesson_progress`、`course_progress` 表、ORM、`schema_compat` 兼容建表与历史迁移文件仍保留；本轮不做 DROP/清表/迁移
- 课程学习统一围绕阶段化资料（PDF、视频、链接）与 `MaterialInlineReader` 直读；不新增资料级进度/完成率
- 资料、题目和作品都直接挂在课程下（资料可归入 `CourseStage`）
- 答题统计以 `QuizAttempt` 为事实来源
- 新上传文件统一通过 `file_id` 访问 `/api/files/{id}`
- 生产环境预览 PDF / 视频优先走 Nginx 代理
- 第一阶段部署不要求 S3 端点存在
- 班级必须归属一门课程
- 发布作业可以一次选择同一课程下的多个班级
- 作业练习必须通过 `QuizAttempt.announcement_id` 记录作业维度
- 作业只有在全部配置题目都已有答题记录后才创建 `TaskCompletion`；答题、评分和完成记录在同一事务中提交
- 所有密码写入路径必须递增 `User.token_version`；登录态改密返回替换 Token，前端先保存新 Token 再继续密保或导航
- 密码修改、密保重置、教师/管理员审批重置和管理员直接重置必须写入审计日志；软删除用户不能登录或复用旧 Token
- 学生提交作品必须选择自己已加入班级对应的课程
- 教师只能访问自己创建的课程及其下属班级、资料、学生成绩和作品审核范围；共享题目的编辑权依据 `Question.created_by`
- 教师可以删除自己课程下的资料，包括公共课程同步到教师课程副本里的资料，但不会影响公共课程源
- 教师可以新增和编辑自己创建的题目，但不能删除题目；题目删除仅由管理员执行
- 公共课程的题库为全站共享题库，不再复制题目到教师课程副本；教师和管理员新增或导入题目会写入 `created_by` 并记录贡献日志
- 删除教师课程或公共课程时不转挂、不软删、不隐藏共享题目；活跃共享题库只看 `Question.deleted_at`，课程仅是挂载上下文
- 公共课程题库的新增与导入会记录到 `question_contribution_logs`，保存课程快照、操作人、动作类型、题目数量和时间
- 课程正式 API 统一使用 `/api/courses*`；历史 `/api/questions/courses*` 兼容入口已删除。
- 课程搜索使用 `ilike()`（大小写不敏感 + 中文子串），不再使用 `contains()`。
- 教师课程页“已添加课程”和“公共课程”均通过 `/api/courses` 分页接口携带关键词搜索。
- 教师学生列表分页直接在数据库层完成，不再全量查询到 Python 内存去重再切片。
- 回归保护：`frontend/tests/course-detail-layout-static.test.mjs`、`frontend/tests/material-only-learning-static.test.mjs`、`backend/tests/test_removed_lesson_endpoints.py` 锁定资料唯一学习主路径与课时 API 退役契约。
- 课程资料大文件打开优先走 `/api/materials/{material_id}/file`，后端鉴权后由 Nginx 内部目录传输
- 学生端和教师端资料展示统一使用图文资料卡片和站内预览；旧 `/api/files/{id}` 保留给图片、作品报告等通用文件访问
- ~~学生端“学”页面课时内容只能展示学生已加入课程下的已发布课时~~（已被 2026-07-16 课时下线决策取代）
- ~~课时富文本白名单清洗 / 删除课时时清理进度引用~~（已被 2026-07-16 课时下线决策取代；历史表仍保留）

## 修改记录

### 2026-07-16 移除课程「课时」产品与 API

- 决策：产品界面、前端调用和后端公开接口全链路下线「课时」及课时级学习进度；学习统一围绕阶段化资料直读。
- 后端：注销 `lessons`/`progress` 路由与服务；公开学习删除 `list_public_lessons` 与 `lesson_count`；删除课时/进度 Schema 与专用测试；新增 `test_removed_lesson_endpoints.py` 锁定 HTTP 404 与 OpenAPI 缺席。
- 前端：删除 `api/lesson.ts`、`api/progress.ts` 与 `components/lesson/*`；`LearnView`/`CourseDetailView` 仅资料路径；教师课程详情去掉课时与学习分析；卸载 `@wangeditor` 与专用分包。
- 保留：`Lesson`/`LessonProgress`/`CourseProgress` ORM、`schema_compat` 兼容建表、历史迁移文件；不清空历史行。
- 实施计划：`docs/superpowers/plans/2026-07-16-remove-course-lessons.md`
- 服务器部署影响：需要拉代码、前端 `npm ci` 后重新构建部署、重启后端；**不需要**数据库迁移/清表；不需要改 Nginx/Redis/环境变量。

### 2026-07-09 课程课时级进度追踪第一版

> **状态标注（2026-07-16）：** 下列“课时进度产品能力”已被本文件上方「移除课程课时」决策取代。历史表与 ORM 仍保留，产品与 API 已下线。

- 数据：新增 `lesson_progress` 课时进度表与 `LessonProgress` ORM，记录状态、完成百分比、断点位置、累计学习时长、访问次数和关键时间戳；`schema_compat.py` 会在旧库启动时补表。
- 接口：`progress_service.py` 新增课时进度上报、课程进度汇总、班级学生进度、课程学习统计；`/api/courses/{course_id}/progress` 保留 `last_lesson_id` 并增加 `total_lessons`、`completed_lessons`、`total_duration`、`completion_rate`、`lessons`。
- 前端：`CourseDetailView.vue` 对已登录学生的鉴权课程启用 30 秒心跳、页面隐藏/卸载前补报、视频断点采集与恢复；`LearnView.vue` 优先展示后端完成率。
- 回归保护：`backend/tests/test_lessons_progress.py` 覆盖课时进度累加与自动完成、课程进度明细、教师查看班级学生进度、课程学习统计。
- 服务器部署影响：需要备份数据库、拉取代码、重启后端以补建 `lesson_progress` 表，并重新构建部署前端静态资源；不需要修改环境变量或 Nginx 配置。


### 2026-07-08 本地 PDF 浏览器展示修复

- 问题：本地生产预览中，资料弹窗和课程资料直读器把受保护的 `/api/files/{file_id}` 或 `/api/materials/{id}/file` 地址直接交给 `<object>`、`video`、PDF.js 或新窗口。浏览器内嵌标签无法携带 `Authorization` 请求头，而当前后端未开启 query token，导致 PDF 预览拿到 JSON 401；旧的 `/api/materials/{id}/file` 还依赖 Nginx `X-Accel-Redirect`，不适合本地直连 FastAPI 预览。
- 修复：新增 `frontend/src/composables/useAuthenticatedFileUrl.ts`，统一用 `fetch` 携带 `auth_token` 读取 `/api/` 文件流，再通过 `URL.createObjectURL()` 生成 `blob:` 地址供 `<object>`、`video`、PDF.js 和“在新窗口打开”使用；`MaterialPreviewDialog.vue` 优先用 `material.file_id` 走 `/api/files/{file_id}`，`MaterialInlineReader.vue` 改为用 `blobUrl` 渲染 PDF/视频。
- 学习页补充：`CourseDetailView.vue` 在用户已登录且资料有 `file_id` 时优先返回 `/api/files/{file_id}`，让直读器能走带认证文件流；未登录公开资料仍保留公开资料专用 URL 降级路径。
- 回归保护：更新 `frontend/tests/material-preview-static.test.mjs`、`frontend/tests/public-learning-static.test.mjs`，要求资料弹窗和直读器必须使用 `useAuthenticatedFileUrl` 与 `blobUrl`，防止再次把受保护文件地址直接塞给浏览器内嵌标签。
- 验证：执行 `node frontend/tests/material-preview-static.test.mjs`、`node frontend/tests/public-learning-static.test.mjs`、`node frontend/tests/local-file-preview-static.test.mjs`、`npm run build`；并用本地 Playwright 验证教师端资料页选择“Python 基础讲义”后，浏览器请求 `/api/files/*` 返回 `application/pdf`，预览 `<object>` 的 `data` 为 `blob:`。
- 服务器部署影响：本次按用户要求不写入服务器，只在本地生产环境测试；真正上线时需要服务器拉取前端代码并重新构建、部署前端静态资源；不需要后端重启，不需要数据库迁移，不需要修改环境变量或 Nginx 配置。

### 2026-07-07 课程资料页直读式文档站落地

- 问题：学习资料页此前虽然有三栏，但中间仍是资料卡片流，PDF/视频需要点“预览”进入弹窗，不符合古月居图书资源、Material for MkDocs、Docusaurus、VitePress 这类学习文档站的直读体验。
- 修复：`/learn/course/:courseId?tab=materials` 改为文档站式直读结构，左侧按阶段列出资料目录，中间使用 `MaterialInlineReader` 直接阅读当前 PDF、视频或链接资料，右侧只展示当前资料导读、原资料入口和上一份/下一份资料。
- PDF 直读：`MaterialInlineReader.vue` 使用 `vue-pdf-embed` essential 入口并显式配置 PDF.js worker；默认优先选择更适合学习的长 PDF，首屏先渲染前 2 页并提供“加载更多页面”，避免长 PDF 首次打开长时间停在加载状态；异常 PDF 保留中文失败提示和“打开原资料”降级入口。
- 实时刷新：资料页保留轻量轮询能力，当前资料存在 `pending` / `processing` 预览状态时定时刷新，页面重新可见时立即刷新；不引入 WebSocket，不改变后端接口。
- 保留边界：不修改后端接口、数据库结构、资料上传流程、教师端资料管理或管理员公共课程资料管理；`MaterialPreviewDialog` 继续保留给课程正文和管理场景备用。
- 验证：执行 `node .\tests\public-learning-static.test.mjs`、`npm run type-check`、`npm run build`；用 Playwright 在本地生产数据上验证桌面端和移动端资料页，确认中间区存在 PDF canvas、资料 tab 主流程不再出现 `MaterialRichCard`、视频和链接可在中间区直接切换、移动端无横向溢出。截图保存在 `output/webtest/inline-reader/course-materials-inline-desktop.png`、`output/webtest/inline-reader/course-materials-inline-mobile.png`、`output/webtest/inline-reader/course-materials-inline-mobile-reader.png`。
- 服务器部署影响：本次为前端页面改造；上线需要服务器拉取前端代码、重新构建并部署前端静态资源；不需要后端重启，不需要数据库迁移，不需要修改环境变量或 Nginx 配置。

### 2026-07-07 课程资料页直读式文档站实施计划

- 背景：在 2026-07-06 完成资料页直读式文档站调研后，继续把方案拆成可执行实施计划，便于后续正式编码时逐项验收。
- 计划：新增 `docs/superpowers/plans/2026-07-07-course-materials-inline-reader.md`，覆盖静态回归测试、`MaterialInlineReader` 组件、`CourseDetailView.vue` 资料 tab 直读改造、桌面/移动端 Playwright 截图验收、资料预览状态轻量实时刷新和最终文档记录。
- 范围：计划明确第一阶段只改前端资料展示，不改后端接口、数据库结构、上传流程、教师端资料管理或管理员公共课程资料管理；`MaterialPreviewDialog` 继续保留给课程正文和管理场景备用。
- 服务器部署影响：本次仅新增实施计划和修改记录，不影响服务器；不需要服务器拉代码、重启服务、重新构建前端、数据库迁移、环境变量修改或 Nginx 配置调整。若后续按计划改正式前端页面，上线时需要重新构建并部署前端静态资源。

### 2026-07-06 课程资料页直读式文档站调研

- 背景：用户希望学习资料页接近 `https://book.guyuehome.com/` 这类学习文档站，而不是资料卡片列表、预览按钮和弹窗式 PDF 查看，并要求先拓展调研同类学习网站。
- 调研：新增 `docs/superpowers/specs/2026-07-06-course-materials-inline-reader-research-design.md`，对比古月居图书资源、Material for MkDocs、Docusaurus、VitePress、GitBook、Mintlify、Nextra 的导航和阅读结构。
- 现状判断：当前 `/learn/course/:courseId?tab=materials` 虽已有左目录、中资料流、右索引的三栏，但中间仍是 `MaterialRichCard` 卡片流，点击后进入 `MaterialPreviewDialog`，PDF/视频不作为页面主阅读对象。
- 推荐方向：资料页后续应改为“课程资料直读器”，左侧阶段化资料目录负责切换资料，中间直接嵌入当前 PDF/视频/链接阅读框，右侧只展示当前资料导读和相邻资料；资料预览弹窗降级为备用路径。
- 服务器部署影响：本次仅新增调研设计文档和修改记录，不影响服务器；不需要服务器拉代码、重启服务、重新构建前端、数据库迁移、环境变量修改或 Nginx 配置调整。若后续按方案改正式前端页面，上线时需要重新构建并部署前端静态资源。

### 2026-07-06 对抗式真实网页三轮测试与移动端整改

- 测试范围：在当前分支本地生产环境完成三轮真实网页测试，覆盖游客、学生、教师、管理员四类身份；逐页截图检查排版、按钮色彩、弹窗、Toast、空状态和文件预览链路。最终报告目录为 `output/webtest/screenshots/2026-07-06T14-16-31-411Z/`，本轮共生成 77 张截图、记录 47 次真实 API 操作，最终 `pageIssues=0`、`layoutIssues=0`。
- 真实学习资料：本轮测试不使用空白或占位文件，生成并上传符合 AI 通识教育主题的长内容资料，包括 `ai-literacy-learning-handbook.pdf`（12 页）、`student-ai-project-report.pdf`（8 页）、`public-ai-literacy-reading-pack.pdf`（10 页），并配套生成 AI 通识课程封面、读书会图解、学生项目封面和流程图图片，用于浏览器端上传、打开和截图验证。
- 本地生产数据：教师端课程资料、管理员公共课程资料、学生作品、Excel 导入数据、管理员端公益活动和读书会图文混排内容均已真实写入本地生产环境 SQLite 数据库 `output/webtest/webtest.sqlite`；管理员端公众号/图文信息已覆盖列表、发布、前台活动页和详情页真实查看流程。
- 发现并整改：修复畸形 `auth_user` 本地缓存导致登录态解析异常；修复学生成长档案雷达图 ECharts 坐标轴可读性 warning；修复 390px 窄屏下教师端资料页、管理员公共课程页、管理员图文管理页横向溢出问题，涉及 `PortfolioView.vue`、`TeacherLayout.vue`、`TeacherMaterials.vue`、`AdminLayout.vue`、`AdminPublicCourses.vue`、`AdminShowcase.vue`。
- 回归保护：新增 `frontend/tests/auth-storage-static.test.mjs`、`frontend/tests/vue-console-warning-static.test.mjs`、`frontend/tests/frontend-typography-static.test.mjs`、`frontend/tests/mobile-admin-layout-static.test.mjs`，并保留 `output/webtest/adversarial-webtest.mjs`、`output/webtest/regression-layout-check.mjs` 作为本地网页真机流程复测脚本。
- 验证：已执行 `node .\frontend\tests\auth-storage-static.test.mjs`、`node .\frontend\tests\vue-console-warning-static.test.mjs`、`node .\frontend\tests\frontend-typography-static.test.mjs`、`node .\frontend\tests\mobile-admin-layout-static.test.mjs`、`node .\output\webtest\regression-layout-check.mjs`、`node .\output\webtest\adversarial-webtest.mjs`、`npm run type-check`、`npm run build`、`git diff --check`。`npm run build` 仅保留 Vite 对现有大 chunk 的体积提示。
- 服务器部署影响：本轮真实测试数据只保存在本地生产环境，不同步服务器数据库；若上线本分支的前端整改，需要服务器拉取前端代码、重新构建并部署前端静态资源；不需要后端重启、不需要数据库迁移、不需要调整环境变量或 Nginx 配置。

### 2026-07-06 教师端页面 UI 回退

- 背景：本轮教师端产品 UI 大改后的页面观感和排版不符合验收预期，用户要求将教师端页面退回。
- 回退：`frontend/src/views/teacher/` 下教师端页面恢复到本轮 UI 大改前状态，并删除教师端重设计专用计划 `docs/superpowers/plans/2026-07-05-teacher-ui-redesign.md` 和静态测试 `frontend/tests/teacher-ui-redesign-static.test.mjs`。
- 保留：继续保留非教师端的全局排版底座、首页/公开页/学生端文字排版优化，以及 `App.vue`、`main.ts`、`AdminPublicCourses.vue` 的本地 warning 收口；不修改后端接口、数据库结构、权限边界、路由语义或服务器配置。
- 回归保护：`frontend/tests/frontend-typography-static.test.mjs` 调整为只覆盖全局排版、首页/公开页和学生端文字排版，不再强制教师端新版 UI 结构；教师端仍保留既有工作台隔离和课程搜索静态测试。
- 验证：本次只在本地生产环境验证，不写入服务器、不部署服务器。
- 服务器部署影响：本次按用户要求不写入服务器；真正上线时若保留本分支其他前端改动，需要服务器拉取前端代码并重新构建、部署前端静态资源；不需要后端重启，不需要数据库迁移，不需要修改环境变量或 Nginx 配置。

### 2026-07-06 全站前端 UI 与文字排版优化

- 问题：首页、公开/认证页和学生端任务页存在标题字体语气不统一、局部宋体大字距残留、中文长句断行不稳、数字排版缺少等宽约束等问题。
- 优化：`frontend/src/assets/main.css` 增加固定排版 token、标题/正文断行保护和等宽数字工具类；首页公共外壳、首页模块、公开活动/关于/联系/隐私/登录注册/修改密码/404 页面、学生端学习/答题/练习/作品/个人/消息页面统一标题层级、说明文字行高和正文行宽。
- 稳定性：`App.vue` 页面切换动画包裹单一真实 DOM 节点，`main.ts` 显式注册 Element Plus 单选组别名，管理员公共课程资料阶段选择和题型标签避免传入 Element Plus 会产生 warning 的 `null` value 或空字符串 tag type。
- 细节收口：学生消息未读卡片移除 3px 侧边色条，改为完整边框、浅底和点状状态提示。
- 保留：不修改后端接口、数据库结构、权限边界、路由语义、课程/作业/资料/作品业务逻辑，不新增 UI 框架、状态管理方案或服务器配置；教师端页面已按反馈回退，不纳入本条 UI 优化结果。
- 回归保护：新增 `frontend/tests/frontend-typography-static.test.mjs` 和 `frontend/tests/vue-console-warning-static.test.mjs`，覆盖全局排版 token、`text-wrap` 断行保护、`tabular-nums` 工具类、学生端任务页与答题页标题去大字距、公开/认证页标题回归 sans 口径、学习页长说明断行保护、学生消息粗侧边色条和纯白文字色残留，以及 Vue Transition / Element Plus warning 易回归点。
- 验证：本轮按本地生产环境流程执行前端静态测试子集、`npm run build`、本地网页交互检查和 `git diff --check`；服务器不写入、不部署。
- 服务器部署影响：本次按用户要求不写入服务器，只在本地生产环境测试；真正上线时需要服务器拉取前端代码并重新构建、部署前端静态资源；不需要后端重启，不需要数据库迁移，不需要修改环境变量或 Nginx 配置。

### 2026-07-04 前端长文案一致性修复

- 问题：前端长文案存在术语和业务口径不一致，教师端混用“发布题目/作业任务”，教师工作台把累计练习次数写成“本周练习”，公开端残留“写死旧模块”等内部迁移说明，管理端密码重置驳回原因填写后未传给接口；第二轮审计又发现共享题库仍被描述为同步到教师副本、首页入口仍写“学习页/任务”、学生消息和作品 PDF 入口存在旧口径。
- 修复：统一教师端“作业/题目/课程资料/公共课程源/课程副本”文案；学生和公开端统一“公开学习馆/学习资料/作业练习”文案；首页移除旧六模块课程预览入口并恢复四入口与今日建议；管理端驳回密码重置申请时传递驳回原因；公共课程删除确认补充同步资料影响范围，并将题库文案改为全站共享题库口径；通用资料组件和作品 PDF 链接统一“资料预览”和“在新窗口打开”。
- 回归保护：新增并扩展 `frontend/tests/copy-consistency-static.test.mjs`，覆盖统计口径、登录边界、内部说明泄露、共享题库口径、首页入口长文案、资料预览术语和未知校验错误兜底；同步更新公开学习、资料预览和首页相关静态测试断言。
- 验证：执行 `node ./tests/copy-consistency-static.test.mjs`、`node ./tests/public-learning-static.test.mjs`、`node ./tests/local-file-preview-static.test.mjs`、`node ./tests/material-preview-static.test.mjs`、`node ./tests/home-first-stage-static.test.mjs`、`node ./tests/home-course-preview-removal-static.test.mjs`、`node ./tests/practice-quiz-flow-static.test.mjs`。
- 服务器部署影响：需要服务器拉取前端代码并重新构建、部署前端静态资源；不需要后端重启，不需要数据库迁移，不需要修改环境变量或 Nginx 配置。

### 2026-07-04 前端 Chunk 体积第一阶段优化

- 问题：前端生产构建存在大 chunk，入口包、教师课程详情页和成长档案页分别承担了全量图标、富文本编辑器和图表库等当前页面不一定需要的成本。
- 优化：`TeacherCourseDetail.vue` 将 `LessonEditor` 改为异步组件；`PortfolioView.vue` 将 ECharts 隔离到 `PortfolioRadarChart.vue` 并异步加载；`main.ts` 将 Element Plus 图标从全量注册改为只注册当前使用的 `Loading`。
- 保留：不改变上传流程、资料预览接口、课程详情业务逻辑、成长档案接口和 Element Plus 组件使用方式；本阶段只移动重依赖加载时机，不做 UI 行为重构。
- 回归保护：新增 `frontend/tests/chunk-optimization-static.test.mjs`，静态检查富文本编辑器、ECharts 和 Element Plus 图标注册不会重新回到入口或页面主 chunk。
- 构建体积：入口 JS 从约 1,211.29 kB 降至约 1,063.84 kB；教师课程详情主 chunk 从约 819.64 kB 降至约 17.65 kB；成长档案主 chunk 从约 465.81 kB 降至约 5.22 kB；富文本编辑器和图表库被拆为异步 chunk。
- 服务器部署影响：需要服务器拉取前端代码并重新构建、部署前端静态资源；不需要后端重启，不需要数据库迁移，不需要修改环境变量或 Nginx 配置。

### 2026-07-04 前端 Chunk 体积第二阶段优化

- 问题：第一阶段后入口主文件仍承担全局 Element Plus、Vue 基础依赖和 HTTP 基础依赖；教师课时编辑器虽然已异步加载，但业务壳仍与 wangEditor 第三方库混在同一个大 chunk。
- 优化：`vite.config.ts` 使用 Vite 8 / Rolldown `codeSplitting.groups`，将 Vue/Pinia/Router、Element Plus、Axios 和 wangEditor 分别拆为命名 vendor chunk；避免使用宽泛 `node_modules` 总包，防止异步重依赖重新进入首屏。
- 优化：`main.ts` 移除 `app.use(ElementPlus)` 全量 JS 注册，改为按当前项目实际使用的 Element Plus 组件白名单注册；继续保留 `element-plus/dist/index.css` 全局样式、中文 locale、`v-loading` 指令和 `Loading` 图标注册。
- 回归保护：新增 `frontend/tests/vendor-chunk-splitting-static.test.mjs`、`frontend/tests/element-plus-whitelist-static.test.mjs`、`frontend/tests/editor-vendor-splitting-static.test.mjs`，分别防止 vendor 分包退化、Element Plus 全量注册回归和 wangEditor 重新混入业务 chunk。
- 构建体积：完整构建通过后，入口业务 JS 约 26.60 kB（gzip 8.91 kB）；`TeacherCourseDetail` 主 chunk 约 18.10 kB；`LessonEditor` 业务壳约 2.29 kB，wangEditor 第三方依赖独立为按需 `vendor-wangeditor`；`vendor-element-plus` JS 从第二阶段分包时约 885.50 kB 降至约 495.19 kB。
- 边界：Vite 仍提示 `vendor-wangeditor` 超过 500 kB，这是 wangEditor 发布的 ESM 聚合包本身体积导致；它已经是课时编辑弹窗按需加载，不再影响首页、学习页、课程详情页和教师课程详情主页面首屏。尝试 `maxSize` 二次拆分后仍会留下约 796 kB 大块且增加请求，因此未保留该配置。
- 服务器部署影响：需要服务器拉取前端代码并重新构建、部署前端静态资源；不需要后端重启，不需要数据库迁移，不需要修改环境变量或 Nginx 配置。

### 2026-07-03 游客行页面开放与答题流程简化

- 行页面：`/act` 和 `/act/showcase/:id` 标记为公开路由，游客可以浏览公益课、读书会和行动图文详情；过期登录态会先清除再按游客身份访问公开路由；教师端学生业务路径拦截仍早于公开路由放行，教师访问 `/act` 继续回到 `/teacher`。
- 作品边界：`ActView.vue` 仅在已登录用户状态下调用作品列表接口；游客不会触发 `/api/projects`，落地项目区域显示“登录后查看同学们的实践成果”和去登录按钮。作品列表、作品详情、点赞、上传仍保持登录后访问。
- 答题流程：`PracticeQuizView.vue` 提交答案后先记录结果；答对非最后一题直接进入下一题，答对最后一题进入总结或完成作业；答错停留当前题展示正确答案和解析，再由学生继续。
- 回归保护：新增 `frontend/tests/act-guest-access-static.test.mjs` 和 `frontend/tests/practice-quiz-flow-static.test.mjs`，覆盖游客行页面公开化、游客不请求作品接口、教师拦截顺序、正确题不展示解析和错误题保留解析。
- 服务器部署影响：需要服务器拉取前端代码并重新构建、部署前端静态资源；不需要后端重启，不需要数据库迁移，不需要修改环境变量或 Nginx 配置。

### 2026-07-03 学生端个人任务色彩重设

- 背景：用户反馈个人任务组件颜色不够美观，需要在不改业务功能的前提下重做色彩表现。
- 修复：`PracticeAssignments.vue` 新增任务页专用 OKLCH 色彩变量，重设作业任务页的浅宣纸底、筛选条、表格头部、状态标签和“去练习”按钮颜色；未完成、已完成、已过期分别改为暖黄、墨绿和藕红，避免继续使用默认红黄绿状态色。
- 保留：作业列表接口、课程筛选、状态筛选、作业名称搜索、排序、进入练习逻辑均不改变；后端、数据库、教师端和管理员端均不调整。
- 回归保护：新增 `frontend/tests/practice-assignments-color-static.test.mjs`，覆盖任务页颜色变量、OKLCH 色彩定义、三个状态标签色和旧默认状态色移除。
- 服务器部署影响：需要服务器拉取前端代码并重新构建、部署前端静态资源；不需要后端重启，不需要数据库迁移，不需要修改环境变量或 Nginx 配置。

### 2026-07-03 学习馆水墨书脊抽书展开

- 背景：用户希望 `/learn` 不再像普通课程列表，而是像图书馆书架一样展示公开课程；点击课程时先像选书一样抽出并展开，再进入类似古月居书站的课程阅读页。
- 修复：`LearnView.vue` 大幅简化为“公开课程书架”主体验，删除旧学习路径卡片和最新资料条带；课程以竖向书脊形式横向排列，点击后在当前页展开为打开的水墨课程书，展示课程简介、课时数、资料数、进度和进入课程按钮。
- 视觉：主题从厚重木架改为暑期水墨风格，使用浅宣纸底、墨绿主色、青蓝水色和轻微墨晕背景，降低装饰密度并突出课程书脊；学习馆首屏不再强制放置独立网站图标块。
- 保留：公开课程接口、学生已加入课程合并、学习进度读取和课程详情跳转逻辑不改变；本次进一步移除顶部搜索/刷新工具条，让首屏只保留课程书架主体验；后端、数据库、教师端和管理员端均不调整。
- 回归保护：更新 `frontend/tests/public-learning-static.test.mjs`，覆盖选中课程状态、水墨主题变量、书脊轨道、竖排课程标题、展开课程书、移动端横向滚动、旧木质书架组件移除，以及搜索/刷新工具条不再回归。
- 服务器部署影响：需要服务器拉取前端代码并重新构建、部署前端静态资源；不需要后端重启，不需要数据库迁移，不需要修改环境变量或 Nginx 配置。

### 2026-07-03 课程资料页书站式展示

- 问题：用户指定 `/learn/course/2?tab=materials` 的文件展示需要效仿古月居书站，但现有“学习资料”页签仍是阶段标题加两列资料卡片；书站式三栏布局只覆盖课程目录/课时阅读页签。
- 修复：`CourseDetailView.vue` 的“学习资料”页签改为书站式三栏布局，左侧为资料目录，中间为按阶段组织的连续资料阅读流，右侧为资料类型统计、快速打开和学习提示。
- 保留：公开学习接口、资料预览弹窗、公开资料文件 URL、教师端和管理员端上传流程均不改变。
- 回归保护：更新 `frontend/tests/public-learning-static.test.mjs`，覆盖材料页签三栏结构、正常中文文案和目录跳转方法。
- 服务器部署影响：需要服务器拉取前端代码并重新构建、部署前端静态资源；不需要后端重启，不需要数据库迁移，不需要修改环境变量或 Nginx 配置。

### 2026-07-03 公开学习馆书站化展示补齐

- 背景：用户反馈“学”页面没有呈现此前确认的古月居书站式公开学习效果，需要把 `/learn` 和课程阅读页从普通课程列表补齐为公开学习馆体验。
- 学习馆：`/learn` 调整为“AI 通识公开学习馆”，增加学习路径、公开课程书架、书本卡片层级和最新资料条带，游客可直接浏览公开课程，登录学生继续保留已加入课程和进度信息。
- 课程阅读：`/learn/course/:courseId` 调整为书站式三栏阅读页，左侧课程目录、中间课时正文、右侧本课资源和学习提示；游客公开预览资料走公开资料文件接口。
- 类型边界：资料展示类型允许 `link`，但后台上传表单和课时正文占位仍仅处理视频/PDF；编辑或嵌入链接资料时给出中文提示，避免类型扩展破坏构建。
- 回归保护：更新 `frontend/tests/public-learning-static.test.mjs`，覆盖公开路由、书本卡片结构、三栏阅读布局、公开资料预览、链接资料类型边界和中文乱码检查。
- 服务器部署影响：需要服务器拉取前端代码并重新构建、部署前端静态资源；不需要后端重启，不需要数据库迁移，不需要调整环境变量或服务器配置。若服务器尚未部署 2026-07-02 的公开学习接口改动，则仍需同步部署该后端接口并重启后端服务。

### 2026-07-02 公开学习馆 P0 首页与游客访问

- 问题：平台原本偏学生、教师和管理员内部使用，游客无法访问 `/learn` 和课程阅读页；首页缺少"深度"表达，公开学习内容无法在服务器上稳定作为公众化学习入口展示。
- 修复：新增 `/api/public/learning/*` 公开只读接口，游客可读取公开课程、已发布课时、公开资料和公开资料文件预览；前端 `/learn` 和 `/learn/course/:courseId` 标记为公开路由，同时保留教师账号进入学生业务路径时跳转 `/teacher` 的边界。
- 首页：首屏明确展示"中国计量大学 · 深度 AI 通识学习平台"，主入口改为公开学习馆，游客可直接开始学习，登录学生继续保留进度能力。
- 学习馆：游客读取公开课程和最新资料；登录学生额外合并已加入课程并保存学习进度；课程详情页对公开课程使用公开接口，对已加入私有课程保留原鉴权接口。
- 回归保护：新增 `backend/tests/test_public_learning.py` 和 `frontend/tests/public-learning-static.test.mjs`，覆盖公开课程隔离、草稿课时过滤、公开资料文件预览、路由公开化、教师端拦截顺序和 Nginx history 路由刷新配置。
- 服务器部署影响：需要服务器拉取代码、重启后端服务、重新构建并部署前端静态资源；不需要数据库迁移，不需要修改环境变量；不需要新增 Nginx 配置，但公开资料预览依赖既有 `/_protected_uploads/` internal 配置，部署前需确认该配置仍存在并指向实际上传目录。

### 2026-07-01 公开学习馆静态 Demo

- 背景：当前最高优先级转为公众化 AI 通识学习平台展示，需先确认首页“深度”定位、学校露出、游客可浏览大部分公开学习内容，以及“学”页面向公开学习馆/书架资料馆演进的视觉方向。
- 新增：`docs/superpowers/demos/2026-07-01-public-learning-demo.html` 静态 HTML Demo，覆盖首页第一屏、P0 游客模式目标、AI 通识书架、书站式阅读预览、教师端/管理员端上传资料进入公开学习馆的逻辑，以及 P0/P1/P2 路线图。
- 设计边界：Demo 参考古月居书站的信息结构，但不复制技术栈、不迁移到 MkDocs；正式实现仍保持 Vue 3 + FastAPI，公开学习内容来自现有课程、课时和资料后台。
- 未改业务代码：本次只新增设计 Demo 和项目记录，未修改 `frontend/src`、`backend/app`、数据库结构、接口语义或权限逻辑。
- 服务器部署影响：Demo 文档本身不需要服务器修改；若要在服务器展示该 Demo，可作为静态文件发布。正式 P0 代码实现后预计需要服务器拉代码、重启后端、重新构建并部署前端静态资源；按当前计划不需要数据库迁移，不需要调整环境变量。

### 2026-06-30 教师端只显示教师工作台

- 问题：教师账号虽然登录后进入 `/teacher`，但仍可通过教师工作台 Logo、“返回学生端”按钮或直接访问 `/`、`/learn`、`/practice` 等学生端业务路径看到学生端页面；同时 `App.vue` 在教师端路由外层仍渲染学生端全局头部和底部。
- 修复：新增教师端学生业务路径拦截，教师访问 `/` 或 `/learn`、`/practice`、`/create`、`/act`、`/portfolio`、`/inbox` 及其子路径时统一回到 `/teacher`；未登录用户访问首页保持不变，管理员访问首页仍进入 `/admin`。
- 教师工作台：`/teacher` 和 `/admin` 下不再渲染学生端 `AppHeader` 和 `AppFooter`；教师工作台 Logo 改为指向 `/teacher`，移除“返回学生端”和“回到首页”入口，只保留“退出登录”按钮。
- 回归保护：新增 `frontend/tests/teacher-workbench-only-static.test.mjs`，静态检查教师端路由边界、工作台壳层隐藏学生端头部底部、教师布局不保留学生端入口或首页入口，并保留退出登录能力。
- 服务器部署影响：需要服务器拉取前端代码并重新构建、部署前端静态资源；不需要后端重启，不需要数据库迁移，不需要调整环境变量或服务器配置。

### 2026-06-30 学生端课程详情页布局遮挡修复

- 问题：`/learn/course/:courseId` 课程详情页桌面端左侧课程目录使用脱离文档流的固定定位，Hero 和正文没有进入同一套避让布局，导致左侧目录遮挡标题、返回按钮和部分正文；固定顶部导航也会压住页面首屏内容。
- 修复：课程详情页新增 `.course-shell` 整体布局容器和 `.course-main-panel` 右侧内容面板，桌面端课程目录改为参与文档流的 `sticky` 侧栏，Hero、加载态、课时正文和资料页统一放在右侧面板内；页面顶部统一通过 `--app-header-height` 为固定导航预留空间。
- 移动端：保留课程目录抽屉交互，侧栏在 900px 以下恢复 `fixed` 抽屉定位，默认收起到屏幕外，通过目录按钮展开，不影响移动端首屏内容阅读。
- 回归保护：新增 `frontend/tests/course-detail-layout-static.test.mjs`，静态检查桌面端侧栏不得使用 `fixed` 覆盖、主内容不得依赖固定 `margin-left` 避让、移动端目录仍为抽屉，以及页面必须为固定顶部导航预留空间。
- 服务器部署影响：需要服务器拉取前端代码并重新构建、部署前端静态资源；不需要后端重启，不需要数据库迁移，不需要调整环境变量或服务器配置。

### 2026-06-30 单字图标统一替换为网站图标

- 问题：教师端、管理员端、登录注册页、学生端学习/练习入口和关于页仍分散使用“师”“管”“探”“学”“思”“探/练/造/行”等单字图标，和当前网站 PNG 标识不一致。
- 修复：将上述第一类 SVG 单字图标和第二类页面单字图标统一替换为 `/cjlu-xuesijianxing-favicon-sharp-20260606-190113.png`，保留原有导航、Hero 和卡片布局尺寸；删除无引用的旧 `frontend/public/favicon.svg` 和 `frontend/public/favicon.ico`，浏览器图标继续由 `frontend/index.html` 指向新的 PNG 网站图标。
- 回归保护：新增 `frontend/tests/site-icon-replacement-static.test.mjs`，静态检查目标页面必须引用网站图标，防止这些位置重新出现旧单字图标结构，并确认旧 favicon 文件不再保留。
- 服务器部署影响：需要服务器拉取前端代码并重新构建、部署前端静态资源；不需要后端重启，不需要数据库迁移，不需要调整环境变量或服务器配置。

### 2026-07-09 课程进度追踪、软删除回收站、通知中心与审计日志扩展

- 课程进度追踪：新增 `lesson_progress` 表、课时进度上报接口、课程进度汇总、班级学生进度和课程学习分析；学生课程详情页接入心跳上报、最新断点保存/恢复、`pagehide` keepalive 补报和完成率展示；教师课程详情新增学习分析标签页，展示学生完成率、学习时长、课时热度和疑似刷课指标。
- 软删除机制：七类核心资源增加 `deleted_at/deleted_by`；课程删除进入回收站并级联班级、资料和公告，共享题目先转挂且不进入恢复批次；管理员端新增“数据回收站”页面和恢复/彻底删除接口。
- 通知系统扩展：系统通知支持分类、优先级、站内跳转链接、偏好设置、批量发送、分类/未读筛选和全部已读；教师只能向自己班级的学生发送，管理员可向任意未删除学生发送；学生端 `/inbox` 与 `/student/notifications` 统一为通知中心，`/student/settings/notifications` 可直接打开通知偏好；顶部通知铃铛提供最近通知下拉；兼容层幂等初始化默认模板，过期通知不会进入列表或未读数，作业截止提醒与过期已读通知清理服务可供外部定时器调用。
- 审计日志系统：新增 `audit_logs`、管理员审计日志页面和查询/导出接口；支持用户、动作、资源类型、资源 ID、状态、时间范围筛选；回收站可直接跳转到指定资源操作历史；导出操作会写入 `audit_log.export` 审计记录。
- 回归保护：新增/扩展 `backend/tests/test_lessons_progress.py`、`backend/tests/test_030405_management_systems.py`、`frontend/tests/teacher-course-analytics-static.test.mjs`、`frontend/tests/notification-center-static.test.mjs`、`frontend/tests/admin-audit-logs-static.test.mjs`。
- 验证：`backend\.venv\Scripts\python.exe -m pytest backend/tests/test_lessons_progress.py backend/tests/test_030405_management_systems.py -q` 通过（22 passed, 1 warning）；教师学习分析、通知中心和管理员审计日志静态检查通过；`frontend` 下 `npm run build` 通过。
- 服务器部署影响：需要服务器拉代码、重启后端、重新构建并部署前端静态资源；需要数据库兼容层补齐新增表、字段和默认通知模板；建议部署前备份数据库；如需自动发送作业截止提醒或清理过期通知，需额外配置定时任务或调度进程；不需要修改环境变量或 Nginx 配置。

### 2026-07-11 多角度代码审查阶段 B 修复

- 学生流程：随机点名改用班级学生接口并防止旧请求覆盖；作品广场继续要求登录，作品通知统一跳转 `/create/project/{id}`；通知中心恢复 15 秒轮询、重新可见刷新和跨组件刷新，偏好设置不参与轮询；页头通知必须先标记已读成功再跳转。
- 课时进度：`LessonProgressIn.visit_started` 显式区分真实进入与普通心跳；SQLite/MySQL 按方言使用原子 upsert，时长和访问次数由数据库表达式累加，完成状态和最高进度不回退；课程页仅在真实切课时增加访问次数，隐藏、`pagehide` 和卸载共用一次性 keepalive 补报。
- 课时完成：无视频课时向已登录学生显示“完成本课”，主动上报 100%；视频课时继续按播放位置计算，不把按钮隐藏作为防刷课手段。
- 课程分析：`GET /api/courses/{course_id}/analytics` 接受 `page/page_size`，学生明细返回 `{items,total,page,page_size}`；有效学生、学生汇总和课时汇总均由数据库聚合，教师端使用服务端分页，不再加载全部 `LessonProgress` ORM。
- 回归保护：新增并发首次上报、100 名学生 × 20 个课时规模、访问次数、非视频完成和分页静态契约；修正静态测试运行目录和已过期首页品牌断言。
- 验证：阶段 B 后端回归 `16 passed, 1 skipped, 1 warning`，跳过项为未配置 `TEST_MYSQL_URL` 的 MySQL 并发用例；全部前端静态测试通过；`npm run build --prefix frontend` 通过，仅保留既有大 chunk 警告。真实浏览器流程和 MySQL 实库仍需部署前验收。
- 服务器部署影响：需要服务器拉取代码、重启后端服务、重新构建并部署前端静态资源；本阶段不新增表或字段，不需要数据库迁移，不需要调整环境变量、Redis 或 Nginx 配置。

### 2026-07-12 阶段 C 文件鉴权与流式预览修复（Task 4 + Task 5）

- 前端新增 `AuthenticatedFileImage.vue` 通用组件和 `useAuthenticatedFileUrl.ts` 组合式函数，统一管理私有文件短时签名 URL 的获取、续签和取消。
- 迁移作品详情页封面/图片、教师审核报告预览、管理员 PDF 预览等剩余消费者到签名 URL 方案，杜绝普通登录 JWT 出现在 URL 中。
- 作品封面优先使用 `file_id/cover_file_id`，历史外链作回退；公开活动封面继续匿名直连。
- Task 5 使用临时 SQLite + local 存储验收全链路（真实 2.67MB MP4，ftyp 魔数通过）：签名 URL 获取、文件体下载、Range 206（含中段 Range）、无认证拒绝、URL 安全检查全部 26/26 PASS。
- 回归保护：新增 `protected-file-consumers-static.test.mjs`、`file-access-url-static.test.mjs`；既有 pytest 78 passed。
- 服务器部署影响：需要服务器拉代码、重启后端、重新构建前端；不需要数据库迁移或环境变量调整。真实 Nginx 文件体传输和 Range 需部署后验收。

### 2026-07-13 自由练习提交范围 + 软删除读路径过滤

- 问题：学生自由练习只要加入任意课程即可对全站任意 `question_id` 提交并拿回标准答案；课程/班级/资料/作业/公开学习等业务读路径未统一排除 `deleted_at`，与文件链软删过滤不一致。
- 修复：
  - `quiz_service.submit_answer`：活跃题目 + 私有课限本课选课、公共课题保留共享题库；作业路径继续校验任务与 `question_ids`
  - `access_control_service.student_can_access_course` 及资料/作业/公开学习/课程题目读路径统一过滤软删班课与资源
  - 学生拉题接口隐藏 `answer/explanation`，练习页用提交结果回填正确答案/解析
  - 统计与错题本可见范围与提交规则对齐
- 本轮不做：正式删除入口统一软删、上传上限、连接池、Redis
- 回归保护：新增 `backend/tests/test_quiz_submit_scope.py`、`backend/tests/test_soft_delete_read_filters.py`；扩展 `backend/tests/test_access_control_service.py`
- 验证：相关后端 pytest `33 passed`；`frontend/tests/practice-quiz-flow-static.test.mjs` 通过
- 实施记录：`docs/superpowers/plans/2026-07-13-quiz-scope-soft-delete-read-filters.md`
- 服务器部署影响：需要服务器拉代码、**重启后端**、**重新构建并部署前端**；**不需要**数据库迁移、调整 Nginx 或环境变量。

### 2026-07-14 「学」页教程站形态改造

- 背景：书架式 `/learn` 不符合「游客友好教程站」目标；资料目录阶段与资料同宽同色、行高过大；右侧当前资料 facts 冗余。
- 入口：`LearnView.vue` 去掉书脊/翻开书/页级统计/最新资料条，改为公开教程卡片网格；接通 `getPublicCourses(keyword)` 搜索与空结果；保留公开课 + 已加入课合并与进度「继续学习」。
- 课程页：`CourseDetailView.vue` 资料 Tab 阶段头单行紧凑可折叠、资料行缩进单行选中态；去掉右侧 `guide-facts`；文案改为公开教程阅读 / 教程目录 / 学习资料 / 返回教程列表。
- 路由标题：`/learn` meta 改为「学 · 公开教程」。
- 回归保护：更新 `frontend/tests/public-learning-static.test.mjs`、`copy-consistency-static.test.mjs`。
- 验证：`npm run build` 通过；上述静态测试通过。
- Demo / 计划：`docs/superpowers/demos/2026-07-14-learn-tutorial-site-demo.html`、`docs/superpowers/plans/2026-07-14-learn-tutorial-site-ui.md`
- 服务器部署影响：需要服务器拉代码并**重新构建、部署前端**；**不需要**后端重启、数据库迁移、改 Nginx 或环境变量。首页部分入口仍可能写「公开学习馆」，本轮未全站改首页文案。

### 2026-07-14 共享题库闭环：添加人 / 星级 / 编辑归属

- 问题：题库已是全站共享，但教师端仍显示基于 `source_question_id/is_synced` 的“公共/私有”标签，容易误解；列表也未完整展示添加人与星级，编辑归属曾误用课程创建人。
- 修复：
  - 列表接口补齐 `created_by`、`creator_name`、`star_rating`，`is_owner` 改为 `Question.created_by == 当前用户`
  - 教师端列表增加“添加人”“星级”，新增/编辑弹窗支持 1-5 星；移除误导性公共/私有标签
  - 编辑与 Excel 导入补齐 `stem_hash` 同题干拦截，并与手工新增一致写入默认星级
- 本轮不做：题目删除入口、评分/收藏审核流、数据库迁移、学生端答题改动
- 回归保护：扩展 `backend/tests/test_public_question_contribution.py`、`backend/tests/test_question_import_skip.py`；新增 `frontend/tests/teacher-question-bank-static.test.mjs`
- 实施计划：`docs/superpowers/plans/2026-07-14-shared-question-bank-closure.md`
- 服务器部署影响：需要服务器拉代码、**重启后端**、**重新构建并部署前端**；**不需要**数据库迁移、调整 Nginx 或环境变量。

### 2026-07-14 管理员共享题库一键/批量删除

- 问题：管理员题库页展示全站共享题，但单题删除仍要求 `question.course_id == 当前公共课`，跨课挂载题无法删；缺少批量/一键删除。
- 修复：
  - 单题删除改为共享题库语义，仅校验管理入口公共课存在
  - 新增 `POST /api/admin/public-courses/{course_id}/questions/batch-delete`
- 删除共享题目前检查作业引用；有引用时拒绝删除并保留答题记录与 `question_ids`，无引用时进入回收站
  - 管理端题库增加多选、删除选中、一键删除全部
- 回归保护：扩展 `backend/tests/test_public_question_contribution.py`；新增 `frontend/tests/admin-question-batch-delete-static.test.mjs`
- 服务器部署影响：需要服务器拉代码、**重启后端**、**重新构建并部署前端**；**不需要**数据库迁移、调整 Nginx 或环境变量。

### 2026-07-14 代码审查修复后的稳定事实

- 共享题库管理入口：管理员通过任一未软删除公共课程入口管理全站活跃共享题库；编辑教师贡献题时不要求题目原始课程等于入口课程；活跃共享题只要求题目自身未软删除。
- 共享题库去重：`question_bank_service.compute_stem_hash` 是教师端和管理员端新增、编辑、导入的统一规范化 SHA-256 题干哈希实现；同题干判断覆盖全部活跃题目（不因挂载课程软删而排除），兼容初始化会回填历史空值、MD5 和异常长度哈希。
- 正式删除入口：班级、作业、资料、作品、教师账号、公共课程、公共资料和共享题目均保留主记录及必要关联，写入 `deleted_at/deleted_by`；普通读取、统计和文件授权排除软删除资源，回收站恢复和最终清理是专用入口。
- 管理端软删除边界：公共课程、公共资料、共享题目及题库计数/指纹/重复查询的正常入口排除软删除题目；课程软删除不得让共享题目从题库、查重或管理入口消失。
- 展示文件权限：已发布展示项的封面、图库、内容块图片可匿名访问；未发布展示项仅创建者管理员或教师可预览，普通用户和非创建者按不存在处理。
- 展示内容块图片授权扫描只读取必要列并使用 `yield_per(100)` 分批迭代，不再 `.all()` 一次加载全表内容块 JSON。
- Nginx `.mjs` 规则只匹配 `/assets/` 下构建产物；正式部署需同步配置并执行 `nginx -t` 后 reload。
- 部署安全门禁：`redeploy-server.ps1` 先检查脏工作区，以一次无交互 `git fetch` 锁定提交并校验可快进关系，只对已验证对象执行本地 `git merge --ff-only`；`upload-local-storage-deploy.ps1` 仅能上传仓库外的 Nginx 候选文件。
- 验证基线：后端全量 `342 passed, 1 skipped, 1 warning`，前端 42 个静态测试与生产构建通过；部署脚本回归 `14 passed, 1 warning`。
- 实施记录：`docs/superpowers/plans/2026-07-14-review-remediation.md`。
- 服务器部署影响：需要同步代码、重启后端、重新构建并发布前端、更新并 reload Nginx；不需要数据库迁移或环境变量修改。服务器只读预检已发现未提交后端文件和未跟踪的 `frontend/.env.production`，必须由维护者先核对处理；在工作区干净前禁止真实部署。

### 2026-07-15 总体治理路线图与第一阶段实现状态

- 设计：`docs/superpowers/specs/2026-07-15-overall-governance-roadmap-design.md`
- 实施计划：`docs/superpowers/plans/2026-07-15-overall-governance-roadmap.md`
- 一致性评估：`docs/superpowers/2026-07-15-project-consistency-assessment.md`
- **Task 0（基线复核）已完成（条件性通过）：** 前置分任务（共享题库闭环、自由练习/读路径过滤）代码侧可视为完成；工作区差异已分类；未覆盖用户改动。
- **第一阶段（业务数据规则）代码主体已在工作区（修改记录第 58 轮），验收门未全部签字：**
  - 正式删除入口统一调用 `soft_delete`；课程恢复按 `deleted_at + deleted_by` 同批次级联；`purge_resource` 仅处理已软删记录；删除/恢复/清理写审计。
  - 题干哈希统一为 `question_bank_service` 规范化 SHA-256；`schema_compat` 回填空值/旧 MD5/异常长度；**未**单独拆 `question_hash_service.py`。
  - 定向回归（软删关系/文件访问/读过滤/题库）曾记 **53 passed**；后端用例收集 **356**；前端静态 **42 passed**。
  - **未验证：** 真实 MySQL 哈希回填；完整七类“正式入口 → 回收站可见 → 恢复”矩阵是否 100% 对齐路线图验收门 1–6；本轮文档同步未重跑全量 pytest 与 `npm run build`。
- **阶段 D 剩余：** Task 3–5（缓存边界、忘记密码跨进程限流、启动锁与索引）仍未实施，归总体治理第三阶段。
- **第二阶段及以后：** 可恢复发布、并发扩容、工程结构收口均未开始。
- 服务器部署影响：**本条为文档同步，不需要服务器修改。** 第一阶段代码若将来上线，须先过第二阶段备份/回退/健康检查门，不得直接部署脏工作区。

### 2026-07-17 删课后共享题库不再隐形

- 问题：删课路径不转挂题目，但活跃题库查询仍要求所属课程未软删，导致题目 `deleted_at is None` 却在列表、练习、查重、管理端“消失”。
- 修复：
  - `question_bank_service._active_questions_query` 只过滤 `Question.deleted_at`
  - 教师题库列表/单题、管理端公共题库列表/单题/更新/批量删除、学生自由练习可见范围同步去课程软删过滤
  - 公共课挂载题即使挂载课进回收站，只要题目未删仍属共享题库；私有课题目仍要求挂载课活跃且学生有选课
  - `rehome_questions_before_course_delete` 降级为历史兼容空操作，正式删课路径不得再依赖转挂
- 回归保护：扩展 `test_soft_delete_read_filters`、`test_030405_management_systems`、`test_public_course_delete`、`test_integration_bugfixes`
- 服务器部署影响：需要服务器拉代码、**重启后端**；**不需要**数据库迁移、前端重建、Nginx 或环境变量调整

### 2026-07-17 共享题库删课后续闭环（已通过临时 MySQL 验收）

- 计划：`docs/superpowers/plans/2026-07-17-shared-question-bank-followups.md`
- **稳定事实（代码侧）：**
  - 课程物理清理：允许共享题/资料/作品/source 等引用脱钩（`SET NULL` + 名称快照）；同批子资源与历史课时进度仍按既有规则清理；cleanup 预检阻断非同批活跃引用
  - 管理员独立共享题库：`/api/admin/question-bank` + `/admin/question-bank`；公共课程页只维护阶段/资料；旧公共课题库路由保留并返回 `Deprecation`/`Link`
  - 学生全局自由练习：`/api/quiz/questions` + `/practice/quiz`；课程卡片只承载作业；草稿键 `quiz-draft:global-practice`
  - 学生 quiz 路由强制学生角色；管理审计使用真实 `AuthUser`；历史 `question_bank_root_course_id` 不再参与启动改写/删课阻断；无效 ORM `cache_result` 已移除
- **验证：** 定向后端相关套件通过；前端相关静态测试、`npm run type-check`、`npm run build` 通过
- **真实 MySQL 验收（2026-07-17）：** 临时库 `tongshi_cleanup_verify` 上执行 `backend/scripts/verify_course_cleanup_mysql.py`，`information_schema` 外键矩阵与 cleanup 脱钩场景 `ALL_MYSQL_VERIFY_OK`；设计文档 `docs/superpowers/specs/2026-07-17-course-purge-reference-detachment-design.md`；SQLite `PRAGMA foreign_keys=ON` 单测通过
- **附带修复：** 系统清理审计改为 `user_id=NULL`（避免无 `system` 用户时 FK 失败）；审计 `error_message` 截断 512
- 服务器部署影响：见修改记录第 71 轮（需拉代码、重启后端、重建前端；需 schema_compat/可空列与 SET NULL FK 兼容迁移；发布前备份）
