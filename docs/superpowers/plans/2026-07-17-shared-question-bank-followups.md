# 2026-07-17 共享题库删课后续审查与实施计划

> **供执行代理使用：** 实施时必须先使用 `subagent-driven-development`（推荐）或 `executing-plans`，按任务逐项执行并在每个任务后复核。
>
> **状态：** 代码主体已实施（2026-07-17 工作区）；SQLite/前端静态/type-check/build 已通过；真实 MySQL 临时库 cleanup/FK 已验证通过（`tongshi_cleanup_verify`）
>
> **日期：** 2026-07-17
>
> **前置事实：** 当前工作区已实现“删课不转挂、不软删、不隐藏共享题；活跃共享题只看 `Question.deleted_at`”，相关修改尚未提交
>
> **关联：** `docs/superpowers/specs/2026-07-15-unified-soft-delete-business-rules-design.md`、`docs/superpowers/plans/2026-07-15-unified-soft-delete-business-rules.md`、`docs/superpowers/plans/2026-07-15-overall-governance-roadmap.md`

**目标：** 在不回退共享题库现行规则的前提下，完成课程引用脱钩、独立管理员共享题库、学生全局自由练习池及相关权限、审计、文案和回归闭环。

**架构：** 保持 Routes -> Services -> Models 分层。课程物理清理采用“引用脱钩”：共享题、作品、长保留资料和课程自引用允许在父课程物理删除时置空，同批课程子资源及退役课时进度按既有快照规则清理；不建立系统锚点课、不恢复 rehome。管理员共享题库改为独立 `/api/admin/question-bank` 与 `/admin/question-bank`，学生自由练习改为独立全局题池入口；缓存先移除实际无效的 ORM 缓存装饰器，功能性缓存仍归总体路线图第三阶段。

**技术栈：** FastAPI、SQLAlchemy、MySQL、SQLite、pytest、Vue 3、TypeScript、Element Plus、Node 静态测试、Redis（本轮不启用新的缓存能力）。

---

## 一、复审范围与证据

### 1.1 已核对的当前实现

- 共享题库查询、教师题库、学生练习、管理员公共课题库：`question_bank_service.py`、`question_service.py`、`quiz_service.py`、`admin_public_course_service.py`
- 课程物理清理和 ORM/FK：`soft_delete_cleanup_service.py`、`entities.py`、`schema_compat.py`
- 作业题目范围：`announcement_service.py`、`task_service.py`
- 缓存：`core/cache.py`、`question_service.get_course_detail`、`admin_public_course_service.list_public_courses`
- 前端：教师题库、教师课程、管理员公共课程、学生练习、个人中心错题本
- 测试：练习提交、软删除读取、到期清理、公共课删除、共享题库贡献、题目导入查重及相关前端静态测试

### 1.2 本次新鲜验证（2026-07-17 提交前复核）

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_030405_management_systems.py backend/tests/test_admin_question_bank.py backend/tests/test_global_practice_pool.py backend/tests/test_integration_bugfixes.py backend/tests/test_public_course_delete.py backend/tests/test_public_question_contribution.py backend/tests/test_question_import_skip.py backend/tests/test_quiz_submit_scope.py backend/tests/test_schema_compat.py backend/tests/test_soft_delete_cleanup.py backend/tests/test_soft_delete_read_filters.py -q
```

结果：`170 passed, 1 warning`。

```powershell
$tests = Get-ChildItem frontend/tests -Filter '*.test.mjs'
foreach ($test in $tests) { node $test.FullName }
```

结果：`43` 个前端静态测试全部通过；`npm run type-check`、`npm run build` 通过。

真实 MySQL 临时库：`backend/scripts/verify_course_cleanup_mysql.py` 输出 `ALL_MYSQL_VERIFY_OK`，`cleaned_count=3`、`failed_count=0`，五类可脱钩外键均为 `ON DELETE SET NULL`。

### 1.3 复审阶段的验证限制（现已解除）

- 初次复审时，通用 SQLite 内存库未开启 `PRAGMA foreign_keys=ON`；现已新增 cleanup 专用外键开启测试。
- 初次复审时没有真实 MySQL 到期清理证据；现已在专用临时库 `tongshi_cleanup_verify` 完成外键矩阵与 cleanup 场景验证，未触碰正式库 `tongshi`。
- 目标文档是未跟踪新文件；工作区已有共享题库相关未提交修改，本计划不得覆盖或回滚这些修改。

## 二、对原问题清单的复审结论

| 原 ID | 复审结论 | 修正后的判断 |
|---|---|---|
| P0-1 | **确认，但原范围过窄** | `Question.course_id` 会阻断 MySQL Core DELETE；此外 `Course.source_course_id`、`question_bank_root_course_id`、未同批班级/资料/作业、阶段、历史课时/进度、作品等也可能阻断或级联。必须先做完整入站外键矩阵，不能只特判题目。 |
| P0-2 | **条件风险，方案已定** | 已选择 `Question.course_id ON DELETE SET NULL`；课程物理清理后学生题目可见性必须把空挂载题继续视为共享题，并补列表、提交和统计回归。 |
| P0-3 | **确认** | 代码已允许“公共挂载课软删后，共享题仍可供有活跃选课的学生练习”，但缺少正向列表与提交回归。 |
| P1-1 | **确认，但问题性质写错** | `@cache_result("course:detail:{course_id}")` 默认把 `Session` 写进键，返回值又含 ORM `Course`，JSON 写缓存会失败并降级；当前不是“可能脏 5 分钟”，而是缓存基本未生效。 |
| P1-2 | **确认** | `/quiz/submit` 使用 `get_current_user`，服务仅在 `role == "student"` 时做可见性校验；教师/管理员可提交任意活跃题并读取答案与解析。 |
| P1-3 | **确认** | 管理端公共课程、公共资料、单题/批量删题使用伪造的 `AuthUser(id="admin")`；题目更新没有审计，贡献日志不能替代操作审计。 |
| P1-4 | **不是当前缺陷** | `create_announcement` 明确只要求题目来自未删除的全站题库，错误文案也写“题目必须来自全站题库”；作业提交按作业 `question_ids` 授权。应补稳定事实和测试，不应未经决策收紧。 |
| P1-5 | **降级为前端 UX 缺口** | 后端允许教师编辑自己创建、挂载课已软删的题；前端仍保留旧 `course_id`，并不会必然保存失败，但下拉中没有该课程名称，容易显示空值并误导改挂。 |
| P1-6 | **确认** | 教师和管理员删课文案没有说明共享题不随课删除。 |
| P1-7 | **确认，方案已定** | 新增独立管理员共享题库入口，题库管理不再依赖活跃公共课；公共课程页移除题库维护标签，只保留课程、阶段、资料和贡献快照。 |
| P1-8 | **确认，并需扩大** | 除原列场景外，必须增加 SQLite 外键开启测试、完整课程入站 FK 场景和真实 MySQL 条件验证。 |
| P1-9 | **确认** | 多份旧设计/计划仍宣称删课前必须 rehome 或活跃题必须挂在未删课程，需加废止横幅。 |
| P2-1 | **确认但优先级低** | `_format_course` 当前正式路由都传入全站题数，危险回落暂未走到；仍应删除回落，避免未来误用。 |
| P2-2 | **确认** | `_format_course_batch` 的资料数、班级数没有过滤 `deleted_at`，与单条详情不一致。 |
| P2-3 | **确认** | 错题本查询课程名时过滤软删课程，导致历史公共挂载题显示“未命名课程”。 |
| P2-4 / P2-7 | **确认，方案已定** | 学生自由练习改为一个全局可见题池；课程卡片只承载作业，不再展示重复的全站题数或伪课程统计。 |
| P2-5 | **确认** | 教师标签筛选只过滤后端返回的当前页，并把 `total` 改成当前页命中数，分页总数失真。 |
| P2-6 | **部分确认** | 管理端接口已返回挂载课程 ID/名称，但页面未展示；接口没有返回 `created_by/creator_name`，因此无法展示添加人。 |
| P2-8 | **确认，且比原文更严重** | `rehome_questions_before_course_delete` 已无调用，继续保留 no-op 只会掩盖旧调用；`Course.questions` 仍有 `delete-orphan`；`question_bank_root_course_id` 还在启动兼容逻辑中批量改写并阻断删公共课。 |
| P2-9 | **确认** | 教师题目列表 OpenAPI 仍写“按课程筛选”，实际 `course_id` 已忽略。 |
| P3-1 | **确认** | `list_questions.teacher_id` 不参与查询，只在路由格式化时用于 `is_owner`，服务参数可移除。 |
| P3-2 | **确认，优先级应上调** | 管理端文案宣称“永久移除、删除作业引用和答题记录、不可恢复”，实际是软删除；被未删除作业引用时会拒绝，答题记录和 `question_ids` 都保留。 |
| P3-3 | **确认，优先级应上调** | `question_bank_root_course_id` 不是无害遗留：`schema_compat` 每次启动会重写，公共课删除服务会据此阻断删除。 |
| P3-4 | **确认但本轮后置** | `_cleanup_question` 每题扫描全部带 `question_ids` 的作业，属于到期清理性能债；先完成清理正确性，再按真实数据量优化。 |
| P3-5 | **确认** | 手工新增和导入的重复题提示口径不同，可统一为“题库中已存在相同题目”。 |

## 三、可以直接实施的事项

以下事项已经确认，可在用户明确“开始写代码”或“执行计划”后按顺序实施，无需再次拍板。

### D1 课程 cleanup 安全护栏

- 在 `soft_delete_cleanup_service.py` 增加课程清理前置引用检查，至少覆盖 `questions.course_id`、课程自引用、非同批班级/资料/作业、阶段、课时/进度和作品。
- 存在阻断引用时，不执行 `DELETE courses`，保持课程和引用数据原样；当前资源计入失败/延后并写中文审计，列出阻断类型和数量。
- 这是迁移落地前的止损措施；完成已确认的引用脱钩迁移和真实 MySQL 验证后，才能签署“30 天课程清理”验收。
- 从 `Course.questions` 移除 `delete-orphan`，正式清理继续显式编排，防止未来误用 `db.delete(course)` 时级联误删共享题。

### D2 学生练习回归与角色边界

- 增加“公共挂载课软删后题目仍可列出并提交”“私有挂载课软删后不可见”“无活跃选课不可提交”三组回归。
- `/quiz/submit` 以及同属学生域的 history/stats 路由统一使用 `require_role("student")`；服务层对非学生提交再做一次 403 防御。
- 教师若未来需要预览答案，另开明确的教师预览能力，不复用学生作答接口。

### D3 管理端真实审计身份

- 公共课程、公共资料、共享题目单删/批删服务统一接收真实 `AuthUser`，禁止构造 `id="admin"`。
- 管理员共享题目创建、更新写 `question.create` / `question.update` 审计；贡献日志继续保留，二者职责不同。
- 审计列表展示 `action_name`、`resource_type_name`，内部筛选码仍保留英文，不把英文内部码直接作为主要界面文案。

### D4 共享题库直接一致性修复

- 为教师 HTTP 编辑“挂载课已软删、题目自身未删且创建人为本人”补回归；不改 `course_id` 时必须成功。
- 创建、管理员创建、教师导入、管理员导入撞上“挂载课已软删但题目仍活跃”的同题干时，继续判重或计入 skip。
- 停止 `schema_compat` 对 `question_bank_root_course_id` 的启动批量改写；删除公共课时不再因该历史字段阻断。
- 新建公共课程时不再写入 `question_bank_root_course_id`；现有非空值只作为待退役兼容数据，不再参与业务判断。
- 删除无调用的 root/rehome 运行时 helper；数据库列先兼容保留，不在本批次 DROP。
- 删除管理员 `_format_course` 的本课题数回落；正式接口始终传入全站活跃题数。

### D5 前端与接口可直接修复

- 教师题库编辑已删挂载课题时，显示“挂载课程（已删除）”只读项；用户主动选择活跃自有课时才改挂。
- 教师题库新增明确的 `tag` 查询参数，后端在分页前过滤并返回正确总数；不得继续只过滤当前页。
- 管理题目 DTO 返回挂载状态和添加人，为独立管理员题库页面与旧兼容接口复用；题目挂载课已删时显示“原挂载课程（已删除）”。
- 管理员删题文案改为“移入回收站；被未删除作业引用时不能删除；历史答题记录保留”，删除成功 Toast 改为“已移入回收站”。
- 教师/管理员删课确认明确“共享题目不随课程删除、不转挂”；资料、班级、作业的影响按当前真实级联语义描述。
- 错题本课程名为空时显示“原挂载课程已删除”，不再显示“未命名课程”。
- 课程批量列表的资料数、班级数补 `deleted_at IS NULL`。

### D6 缓存事实纠正

- 移除 `get_course_detail` 的 ORM 返回值缓存装饰器及与其不匹配的失效假象，保持直接查询。
- 同步移除 `list_public_courses` 这类直接返回 ORM 列表的同类无效装饰器；其他服务的缓存统一留到总体路线图第三阶段审计。
- 本计划不新增 `shared:question:count`，不使用 `KEYS course:detail:*` 建立新的大范围失效策略。
- 后续缓存阶段必须先定义可 JSON DTO、权限维度键、精确失效和 Redis 降级测试，再启用缓存。

### D7 文档与接口说明收口

- 在旧 rehome/活跃所属课文档顶部加“已废止”横幅并指向 2026-07-15 规格与本计划。
- `project-map.md` 增加稳定事实：“作业可从全站活跃共享题库选题；提交授权依赖作业 `question_ids`”。
- 修正题目列表 OpenAPI：`course_id` 是兼容参数，不再按课程筛选。
- 清理“题目永久删除、删除答题记录、必须转挂、所属课程决定题目所有权”等错误文案。

## 四、已确认的产品与数据方案

### J1 引用脱钩：课程可以按期物理清理

采用原推荐方案 J1-B，不使用延期墓碑或系统锚点课。

#### J1.1 外键分类

| 引用 | 已确认处理 |
|---|---|
| `Question.course_id` | 改为可空并使用 `ON DELETE SET NULL`；题目仍按自身 `deleted_at` 判断活跃性 |
| `Project.course_id` | 保持可空并统一为 `ON DELETE SET NULL`；作品继续按自身生命周期保留 |
| `Course.source_course_id` | 保持可空并使用 `ON DELETE SET NULL`；公共源清理后教师副本仍保留，停止后续同步 |
| `Course.question_bank_root_course_id` | 退役业务语义，迁移时清空；本计划保留空列，DROP 另立计划，不再参与启动或删除判断 |
| `Material.course_id` | 改为可空并使用 `ON DELETE SET NULL`；同批资料按课程流程快照并删除，先前独立软删且未到 6 个月的资料保留并脱钩，异常活跃资料阻断清理 |
| `Class.course_id`、`Announcement.course_id` | 同批或已到自身期限的子资源先快照并显式删除；存在活跃记录或尚未到期的非同批记录时阻断父课程清理 |
| `CourseStage.course_id` | 随课程清理；先处理阶段下资料的 `stage_id`，再删除阶段 |
| `Lesson`、`CourseProgress`、`LessonProgress` | 产品已下线，作为历史表随课程最终清理；需要保留的统计先进入历史快照 |

#### J1.2 迁移与兼容

- `Question.course_id`、`Material.course_id`、前后端 `QuestionOut.course_id` 和 TypeScript `Question.course_id` 改为可空；正常教师新增题目和新增资料仍必须选择活跃自有课程。
- `Question` 新增 `mount_course_name_snapshot`；兼容迁移先从现有课程回填，创建时有挂载课程就写课程名，课程改名时同步更新，课程 cleanup 前再次固化。
- 题目展示新增 `mount_course_state: "active" | "soft_deleted" | "purged" | "none"`：软删课程仍读取原行，物理清理后使用名称快照，独立题库创建且从未挂课的题显示“独立题库”。
- 已脱钩资料保持软删除状态；管理员恢复时必须提交新的活跃 `target_course_id`，否则返回“原课程已清理，请选择恢复到的课程”，不得恢复出活跃无课程资料。
- `schema_compat.py` 对真实 MySQL 幂等调整列空值和外键；不得只改 ORM。执行前读取实际约束名，删除旧约束后用稳定约束名重建。
- 迁移前备份数据库；迁移后用 `information_schema` 核对 nullability、`DELETE_RULE` 和孤儿记录数量。
- cleanup 首先保留 D1 预检；只有允许置空或已显式清理的引用处理完毕后，才执行课程 Core DELETE。

### J2 独立管理员共享题库入口

采用原推荐方案 J2-A。

- 新建 `backend/app/api/v1/routes/admin_question_bank_routes.py`，注册到 `backend/app/api/v1/__init__.py`，统一前缀为 `/api/admin/question-bank`。
- 新建 `backend/app/services/admin_question_bank_service.py`，承接全站题库列表、新增、编辑、单删、批删、导入模板、导入和贡献记录聚合。
- 新建 `frontend/src/api/adminQuestionBank.ts` 与 `frontend/src/views/admin/AdminQuestionBank.vue`。
- 前端路由新增 `/admin/question-bank`，`AdminLayout.vue` 导航新增“共享题库”。
- `AdminPublicCourses.vue` 移除题库维护标签；公共课程详情只维护课程说明、阶段和资料。
- 新增/导入题目时“原始挂载课程”改为可选：可选择活跃公共课程作为来源快照，也可不选择，直接创建 `course_id = NULL` 的全站共享题。
- `QuestionContributionLog.public_course_id` 改为可空；贡献记录列表改为全站聚合，保留 `public_course_name` 快照，无课程上下文时显示“独立题库”。
- 旧 `/api/admin/public-courses/{course_id}/questions*` 路由在本计划中保留，内部委托新服务并返回 `Deprecation: true` 与新接口 `Link` 响应头；前端上线后不再调用，删除旧路由另立计划。

### J3 学生全局可见题池

采用原推荐方案 J3-A。

- 新增学生接口 `GET /api/quiz/questions`，返回当前学生可见的全局活跃题池，支持 `ids`、`random`，始终隐藏答案和解析。
- `/api/quiz/stats` 继续作为全局题池统计；`/api/quiz/stats/{course_id}` 在本计划中保留并委托全局统计，返回弃用响应头，前端不再调用。
- 新增前端路由 `/practice/quiz`，自由练习不再要求 `courseId`；旧 `/practice/quiz/:courseId` 重定向到新路由并保留 `random/question_ids` 查询参数。
- `PracticeView.vue` 的自由练习区只显示一个全局入口和一组题数/完成数/正确率；课程卡片只显示各课程作业状态。
- `PracticeQuizView.vue` 自由练习改调全局题池接口；作业模式继续使用 `announcementId`，两条路径不混用。
- `useQuizDraft` 的自由练习草稿键从课程 ID 改为固定全局作用域；作业仍不恢复自由练习草稿。
- 学生没有活跃选课时全局题池返回空列表、统计返回 0，页面显示“你尚未加入课程”；可见集合保持“全部公共挂载共享题、空挂载共享题 + 学生所有活跃私有课题”。

### 作业选题范围

现有代码已经明确采用“教师可从全站活跃共享题库选题，学生提交按作业 `question_ids` 授权”。本轮按现状补文档和回归即可。只有用户希望改成课程私有题池时，才另开产品设计，不在本计划内顺手收紧。

## 五、实施任务

### Task 1：先锁住当前工作区共享题库修复

**文件：**

- 测试：`backend/tests/test_quiz_submit_scope.py`
- 测试：`backend/tests/test_soft_delete_read_filters.py`
- 测试：`backend/tests/test_public_question_contribution.py`
- 测试：`backend/tests/test_public_course_delete.py`

- [x] 写公共挂载课软删后的列表/提交正向测试，并先确认旧代码会失败、当前工作区代码通过。
- [x] 写教师 HTTP 编辑已删挂载课自有题测试。
- [x] 写教师/管理员新增与导入撞已删挂载同题干的测试。
- [x] 运行上述测试，保存通过数量；不得修改当前工作区已存在断言的业务方向。

### Task 2：建立 cleanup 外键安全门

**文件：**

- 修改：`backend/app/services/soft_delete_cleanup_service.py`
- 修改：`backend/app/models/entities.py`
- 测试：`backend/tests/test_soft_delete_cleanup.py`
- 条件验证：真实 MySQL 测试或只读外键矩阵记录

- [x] 为 cleanup 专用测试引擎开启 SQLite 外键，先证明现有“课程删掉、独立资料仍保留”的测试在真实 FK 语义下不成立。
- [x] 建立 `courses` 入站外键矩阵，逐项标注 `RESTRICT`、`CASCADE`、`SET NULL` 和服务层处理方式。
- [x] 写题目、教师副本、非同批资料/班级/作业、阶段、课时/进度、作品阻断测试。
- [x] 实现只读预检和中文失败审计；阻断时课程与引用均保留。
- [x] 移除 `Course.questions` 的 `delete-orphan`，验证 ORM 删除不会误删共享题。
- [x] 迁移完成前只签署“不会误删、失败可解释”；完成 J1 引用脱钩和真实 MySQL 验证后再签署“30 天后可以物理删除”。

### Task 3：收紧学生角色并补真实审计

**文件：**

- 修改：`backend/app/api/v1/routes/quiz_routes.py`
- 修改：`backend/app/services/quiz_service.py`
- 修改：`backend/app/api/v1/routes/admin_public_course_routes.py`
- 修改：`backend/app/services/admin_public_course_service.py`
- 修改：`backend/app/services/audit_service.py`
- 修改：`frontend/src/views/admin/AdminAuditLogs.vue`
- 测试：`backend/tests/test_quiz_submit_scope.py`
- 测试：`backend/tests/test_030405_management_systems.py`
- 测试：`backend/tests/test_public_question_contribution.py`

- [x] 写教师/管理员调用学生 quiz 路由返回 403 的失败测试。
- [x] 路由改为学生角色依赖，服务拒绝 `role != "student"` 的提交。
- [x] 写管理员 A 删除、管理员 B 查询审计的测试，断言 `user_id` 为真实操作者。
- [x] 公共资源删除服务统一接收 `AuthUser`，移除所有伪造 `id="admin"`。
- [x] 为管理员共享题创建/更新补审计并登记中文动作映射。
- [x] 审计前端改用服务已返回的中文名称字段。

### Task 4：退役旧题库根并修正接口数据

**文件：**

- 修改：`backend/app/db/schema_compat.py`
- 修改：`backend/app/services/question_bank_service.py`
- 修改：`backend/app/services/question_contribution_service.py`
- 修改：`backend/app/services/admin_public_course_service.py`
- 修改：`backend/app/api/v1/routes/admin_public_course_routes.py`
- 修改：`backend/app/services/course_response_service.py`
- 修改：`backend/app/api/v1/routes/question_routes.py`
- 修改：`backend/app/schemas/common.py`
- 测试：`backend/tests/test_public_course_delete.py`
- 测试：`backend/tests/test_soft_delete_read_filters.py`

- [x] 写“活跃课程仍引用历史 root 时，公共课仍可软删”的失败测试。
- [x] 停止启动时重写 `question_bank_root_course_id`，移除软删除阻断和无调用的 root/rehome helper；本轮保留列，不 DROP。
- [x] 管理题目 DTO 增加添加人和 `mount_course_state`；挂载课程名称保留历史展示。
- [x] 删除 `_format_course` 的本课题数回落。
- [x] 批量课程资料/班级统计过滤软删。
- [x] 修正 OpenAPI 和服务参数，删除“按课程筛选”假语义。

### Task 5：修复前端文案、筛选和已删挂载展示

**文件：**

- 修改：`frontend/src/api/question.ts`
- 修改：`frontend/src/api/adminPublicCourse.ts`
- 修改：`backend/app/services/question_service.py`
- 修改：`backend/app/api/v1/routes/question_routes.py`
- 修改：`frontend/src/views/teacher/TeacherQuestions.vue`
- 修改：`frontend/src/views/teacher/TeacherCourses.vue`
- 修改：`frontend/src/views/admin/AdminPublicCourses.vue`
- 修改：`frontend/src/views/ProfileView.vue`
- 测试：`frontend/tests/teacher-question-bank-static.test.mjs`
- 测试：`frontend/tests/admin-question-batch-delete-static.test.mjs`
- 测试：`frontend/tests/copy-consistency-static.test.mjs`
- 测试：扩展后端题库分页测试，断言标签过滤后的 `items/total/page/page_size`
- 测试：新增或扩展错题课程名静态测试

- [x] 标签筛选改为后端分页参数，总数来自后端过滤结果。
- [x] 教师编辑弹窗显示已删挂载课，不强迫改挂。
- [x] 单删、批删、一键删除全部统一为回收站真实语义。
- [x] 教师/管理员删课确认说明共享题不随课删除、不转挂。
- [x] 错题本显示“原挂载课程已删除”。

### Task 6：移除无效 ORM 缓存，功能缓存继续后置

**文件：**

- 修改：`backend/app/services/question_service.py`
- 修改：`backend/app/services/admin_public_course_service.py`
- 测试：新增课程详情/公共课程列表在 Redis 可用和不可用时的等价结果测试

- [x] 写测试证明当前 ORM 返回值无法 JSON 缓存且键包含会话对象。
- [x] 移除两个无效缓存装饰器和对应误导性精确失效调用。
- [x] 验证 Redis 不可用或未启动时课程详情、公共课程列表结果一致。
- [x] 在总体路线图第三阶段记录剩余缓存装饰器审计，不在本任务发明新键体系。

### Task 7：实施课程引用脱钩迁移

**文件：**

- 新建：`docs/superpowers/specs/2026-07-17-course-purge-reference-detachment-design.md`
- 修改：`backend/app/models/entities.py`
- 修改：`backend/app/db/schema_compat.py`
- 修改：`backend/app/services/soft_delete_cleanup_service.py`
- 修改：`backend/app/services/soft_delete_service.py`
- 修改：`backend/app/api/v1/routes/admin_routes.py`
- 修改：`backend/app/services/admin_public_course_service.py`
- 修改：`backend/app/services/question_service.py`
- 修改：`backend/app/services/quiz_service.py`
- 修改：`backend/app/schemas/common.py`
- 修改：`frontend/src/api/question.ts`
- 修改：`frontend/src/api/admin.ts`
- 修改：`frontend/src/views/admin/AdminRecycleBin.vue`
- 测试：`backend/tests/test_soft_delete_cleanup.py`
- 测试：`backend/tests/test_quiz_submit_scope.py`
- 测试：`backend/tests/test_schema_compat.py`

- [x] 用真实 MySQL `information_schema.KEY_COLUMN_USAGE` 导出所有指向 `courses.id` 的外键，写入引用脱钩设计文档并与第四节矩阵逐项对应。
- [x] 写 `Question.course_id = NULL` 后题库列表、查重、管理员维护、学生可见性和提交仍成功的失败测试；教师新增题和新增资料仍必须选择活跃自有课程。
- [x] 写公共源课程物理删除后 `Course.source_course_id = NULL`、作品课程置空、历史 root 清空的失败测试。
- [x] 写已脱钩资料直接恢复失败、选择活跃目标课程后恢复成功的测试。
- [x] 更新 ORM、Pydantic 和 TypeScript 可空类型，新增 `Question.mount_course_name_snapshot` 和 `mount_course_state` 展示字段；迁移中先按现有 `course_id` 回填名称快照。
- [x] 在 `schema_compat.py` 幂等清理历史 root 值，重建已确认的 `SET NULL` 外键；外键名从 inspector/`information_schema` 获取，不写死未知生产约束名。
- [x] `Course.questions`、`Course.materials` 改为依赖数据库 `SET NULL` 的被动删除关系，不保留会物理删除子项的 ORM delete cascade。
- [x] cleanup 按矩阵先快照、显式删除同批子资源、置空允许脱钩引用，再删除课程。
- [x] 扩展资料恢复请求和回收站弹窗：仅当 `Material.course_id IS NULL` 时要求选择目标课程，并在同一事务中校验课程、重新挂载和恢复。
- [x] 在开启外键的 SQLite 和真实 MySQL 各执行一次课程 cleanup；断言课程删除、共享题/作品保留、引用置空、历史快照存在。

### Task 8：建立独立管理员共享题库

**文件：**

- 新建：`backend/app/api/v1/routes/admin_question_bank_routes.py`
- 新建：`backend/app/services/admin_question_bank_service.py`
- 新建：`frontend/src/api/adminQuestionBank.ts`
- 新建：`frontend/src/views/admin/AdminQuestionBank.vue`
- 修改：`backend/app/api/v1/__init__.py`
- 修改：`backend/app/models/entities.py`
- 修改：`backend/app/db/schema_compat.py`
- 修改：`backend/app/schemas/common.py`
- 修改：`backend/app/api/v1/routes/admin_public_course_routes.py`
- 修改：`backend/app/services/admin_public_course_service.py`
- 修改：`backend/app/services/question_contribution_service.py`
- 修改：`frontend/src/router/index.ts`
- 修改：`frontend/src/views/admin/AdminLayout.vue`
- 修改：`frontend/src/views/admin/AdminPublicCourses.vue`
- 测试：新建 `backend/tests/test_admin_question_bank.py`
- 测试：新建 `frontend/tests/admin-question-bank-static.test.mjs`
- 测试：扩展 `frontend/tests/copy-consistency-static.test.mjs`

- [x] 写没有任何活跃公共课程时，管理员仍可列表、新增 `course_id = NULL` 题目、编辑和软删除的失败测试。
- [x] 写独立题库导入、`public_course_id = NULL` 贡献记录聚合、真实审计身份和分页筛选测试。
- [x] 实现 `/api/admin/question-bank` 的列表、创建、编辑、单删、批删、模板、导入和贡献记录接口。
- [x] 旧公共课程题库路由委托新服务，并增加 `Deprecation: true` 与指向新接口的 `Link` 响应头；本计划不删除旧路由。
- [x] 实现管理员独立题库页面、API 封装、路由和导航；页面包含题干、题型、标签、星级、添加人、原挂载课程和回收站删除操作。
- [x] 从 `AdminPublicCourses.vue` 移除题库维护和题库贡献标签，确保公共课程删除不影响管理员题库入口。

### Task 9：改造学生全局自由练习

**文件：**

- 修改：`backend/app/api/v1/routes/quiz_routes.py`
- 修改：`backend/app/services/quiz_service.py`
- 修改：`frontend/src/api/quiz.ts`
- 修改：`frontend/src/router/index.ts`
- 修改：`frontend/src/views/PracticeView.vue`
- 修改：`frontend/src/views/PracticeQuizView.vue`
- 修改：`frontend/src/composables/useQuizDraft.ts`
- 测试：`backend/tests/test_quiz_submit_scope.py`
- 测试：`frontend/tests/practice-quiz-flow-static.test.mjs`
- 测试：新增 `frontend/tests/global-practice-pool-static.test.mjs`

- [x] 写 `/api/quiz/questions` 只返回学生全局可见题、隐藏答案解析、支持 `ids/random` 的失败测试。
- [x] 写空挂载共享题可见、无活跃选课返回空池和零统计、私有未选课题不可见的测试。
- [x] 实现全局题池接口并让 `/quiz/stats` 使用同一可见 ID 子查询；旧课程统计接口委托全局统计并返回弃用响应头，本计划不删除旧接口。
- [x] 新增 `/practice/quiz` 路由；旧课程练习路由重定向并保留 `random/question_ids` 查询参数。
- [x] `PracticeView` 只保留一个自由练习面板，调用 `getQuizStats()`；课程区域只显示作业状态。
- [x] `PracticeQuizView` 自由模式调用全局题池，作业模式保持原接口；草稿键改为固定 `quiz-draft:global-practice`，旧课程草稿不迁移也不读取。
- [x] 验证多个选课课程下页面只有一个自由练习入口，题数、完成数和准确率不再按课程重复。

### Task 10：文档与完整验收

**文件：**

- 修改：`docs/superpowers/project-map.md`
- 修改：旧 rehome/活跃所属课 specs/plans 的废止横幅
- 修改：`backend/docs/项目修改记录.md`
- 条件修改：`AGENTS.md`（只写最终稳定事实，不写临时任务状态）

- [x] 更新稳定事实、废止旧文档、记录实际测试与服务器影响。
- [x] 运行受影响后端测试、前端静态测试、`npm run type-check`、`npm run build`。
- [x] 在真实 MySQL 或等价临时库执行外键开启的 cleanup 验证；未执行时明确写“未验证”，不得签字。
- [x] 运行 `git diff --check`。
- [x] 代码修改完成后运行 `graphify update .`；`graphify-out/` 不进入暂存范围。

## 六、验收门

### 6.1 直接修复批次验收

1. 公共挂载课软删后，共享题仍可供有活跃选课学生列出和提交；私有软删挂载不可见。
2. 非学生不能调用学生 quiz 路由获取答案/解析。
3. 管理端删除审计记录真实用户；题目创建/更新可追溯。
4. 管理删题文案与软删除、作业引用拒绝、历史答题保留一致。
5. 教师可维护自己创建的已删挂载课题目；标签分页总数正确。
6. 历史题库根不再影响启动数据或阻断公共课软删除。
7. 课程 cleanup 遇到任何未处理外键时不误删、可审计、可重试。
8. 无效 ORM 缓存已移除，未提前引入第三阶段缓存方案。

### 6.2 整体闭环验收

只有 Task 7–9 的已确认方案全部完成，旧接口兼容行为有测试，且真实 MySQL cleanup 验证通过，才可声称“共享题库删课语义闭环”。SQLite 测试、前端静态测试或文档完成不能替代该验收门。

## 七、建议执行顺序

```text
先保留并验证当前工作区“删课不隐藏共享题”修复
    -> Task 1 回归锁定
    -> Task 2 cleanup 安全护栏
    -> Task 3 学生角色 + 真实审计
    -> Task 4 历史 root/接口数据
    -> Task 5 前端文案与筛选
    -> Task 6 移除无效缓存
    -> Task 7 课程引用脱钩迁移
    -> Task 8 独立管理员共享题库
    -> Task 9 学生全局自由练习
    -> Task 10 文档与完整验收
```

## 八、服务器部署影响

| 内容 | 服务器影响 |
|---|---|
| 计划审查阶段仅修改本文档 | **不需要服务器修改** |
| Task 1 仅测试 | 不需要服务器修改 |
| Task 2–4、Task 6 后端 | 服务器拉代码并重启后端；D1 护栏和历史 root 退役本身不迁库 |
| Task 5 前端 | 服务器拉代码、重新构建并部署前端静态资源 |
| J1 引用脱钩（已确认） | 发布前备份数据库；执行真实 MySQL 外键/空值迁移；拉代码并重启后端；同步重建前端 |
| J2 独立管理员题库入口（已确认） | 执行 `question_contribution_logs.public_course_id` 可空迁移；拉代码、重启后端、重新构建前端；不新增业务表 |
| J3 学生全局练习改造（已确认） | 拉代码、重启后端、重新构建前端；不迁库 |

所有实现批次都必须在 `backend/docs/项目修改记录.md` 写明实际部署动作；未部署统一写“尚未执行”。

## 九、明确不做

- 不在本计划中实现完整题目标签化、标签必填或删除 `Question.course_id` 的全部迁移。
- 不恢复 rehome 作为删课主路径。
- 不提前实施 Redis 多 worker、一致性限流、启动锁或压测。
- 不借共享题库任务重构无关学生页面、回收站全站 UX 或其他资源生命周期。
- 不把当前通过的 SQLite 清理测试当作真实 MySQL 验收结果。
