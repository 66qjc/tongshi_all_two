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
- 发布作业可以一次选择同一课程下的多个班级
- 作业练习必须通过 `QuizAttempt.announcement_id` 记录作业维度
- 学生提交作品必须选择自己已加入班级对应的课程
- 教师只能访问自己创建的课程及其下属班级、资料、题目、学生成绩和作品审核范围
- 教师可以删除自己课程下的资料，包括公共课程同步到教师课程副本里的资料，但不会影响公共课程源
- 教师可以新增和编辑自己课程中的题目，但不能删除题目；题目删除仅由管理员执行
- 公共课程的题库为全站共享题库，不再复制题目到教师课程副本；教师和管理员新增或导入题目会写入公共题库并记录贡献日志
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
