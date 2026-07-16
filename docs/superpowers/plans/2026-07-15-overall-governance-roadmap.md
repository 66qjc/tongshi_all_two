# AI 通识教育课程平台总体治理路线图实施计划

> **给执行代理：** 必须按阶段逐项执行。步骤使用复选框跟踪。阶段 D、单机加固和多人占线已有各自的详细计划，本计划只负责准入、排序、边界和跨阶段验收，不复制其中的服务器命令或七类软删除实现细节。

**目标：** 在不覆盖当前工作区改动的前提下，先完成业务数据删除与恢复规则统一，再依次完成可恢复发布、并发一致性和工程结构收口。

**架构：** 采用四阶段串行准入。第一阶段复用阶段 D 的数据生命周期和题干哈希任务；第二阶段复用单机加固与一致性评估 P0；第三阶段复用阶段 D 的缓存、限流、索引、启动锁任务及多人占线计划；第四阶段只收敛高风险事务、接口契约、术语和文档事实源。每一阶段必须通过验收门，才能向下一阶段交接。

**技术栈：** FastAPI、SQLAlchemy、MySQL、SQLite、Redis、Vue 3、TypeScript、Vite、Element Plus、pytest。

---

## 执行前约束

- 用户已确认以功能上线速度为第一目标，第一开发重点是数据删除与恢复规则统一。
- 用户允许在当前无人使用期间安排维护停服；本计划不要求双实例或零中断发布。
- 当前工作区存在大量未提交改动，所有执行者必须保留它们；不得执行 `git reset --hard`、`git checkout --`、`git clean` 或批量删除。
- 两个正在推进的分任务完成前，不进入 Task 1 的代码实施。完成的定义见 Task 0。
- 本计划不直接修改服务器。每个需要服务器操作的阶段必须沿用对应既有计划，并在阶段记录中填写服务器部署影响。
- 每个阶段的代码改动必须先写失败测试，再写最小实现；每阶段结束运行受影响测试、前端构建和 `git diff --check`。
- 不自动提交或暂存文件。若需要提交，执行者必须先确认只包含当前阶段文件，并获得明确提交授权。

## 文件与职责地图

### 第一阶段涉及文件

软删除入口和关系保持沿用 `docs/superpowers/plans/2026-07-10-remediation-phase-d-soft-delete-cache-db.md` 的 Task 1，涉及：

- `backend/app/services/soft_delete_service.py`
- `backend/app/services/class_service.py`
- `backend/app/services/announcement_service.py`
- `backend/app/services/material_service.py`
- `backend/app/services/project_service.py`
- `backend/app/services/question_service.py`
- `backend/app/services/admin_public_course_service.py`
- `backend/app/services/file_service.py`
- `backend/app/api/v1/routes/admin_routes.py`
- `backend/app/api/v1/routes/admin_public_course_routes.py`
- `frontend/src/api/admin.ts`
- `frontend/src/views/admin/AdminRecycleBin.vue`
- `backend/tests/test_030405_management_systems.py`
- `backend/tests/test_soft_delete_relationships.py`
- `backend/tests/test_soft_deleted_file_access.py`

题干哈希统一沿用同一计划的 Task 2，涉及：

- `backend/app/services/question_hash_service.py`
- `backend/app/models/entities.py`
- `backend/app/services/question_service.py`
- `backend/app/services/admin_public_course_service.py`
- `backend/app/db/schema_compat.py`
- `backend/tests/test_question_duplicate_candidates.py`
- `backend/tests/test_question_import_skip.py`
- `backend/tests/test_schema_compat.py`

### 第二阶段涉及文件和外部边界

- 仓库内：`deploy/redeploy-server.ps1`、`deploy/README.md`、`backend/docs/项目修改记录.md`、`docs/superpowers/project-map.md`（仅在稳定入口发生变化时更新）。
- 服务器外部边界：备份、journal、磁盘检查、systemd、Nginx、环境变量和上传目录只按 `docs/superpowers/plans/2026-07-14-single-server-ops-hardening.md` 执行，不在本计划另写命令。

### 第三阶段涉及文件

缓存、限流和数据库兼容沿用阶段 D 的 Task 3 至 Task 5：

- `backend/.env.example`
- `backend/app/core/config.py`
- `backend/app/core/cache.py`
- `backend/app/db/redis_client.py`
- `backend/app/services/admin_public_course_service.py`
- `backend/app/services/class_service.py`
- `backend/app/services/question_service.py`
- `backend/app/services/course_response_service.py`
- `backend/app/services/auth_service.py`
- `backend/app/api/v1/routes/admin_public_course_routes.py`
- `backend/app/api/v1/routes/course_routes.py`
- `backend/main.py`
- `backend/app/db/schema_compat.py`
- `backend/tests/test_cache_behavior.py`
- `backend/tests/test_cache_authorization.py`
- `backend/tests/test_forgot_password_rate_limit.py`
- `backend/tests/test_mysql_schema_compat_integration.py`
- `backend/tests/test_search_optimization.py`

扩容参数、Nginx 形态和前端高延迟适配继续归 `docs/superpowers/specs/多人占线计划暂存.md`，不得在本计划中重新定义参数。

### 第四阶段涉及文件

- 服务事务边界：以静态扫描识别的高风险写路由和对应 service 为范围，优先处理 33 个直接数据库写操作路由，不迁移无风险只读查询。
- 核心接口契约：`backend/app/api/v1/routes/` 中的登录、分页、详情、文件签名和作业接口，以及其 Schema/API 类型文件。
- 稳定事实文档：`docs/superpowers/project-map.md`、`backend/docs/项目修改记录.md`、运维说明、术语表和变更记录索引。
- 图谱同步：代码或文档事实改变后运行 `graphify update .`，不暂存 `graphify-out/` 产物。

## Task 0：分任务完成门与基线复核

**目标：** 确认当前两个分任务已经结束且不会与总体治理第一阶段争用同一规则。

- [x] **Step 1：确认分任务交付物**

逐项核对两个分任务的代码、测试、计划或修改记录。每个分任务必须能回答：改了哪些文件、测试如何验证、是否需要服务器部署、是否改变删除/恢复/缓存/题库语义。

**2026-07-15 复核结论：**

1. **共享题库闭环**（`docs/superpowers/plans/2026-07-14-shared-question-bank-closure.md`，修改记录第 54 轮）
   - 代码/测试：列表补齐 `created_by`/`creator_name`/`star_rating`/`is_owner`；编辑与导入补齐 `stem_hash`；教师端添加人与 1-5 星展示。
   - 验证：相关后端 18 passed（记录时）；当前定向回归含题库与软删共 53 passed；前端 `teacher-question-bank-static` 与全量 42 个静态测试通过。
   - 服务器：需要拉代码、重启后端、重建前端；不需要迁移/环境变量。**本机未代部署。**
   - 语义：改变题库展示与编辑归属判定，以及更新/导入的题干哈希拦截；**不改变删除/恢复/缓存生命周期**。
   - 状态：计划 19/20 勾完成；仅“手工验收教师端”未勾。代码侧可视为完成，手工验收仍待用户确认。

2. **自由练习范围 + 软删除读路径过滤**（`docs/superpowers/plans/2026-07-13-quiz-scope-soft-delete-read-filters.md`，项目地图 2026-07-13 记录）
   - 代码/测试：`quiz_service` 收紧提交范围；课程/班级/资料/作业/公开学习读路径过滤 `deleted_at`；学生拉题不预下发答案。
   - 验证：读过滤与相关回归已在工作区；`test_soft_delete_read_filters` 等纳入当前 53 条定向通过集。
   - 服务器：需拉代码并重启后端、重建前端；**不改变正式删除入口语义**（只做读路径与练习范围）。
   - 状态：记录为已落地；与第一阶段“正式删除入口统一软删”互补，不争用同一写入口规则。

补充：工作区另有「学」页教程站、PDF 自动加载、公开文件链路等 07-14 交付，属并行前端/文件链改动，不是总体治理第一阶段前置门，但占用同一工作区，分类见 Step 2。

- [x] **Step 2：读取工作区差异清单**

执行只读检查：

```powershell
git status --short
git diff --name-only
git diff --stat
```

将现有文件分为“分任务文件”“总体治理文件”“无关用户改动”三组。无关用户改动不纳入后续暂存、提交或回滚。

**2026-07-15 分类（约 64 项，未暂存/提交）：**

| 分组 | 代表范围 | 处理原则 |
|---|---|---|
| 分任务 A 共享题库 | `question_routes`/`schemas`/`TeacherQuestions`/`question.ts`/相关测试与计划 | 保留；不回滚 |
| 分任务 C 读路径与练习 | `quiz_service`/`access_control`/`PracticeQuizView`/`test_quiz_submit_scope` 等 | 保留；不回滚 |
| 学页/资料阅读 | `LearnView`/`CourseDetailView`/`MaterialInlineReader`/公开学习相关 | 保留；非本阶段提交范围 |
| 公开文件/活动页/文案 | `Act*`/`HeroSection`/`material_routes`/相关静态测试 | 保留；非本阶段提交范围 |
| 总体治理文档 | `2026-07-15-overall-governance-*`、一致性评估、单机加固计划 | 文档；可与阶段记录同步 |
| 治理第一阶段代码（已在工作区） | `soft_delete_service` 与七类删除入口、`schema_compat` 哈希回填、软删关系/文件测试、修改记录第 58 轮等 | **已是 Task 1 范围实现**，见 Step 3 |
| 混合/其它 | `project-map.md`、`项目修改记录.md`、`PRODUCT.md` | 记录类与产品文；不覆盖无关用户意图 |

- [x] **Step 3：复核治理设计与现状差异**

重新阅读 `docs/superpowers/specs/2026-07-15-overall-governance-roadmap-design.md`、一致性评估和两个分任务记录，确认第一阶段仍以删除/恢复规则为首要范围。若分任务已改变其中的稳定事实，先修订设计文档，再继续本计划；不得直接按旧假设写代码。

**2026-07-15 关键差异（必须先解释再继续）：**

1. **第一阶段目标未变：** 仍以七类资源正式删除/恢复/最终清理、活跃过滤、审计和题干 SHA-256 统一为首要范围；缓存/多 worker/发布加固仍属后阶段。
2. **实现超前于本计划勾选：** 修改记录第 58 轮已写明“正式删除入口软删除与题干哈希升级”，工作区中班级/作业/资料/作品/用户/公共课/公共资料/题目删除入口已调用 `soft_delete`；`restore_resource` 按 `deleted_at + deleted_by` 同批次恢复课程子资源；`purge_resource` 仅清理已软删记录；`question_bank_service.compute_stem_hash` 为规范化 SHA-256，`schema_compat` 回填空值/非 64 位旧哈希。
3. **阶段 D 计划文件未同步：** `2026-07-10-remediation-phase-d-soft-delete-cache-db.md` 的 Task 1/2 复选框仍全为未勾，与代码和修改记录不一致。
4. **路径偏差：** 阶段 D 写的 `question_hash_service.py` 未单独建文件，哈希落在 `question_bank_service.py`；功能等价，文档应记为既成事实而非再拆文件。
5. **验收门尚未完全闭合的风险点：** 阶段 D 原文要求“全部通过真实正式删除入口”的回收站可见/恢复批次/七类完整矩阵；当前 `test_soft_delete_relationships` 覆盖班级/作业/资料/作品/教师/公共课/公共资料/题目引用拒绝，**不等于**路线图验收门 1–6 已全部签字。真实 MySQL 哈希回填未验证。
6. **与分任务边界：** 共享题库闭环与读路径过滤不否定删除生命周期，但共享题库已占用 `question_service`/哈希语义；后续 Task 1 只能在既有 SHA-256 与软删入口上补验收缺口，禁止再引入第二套 helper。

**结论：** 设计目标仍有效；不得假装“尚未开始 Task 1”。进入 Task 1 前应改为**差距验收与补测**，而不是从零重写。是否修订设计文档表述（“待实施”→“工作区已实现、待闭合验收”）需用户确认。

- [x] **Step 4：建立阶段基线**

记录当前后端测试数量、前端静态测试入口、前端构建状态、服务器部署影响的现状声明和未提交文件边界。基线只写入当前阶段记录，不把一次性命令输出写进 `AGENTS.md`。

**2026-07-15 基线：**

| 项 | 现状 |
|---|---|
| 后端用例收集 | `356 tests collected`（`pytest --collect-only`） |
| 定向回归（软删关系 + 文件访问 + 读过滤 + 题库） | **53 passed，1 warning** |
| 前端静态测试 | **42 passed**（`node --test tests/*.mjs`） |
| 前端生产构建 | 本轮 Task 0 **未重跑** `npm run build`（避免与大量未提交前端改动纠缠）；修改记录第 57/58 轮曾记通过 |
| 服务器 | 本轮**未连接/未修改服务器**；第 58 轮声明不需要服务器修改；上线仍须第二阶段备份与维护门 |
| 工作区 | `main` 上大量未提交改动；禁止 `reset/clean`；未获授权不暂存提交 |
| 分支 | `main...origin/main`，无独立 worktree |

**完成门：** 两个分任务均有明确交付状态；工作区差异已分类；设计与实现无未解释冲突；用户改动未被覆盖。未通过时停止，不进入 Task 1。

**完成门判定（2026-07-15）：条件性通过，需用户确认后才进入 Task 1。**

- 两个前置分任务：代码侧可视为完成；共享题库手工验收仍开放。
- 工作区已分类，用户/并行改动未覆盖。
- **存在必须解释的冲突：** Task 1 主体代码已在工作区（第 58 轮），阶段 D 勾选与设计“待实施”表述过时。
- 因此：**停止自动进入 Task 1 重写**；下一步只能是用户确认后的“差距清单验收/补测/文档同步”。

**用户决策（2026-07-15）：选项 3 — 只做文档同步。**

已同步：设计状态快照、阶段 D Task 1/2 勾选与路径偏差说明、`project-map`、`AGENTS.md`、修改记录第 59 轮。**未**进入 Task 1 代码或补测；验收门仍未签字。

## Task 1：业务数据规则闭环

**目标：** 让删除、恢复、最终清理、活跃读取和题干哈希在所有正式入口上表达同一规则。

- [ ] **Step 1：按阶段 D Task 1 编写失败测试**

执行阶段 D Task 1 中的主记录、关联记录、回收站、恢复、文件权限和题目引用测试设计。测试必须从真实正式删除入口进入，并断言主记录未物理消失、普通读取不可见、回收站可见、恢复结果符合删除批次规则。

- [ ] **Step 2：运行失败测试并记录现状**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_030405_management_systems.py backend/tests/test_soft_delete_relationships.py backend/tests/test_soft_deleted_file_access.py -q
```

Expected：在实现尚未闭环的路径上出现失败；若全部通过，先核对测试是否覆盖正式入口和关联数据，不得直接宣称阶段完成。

- [ ] **Step 3：实现统一软删除入口**

严格按阶段 D Task 1 的步骤 3 至步骤 6 实施：资源 ID 转换、各正式入口改用软删除服务、保留关联记录、同批次恢复、活跃读取过滤和文件权限过滤。不得在本计划中新增另一套软删除 helper 或改变阶段 D 已确认的动作名。

- [ ] **Step 4：按阶段 D Task 2 统一题干哈希**

先实现统一规范化函数和 SHA-256 计算，再覆盖创建、编辑、管理员创建和导入；兼容层分批升级旧 MD5、空值和异常长度记录。哈希只作候选索引，最终重复判定继续比较完整题目语义。

- [ ] **Step 5：运行第一阶段回归**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_030405_management_systems.py backend/tests/test_soft_delete_relationships.py backend/tests/test_soft_deleted_file_access.py backend/tests/test_teacher_student_delete_scope.py backend/tests/test_project_course_scope.py backend/tests/test_public_course_delete.py backend/tests/test_question_duplicate_candidates.py backend/tests/test_question_import_skip.py backend/tests/test_schema_compat.py -q
npm run build --prefix frontend
git diff --check
```

Expected：受影响后端测试通过，前端生产构建成功，差异无空白错误。真实 MySQL 迁移测试未配置时必须明确记录为未验证，不得用 SQLite 结果替代。

- [ ] **Step 6：同步第一阶段记录**

在 `backend/docs/项目修改记录.md` 或阶段 D 既有记录中补充本阶段实际变更、测试结果和服务器部署影响。若尚未发布到服务器，明确写“不需要服务器修改”；若需要维护发布，只记录待执行影响，不在本地直接操作服务器。

**第一阶段验收门：** 七类资源正常删除后普通页面、统计和文件入口均不可见；回收站可见；恢复只恢复同批次；最终清理才物理删除；删除、恢复、清理有审计；题干哈希规则统一；本地回归和构建通过。

## Task 2：生产安全与可恢复发布

**目标：** 让第一阶段能够在计划维护窗口内安全发布、失败回退并验证数据恢复点。

- [ ] **Step 1：冻结第一阶段发布版本**

确认第一阶段代码只来自已分类的当前变更，建立可追溯提交或等价版本标识；环境文件、用户未提交改动和临时文件不得混入发布源。

- [ ] **Step 2：执行单机加固计划的备份与恢复任务**

按 `docs/superpowers/plans/2026-07-14-single-server-ops-hardening.md` 的 Task 1、Task 2、Task 6 执行。该计划负责具体备份、磁盘、journal、timer 和恢复命令，本计划不复制命令。任何备份失败、恢复校验失败或磁盘低于阈值，都阻止发布。

- [ ] **Step 3：执行可重复部署与健康检查任务**

按单机加固计划 Task 5 和 Task 7 验证依赖同步、前端构建、静态同步、服务重启、健康检查和失败日志。维护窗口允许停服，但只有健康检查成功后才报告发布成功。

- [ ] **Step 4：核对安全边界决定**

按一致性评估 P0-3 核对 HTTPS、后端环回绑定、端口阻断、文件 Range 访问和登录跳转。若域名、证书或网络权限尚未具备，记录为阻塞风险，不用“当前端口外部超时”推断安全完成。

- [ ] **Step 5：同步服务器影响记录**

明确写出是否拉取代码、重启后端/Nginx/MySQL/Redis、重新构建前端、执行数据库迁移、修改环境变量、建立备份 timer。没有执行的项目写“不需要服务器修改”或“尚未执行”，不能用计划内容代替运行证据。

**第二阶段验收门：** 数据库和上传文件可隔离恢复；磁盘与日志门槛有效；发布源可追溯；维护失败有回退路径；首页、关键 API、健康接口和受控文件访问通过。

## Task 3：并发性能与跨进程一致性

**目标：** 只有在第一、二阶段稳定后，才启用可验证的缓存、多进程限流、数据库索引和扩容评估。

- [ ] **Step 1：先按阶段 D Task 3 编写缓存失败测试**

覆盖稳定键、Session 不入键、JSON DTO、权限隔离、精确失效、Redis 故障冷却、`REDIS_ENABLED=false` 降级和测试 Redis 命名空间。测试不得连接生产 Redis DB 或使用 `FLUSHDB`。

- [ ] **Step 2：按阶段 D Task 4 迁移忘记密码计数**

先验证两个独立 worker 共享 FakeRedis 计数，再实现 Redis 原子计数、TTL、成功清理和故障降级。Redis 未启用时只保证单 worker 语义，不能进入多 worker 准入。

- [ ] **Step 3：按阶段 D Task 5 完成启动锁和索引**

先在 SQLite 旧结构和 mock 测试中验证锁覆盖范围，再在名称以 `_test` 结尾且已备份的 MySQL 测试库中验证并发初始化、索引和锁释放。没有 `TEST_MYSQL_URL` 时明确记录真实 MySQL 未验证。

- [ ] **Step 4：运行缓存、认证、兼容和完整回归**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_cache_behavior.py backend/tests/test_cache_authorization.py backend/tests/test_forgot_password_rate_limit.py backend/tests/test_schema_compat.py backend/tests/test_search_optimization.py backend/tests/test_mysql_schema_compat_integration.py -q
backend\.venv\Scripts\python.exe -m pytest backend/tests -q --basetemp=tmp/pytest-phase-governance
npm run build --prefix frontend
```

Expected：本地业务测试和构建通过；真实 MySQL 条件测试若无凭据仅允许明确跳过。

- [ ] **Step 5：依据多人占线计划评估 worker 和连接池**

完成缓存、启动锁、连接池和 Nginx 依赖核对后，才按 `docs/superpowers/specs/多人占线计划暂存.md` 的阶段顺序做压测。不得直接采用计划中的 worker 数量或连接池数值作为完成证据；必须以 CPU、内存、MySQL 活跃连接数、P95 和 5xx 结果作准。

**第三阶段验收门：** 缓存命中不串权限且可精确失效；Redis 故障可降级；跨进程限流一致；数据库索引和启动锁通过真实条件验证；压测结论明确后才准入多 worker。

## Task 4：工程结构与文档收口

**目标：** 把前三阶段的稳定规则固化到事务边界、接口契约、术语和当前事实文档中。

- [ ] **Step 1：盘点 33 个直接数据库操作路由**

按一致性评估中的扫描结果建立清单，先标记包含写入、审计、缓存失效或回滚的高风险路由；只读查询和导出接口保持原状，避免无收益的大规模重构。

- [ ] **Step 2：为高风险写路由编写事务失败测试**

每个目标写入口至少覆盖业务写入成功、审计写入失败、缓存失效失败和异常回滚。测试断言同一业务操作只有一个事务拥有者，不能出现业务已提交而审计或缓存状态缺失。

- [ ] **Step 3：收敛事务到服务层**

按 Routes -> Services -> Models 约定迁移高风险写逻辑；路由只负责鉴权、参数解析和响应格式，服务负责业务写入、审计、缓存失效和一次性 commit/rollback。迁移过程中不得改变既有接口结构或删除/恢复语义。

- [ ] **Step 4：补齐核心响应契约检查**

为登录、分页、详情、文件签名和作业接口增加显式 Schema 或自动契约校验；文件流、Excel 和 keepalive 请求保留明确例外。每个新增或修改字段都必须同时更新后端 Schema、前端类型和回归测试。

- [ ] **Step 5：整理术语和稳定事实文档**

更新 `project-map.md`、修改记录和文档索引，固定“作业”“公告”“共享题库”“课程挂载上下文”“创建人编辑归属”等术语。历史计划保留历史状态，不能继续充当当前实现说明。

- [ ] **Step 6：执行第四阶段验证与图谱更新**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests -q --basetemp=tmp/pytest-final
npm run build --prefix frontend
git diff --check
graphify update .
```

Expected：后端回归、前端构建和差异检查通过；图谱增量更新成功；`graphify-out/` 不进入暂存范围。

**第四阶段验收门：** 高风险写路径事务边界清楚；核心接口字段变化可被检查；术语和生命周期只有一套；项目地图、运维手册和变更记录指向同一稳定事实。

## Task 5：总体验收与收尾

- [ ] **Step 1：逐项核对四阶段交接产物**

确认删除生命周期、发布基线、缓存/启动锁结论、压测基线、事务约定、契约清单和文档索引均有文件或测试证据。

- [ ] **Step 2：核对未完成项与阻塞项**

将未配置的真实 MySQL、尚未执行的服务器操作、未具备的 HTTPS 条件、压测限制和外部存储缺口分别记录为“未验证”“阻塞”或“后续范围”，不得写成已完成。

- [ ] **Step 3：同步最终修改记录**

修改记录必须包含本轮代码、接口、页面、构建和服务器部署影响；没有服务器操作时明确写“不需要服务器修改”。不把一次性调试命令和临时状态写入 `AGENTS.md`。

- [ ] **Step 4：保留工作区边界**

再次运行 `git status --short` 和 `git diff --name-only`，确认总体治理改动与两个分任务、用户既有改动可区分；未获授权不暂存、提交、推送或回滚任何文件。

## 总体完成标准

- 删除、恢复、最终清理、活跃读取和题干哈希规则在正式入口上可解释、可测试。
- 维护发布前有验证过的数据库和上传文件恢复点，失败有回退路径。
- Redis、跨进程限流、数据库启动锁和索引在启用多 worker 前完成条件验证。
- 高风险事务、核心接口契约、术语和长期文档形成稳定事实源。
- 每个阶段都有测试证据和服务器部署影响说明；未验证路径被明确标记。
