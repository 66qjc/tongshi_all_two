# 项目地图

## 当前架构

- 前端：`frontend/`，Vue 3 + TypeScript + Vite + Element Plus
- 后端：`backend/`，FastAPI + SQLAlchemy
- 部署：`deploy/nginx.conf` 负责生产 Nginx 示例，代理 `/api/` 和 `/uploads/` 到后端
- 存储：第一阶段默认本地上传目录，后续再接入 S3 / SeaweedFS / MinIO
- 测试：`backend/tests/`，以 SQLite 内存库为主

## 核心业务结构

```text
User(teacher) -> Course -> Class -> StudentClassEnrollment -> User(student)
User(teacher) -> Course -> Material
User(teacher) -> Course -> Question -> QuizAttempt
User(teacher) -> Course -> Project
User(teacher) -> Course -> Lesson
User(student) -> CourseProgress -> Course / Lesson
Announcement -> AnnouncementClass -> Class
Announcement -> QuizAttempt(announcement_id) -> TaskCompletion
```

## 后端主要文件

- ORM：`backend/app/models/entities.py`
- Schema：`backend/app/schemas/common.py`
- 兼容层：`backend/app/db/schema_compat.py`
- 班级服务：`backend/app/services/class_service.py`
- 资料服务：`backend/app/services/material_service.py`
- 资料预览服务：`backend/app/services/material_preview_service.py`
- 课时服务：`backend/app/services/lesson_service.py`
- 学习进度服务：`backend/app/services/progress_service.py`
- 题库服务：`backend/app/services/question_service.py`
- 公共课程题库贡献记录：`backend/app/services/question_contribution_service.py`
- 公告服务：`backend/app/services/announcement_service.py`
- 任务服务：`backend/app/services/task_service.py`
- 教师统计/成绩/作品审核：`backend/app/services/teacher_service.py`

## 教师端页面

- `/teacher`
- `/teacher/courses`
- `/teacher/classes`
- `/teacher/publish`
- `/teacher/grades`
- `/teacher/task-report`
- `/teacher/reviews`
- `/teacher/materials`
- `/teacher/student-admin`
- `/teacher/questions`

## 学生端页面

- `/learn`
- `/learn/course/:courseId`
- `/practice`
- `/practice/quiz/:courseId`
- `/practice/announcement/:announcementId`
- `/inbox`

## 长期约定

- 不再使用独立章节表、章节 API 或章节页面
- 资料、题目和作品都直接挂在课程下
- 答题统计以 `QuizAttempt` 为事实来源
- 新上传文件统一通过 `file_id` 访问 `/api/files/{id}`
- 生产环境预览 PDF / 视频优先走 Nginx 代理
- 第一阶段部署不要求 S3 端点存在
- 班级必须归属一门课程
- 发布题目可以一次选择同一课程下的多个班级
- 题目任务练习必须通过 `QuizAttempt.announcement_id` 记录任务维度
- 学生提交作品必须选择自己已加入班级对应的课程
- 教师只能访问自己创建的课程及其下属班级、资料、题目、学生成绩和作品审核范围
- 教师可以删除自己课程下的资料，包括公共课程同步到教师副本里的资料，但不会影响公共课程源
- 教师可以新增和编辑自己课程中的题目，但不能删除题目；题目删除仅由管理员执行
- 公共课程是所有教师共享的题库源。教师在公共课程副本里新增或导入题目时，会回写到源公共课程，再同步到所有教师副本
- 公共课程题库的新增与导入会记录到 `question_contribution_logs`，保存课程快照、操作人、动作类型、题目数量和时间
- 课程正式 API 统一使用 `/api/courses*`；历史 `/api/questions/courses*` 兼容入口已删除。
- 课程搜索使用 `ilike()`（大小写不敏感 + 中文子串），不再使用 `contains()`。
- 教师课程页“已添加课程”和“公共课程”均通过 `/api/courses` 分页接口携带关键词搜索。
- 教师学生列表分页直接在数据库层完成，不再全量查询到 Python 内存去重再切片。
- 回归保护：`frontend/tests/course-detail-layout-static.test.mjs` 用于验证课程详情页面布局不退化。
- 课程资料大文件打开优先走 `/api/materials/{material_id}/file`，后端鉴权后由 Nginx 内部目录传输
- 学生端和教师端资料展示统一使用图文资料卡片和站内预览；旧 `/api/files/{id}` 保留给图片、作品报告等通用文件访问
- 学生端“学”页面课时内容只能展示学生已加入课程下的已发布课时；草稿课时对学生不可见
- 课时富文本在创建、更新和读取时都必须经过后端白名单清洗；前端 `v-html` 仅渲染后端清洗后的内容
- 删除课时时必须清空 `course_progress.last_lesson_id` 引用，避免学习进度指向已删除课时

## 修改记录

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
