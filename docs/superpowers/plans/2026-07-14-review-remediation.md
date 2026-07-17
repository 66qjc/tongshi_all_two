# 代码审查问题修复实施计划

> **已废止（共享题可见性/入口部分）：** “活跃共享题必须所属课程未删除”“管理员仅通过活跃公共课程入口管理题库”等表述已废止。
> **现行规则：** 活跃共享题只看 `Question.deleted_at`；管理员独立入口 `/admin/question-bank` 与 `/api/admin/question-bank`；删课不转挂、不隐藏共享题；物理清理可置空挂载。
> **依据：** `docs/superpowers/plans/2026-07-17-shared-question-bank-followups.md`。

> **执行要求：** 当前工作区包含用户尚未提交的前后端改动。本计划在当前会话内逐项执行，必须使用测试驱动开发、系统化调试和完成前验证；不得回滚、提交、推送或部署无关改动。

**目标：** 修复共享题库管理权限与去重、管理端软删除过滤、展示文件预览权限、内容块扫描性能、删除风险文案和 Nginx `.mjs` 匹配范围，并完成文档与部署影响记录。

**方案：** 共享题库的正常读写统一只处理“题目未删除且所属课程未删除”的记录，管理员通过任一活跃公共课程入口管理全站共享题库。题干哈希统一下沉到共享题库辅助服务，教师和管理员的新增、编辑、导入复用同一套规则。展示文件先判断激活内容的公开访问，再判断管理员或教师对自己创建的未激活展示项的封面、图库和内容块图片访问；内容块检查使用分批迭代，避免一次加载全表 JSON。

**技术栈：** FastAPI、SQLAlchemy、Pytest、Vue 3、TypeScript、Node 静态测试、Nginx。

---

## 范围与验收

### 范围内

- 管理员可从任一活跃公共课程入口编辑教师私有课程中贡献到共享题库的活跃题目。
- 管理员与教师新增、编辑、导入题目时，统一计算 `stem_hash`，同题干在全站活跃共享题库中拒绝或跳过；编辑排除当前题目。
- 管理端公共课程、资料、题目查询排除软删除记录及所属软删除课程。
- 激活展示内容的文件保持公开；未激活展示内容仅允许创建者管理员或教师读取，其他用户不能读取。
- 内容块图片引用检查改为分批扫描，不引入数据库结构变更。
- 删除共享题目的单条、批量、全部确认文案明确教师贡献题目、作业引用、答题记录和不可恢复风险。
- Nginx `.mjs` MIME 规则仅匹配 `/assets/` 下的文件。
- 修复本轮涉及文档的尾部空白并记录服务器部署影响。

### 不在范围内

- 不改变现有接口响应结构。
- 不新增数据库表、字段或迁移。
- 不部署到服务器，不覆盖服务器脏工作区。
- 不处理完整软删除写入口、Redis、多 worker、上传连接池等其他长期债务。

## 任务 1：补充后端失败测试

**文件：**

- 修改：`backend/tests/test_public_question_contribution.py`
- 修改：`backend/tests/test_soft_delete_read_filters.py`
- 修改：`backend/tests/test_material_file_acceleration.py`

- [x] 新增管理员跨课程入口编辑教师贡献题目的接口测试，当前应因 `Course.is_public` 和 `course_id` 限制失败。
- [x] 新增管理员新增、编辑、导入写入 `stem_hash` 并拦截同题干的测试，当前应因管理员路径未写哈希失败。
- [x] 新增软删除公共课程、资料、题目不出现在管理端正常入口且不能再编辑的测试，当前应因查询缺少 `deleted_at` 过滤失败。
- [x] 新增未激活展示项创建者可读取封面、图库和内容块图片，非创建者不可读取的测试，当前应因死代码失败。
- [x] 分别运行新增测试并确认失败原因与目标缺陷一致，而不是测试设置或语法错误。

## 任务 2：统一共享题库哈希与活跃记录范围

**文件：**

- 修改：`backend/app/services/question_bank_service.py`
- 修改：`backend/app/services/question_service.py`
- 修改：`backend/app/services/admin_public_course_service.py`

- [x] 在 `question_bank_service.py` 增加统一的题干规范化与哈希函数，哈希算法保持与现有数据兼容。
- [x] 让指纹收集、题目列表、统计和重复查询只覆盖活跃题目及其活跃课程。
- [x] 教师新增、编辑、导入改为复用统一哈希函数，并在哈希查重时排除软删除题目和软删除课程。
- [x] 管理员新增写入 `stem_hash`，管理员编辑合并变更后重算哈希并排除自身查重，管理员导入写入哈希并把同题干计入跳过结果。
- [x] 运行共享题库定向测试，确认新增失败测试转绿且已有贡献日志、批量删除行为不回归。

## 任务 3：修复管理员共享题目编辑与软删除过滤

**文件：**

- 修改：`backend/app/api/v1/routes/admin_public_course_routes.py`
- 修改：`backend/app/services/admin_public_course_service.py`

- [x] `_get_public_course`、公共课程列表和 `get_course_by_id` 排除软删除课程。
- [x] 公共资料获取、列表、更新、删除同时排除资料和所属课程的软删除记录。
- [x] 共享题目获取、列表、更新、删除只处理活跃题目和活跃所属课程。
- [x] 编辑路由只校验当前入口是活跃公共课程，不再要求题目原始 `course_id` 等于入口课程。
- [x] 运行管理员公共课程与软删除定向测试，确认新增失败测试转绿。

## 任务 4：修复展示文件访问权限与扫描性能

**文件：**

- 修改：`backend/app/services/file_service.py`
- 修改：`backend/tests/test_material_file_acceleration.py`

- [x] 保留激活展示项封面、图库、内容块图片的匿名公开读取。
- [x] 激活引用未命中时，仅允许 `admin` 或 `teacher` 读取自己创建的未激活展示项所引用的封面、图库和内容块图片。
- [x] 普通用户和非创建者继续返回无权限结果。
- [x] 内容块检查使用 `yield_per` 分批迭代，只读取 `id`、`created_by`、`content_blocks` 等必要列，不使用 `.all()` 一次加载全部 JSON。
- [x] 运行文件权限定向测试，确认拥有者与非拥有者边界均通过。

## 任务 5：修复前端风险文案与静态测试

**文件：**

- 修改：`frontend/src/views/admin/AdminPublicCourses.vue`
- 修改：`frontend/tests/copy-consistency-static.test.mjs`

- [x] 先更新静态测试，要求删除题目文案明确“可能包含教师贡献题目”“会从作业移除引用”“会删除相关答题记录”“不可恢复”，并确认旧实现失败。
- [x] 更新单条、批量和全部删除确认文案，保持正常中文并覆盖上述风险。
- [x] 移除“教师自行新增题目不受影响”的过时断言，保留公共资料不影响教师自建资料的既有语义。
- [x] 运行前端静态测试，确认文案约束通过。

## 任务 6：收窄 Nginx `.mjs` 匹配范围

**文件：**

- 修改：`deploy/nginx.conf`
- 修改：`backend/tests/test_deploy_files_static.py`

- [x] 先新增静态断言，要求存在 `location ~* ^/assets/.*\.mjs$`，并禁止全局 `location ~* \.mjs$`，确认当前配置失败。
- [x] 修改 Nginx 规则，仅为 `/assets/` 下 `.mjs` 文件设置 JavaScript MIME 和长期缓存。
- [x] 运行部署静态测试，并执行部署脚本 DryRun，确认配置引用与脚本流程没有回归。

## 任务 7：文档同步与完整验证

**文件：**

- 修改：`docs/superpowers/plans/2026-07-14-review-remediation.md`
- 修改：`backend/docs/项目修改记录.md`
- 修改：`docs/superpowers/project-map.md`

- [x] 在本计划勾选实际完成项，记录任何需要用户判断而暂缓的事项。
- [x] 在项目修改记录中写明本轮功能、测试结果和服务器部署影响。
- [x] 更新项目地图中的稳定事实：共享题库编辑/去重、展示文件预览权限和 Nginx 资源规则。
- [x] 执行受影响后端测试，必要时执行后端全量测试。
- [x] 执行前端静态测试和 `npm run build`。
- [x] 执行 `git diff --check`，修复本轮及已知文档尾部空白，不处理无关业务差异。
- [x] 执行 `graphify update .` 更新代码图谱。
- [x] 对照本计划逐项自审，确认没有扩大权限、没有改变接口结构、没有覆盖并发修改。

## 任务 8：审批复核缺口收口（2026-07-15）

**文件：**

- 修改：`backend/app/services/file_service.py`
- 修改：`backend/app/services/question_service.py`
- 修改：`backend/app/services/admin_public_course_service.py`
- 修改：`backend/app/api/v1/routes/admin_public_course_routes.py`
- 修改：`backend/tests/test_material_file_acceleration.py`
- 修改：`backend/tests/test_soft_delete_read_filters.py`
- 修改：`backend/tests/test_public_question_contribution.py`
- 修改：`frontend/tests/admin-question-batch-delete-static.test.mjs`
- 修改：`frontend/package.json`
- 修改：`backend/tests/test_deploy_files_static.py`
- 修改：`deploy/README.md`
- 修改：`deploy/redeploy-server.ps1`
- 修改：`deploy/upload-local-storage-deploy.ps1`

- [x] 为未激活展示文件补充管理员创建者、管理员非创建者的封面、图库和内容块图片回归测试；激活展示内容仍保持匿名公开。
- [x] 调整文件授权顺序，使管理员先经过展示文件的创建者边界；展示封面和图库的活跃引用查询显式过滤 `ShowcaseItem.is_active`。
- [x] 为教师和管理员 Excel 导入软删除课程补充失败测试，并在课程选择查询中排除 `Course.deleted_at` 非空记录。
- [x] 管理端公共课程格式化和同步摘要仅统计活跃课程副本、资料和题目，并补充聚合字段回归测试。
- [x] 修正管理员导入同题干测试，断言重复项进入 `skips` 而非 `errors`，且不计入失败统计。
- [x] 补充 `find_same_stem_question` 对软删除题目和软删除课程的覆盖。
- [x] 让三个删除确认框分别断言四项风险文案，并将实际使用的 `admin-question-batch-delete-static.test.mjs` 作为本任务的前端回归入口。
- [x] 将 Nginx 静态测试收紧到目标 location 块；部署说明和脚本明确服务器脏工作区门禁、活动配置安装、`nginx -t`、reload 和失败回退。
- [x] 已完成本地验证、提交推送和服务器只读状态检查；因服务器工作区脏而按门禁停止真实部署，未覆盖任何文件。

## 执行结果

- 审批复核的权限、软删除、展示文件和部署门禁缺口已完成本地收口；未扩大接口权限或改变响应结构。
- 后端定向回归：`87 passed, 1 warning`（包含权限、软删除、共享题库和部署脚本用例）。
- 后端全量测试：`342 passed, 1 skipped, 1 warning`。
- 前端静态测试：42 个 `.test.mjs` 文件全部通过；`npm run test:admin-question-batch-delete` 也通过。
- 前端生产构建：类型检查和 Vite 构建通过，仅保留既有大分块警告。
- 部署脚本回归：`14 passed, 1 warning`，覆盖错误 SHA 在 SSH 前失败、CRLF 过滤、提交锁定快进和 Nginx 候选文件上传参数。
- `git diff --check` 已通过；`.pytest-*` 临时目录仅用于本地测试，不纳入提交。
- `graphify update .` 已完成增量更新；仅提示 skill/包版本不一致与一条既存置信度拼写警告，图谱已重建。
- 本地提交 `4bffef1` 已安全推送到 `origin/main`；服务器的 `origin/main` 已指向 `4bffef1`，但工作树 HEAD 仍为旧提交 `6155d70`。
- 服务器只读预检：各核心服务、健康检查与 `nginx -t` 均通过；但服务器工作区仍不干净、根分区约 92% 已用（约 3.2GB 可用），本轮按门禁不执行真实部署。

## 服务器部署影响

正式发布需要先将已验证提交推送到 `origin/main`，再由 `redeploy-server.ps1` 以锁定 SHA 进行一次无交互 `fetch`、本地快进、后端重启和健康检查。需要重新构建并发布前端；若采用新的 Nginx 配置，需先上传到仓库外候选目录，备份后执行 `nginx -t` 再 reload。不需要数据库迁移或环境变量修改。

服务器已只读检查到 4 个已修改代码文件：`backend/app/api/v1/routes/material_routes.py`、`backend/app/api/v1/routes/public_learning_routes.py`、`backend/app/services/file_service.py`、`backend/app/services/public_learning_service.py`，以及一个未跟踪的 `frontend/.env.production`。它们必须先由服务器维护者核对、备份并提交或人工合并；在 `git status --porcelain=v1 --untracked-files=all` 为空、服务器 `origin/main` 与目标 SHA 一致、根分区留有足够构建余量前，禁止真实部署、强制覆盖、`git clean`、`git reset` 或统一发布脚本的绕过调用。

本 P2 验收补充仅调整测试断言和本地 npm 测试入口，不需要单独修改服务器、重启服务、重新构建前端、执行数据库迁移或调整环境变量；随任务 8 的业务改动统一发布时，仍遵循上述服务器脏工作区门禁。
