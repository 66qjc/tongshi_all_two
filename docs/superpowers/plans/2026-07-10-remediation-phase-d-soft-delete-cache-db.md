# 软删除、Redis 与数据库兼容修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐七类资源软删除与关联恢复、修复 Redis 缓存和多 worker 限流边界，并让既有 MySQL 安全获得哈希和索引升级。

**Architecture:** 正式删除入口统一进入软删除服务且不提前破坏关联数据；缓存只包围权限明确的 JSON DTO；忘记密码失败计数在 Redis 开启时共享；启动初始化在同一个 MySQL 命名锁内执行 `create_all`、兼容 DDL、哈希回填和索引补齐。

**Tech Stack:** FastAPI、SQLAlchemy、MySQL、SQLite、Redis、Vue 3、pytest。

**Design:** `docs/superpowers/specs/2026-07-10-code-review-remediation-design.md`

---

### Task 1: 七类资源统一软删除并保留关联完整性

**Files:**
- Modify: `backend/app/services/soft_delete_service.py`
- Modify: `backend/app/services/class_service.py:177-220`
- Modify: `backend/app/services/announcement_service.py:147-158`
- Modify: `backend/app/services/material_service.py:134-143`
- Modify: `backend/app/services/project_service.py:245-260`
- Modify: `backend/app/services/question_service.py:168-190`
- Modify: `backend/app/services/admin_public_course_service.py:120-335`
- Modify: `backend/app/services/file_service.py:90-210`
- Modify: `backend/app/api/v1/routes/admin_routes.py:240-445`
- Modify: `backend/app/api/v1/routes/admin_public_course_routes.py`
- Modify: `frontend/src/api/admin.ts`
- Modify: `frontend/src/views/admin/AdminRecycleBin.vue`
- Modify: `backend/tests/test_030405_management_systems.py`
- Create: `backend/tests/test_soft_delete_relationships.py`
- Create: `backend/tests/test_soft_deleted_file_access.py`

- [ ] **Step 1: 写主记录、关联记录和文件权限失败测试**

新增 `test_user_soft_delete_and_restore`、`test_course_soft_delete_and_restore`、`test_class_soft_delete_and_restore`、`test_announcement_soft_delete_and_restore`、`test_project_soft_delete_and_restore`、`test_material_soft_delete_and_restore`、`test_question_soft_delete_and_restore`，全部通过真实正式删除入口执行。每个用例都断言主记录仍存在且 `deleted_at` 非空、普通列表不可见、回收站可见、恢复后重新可见。用户使用字符串 ID `T900`，恢复和彻底删除不得返回 422。

关联完整性测试在删除前记录数量和 ID：班级的 `AnnouncementClass/AnnouncementRead/TaskCompletion`，作品的 `ProjectImage/ProjectLike`，资料的 `StoredFile/MaterialPreview`，用户的作品/答题/班级关系。软删除和恢复后这些记录必须保持不变，不能只恢复主表。文件测试断言资料/作品软删除后原签名 URL 和新申请均不可访问，恢复后重新可访问。

题目测试创建引用该题的未删除作业，管理员删除必须返回 400“题目已被作业引用，无法删除”；不得清理 `Announcement.question_ids` 或历史 `QuizAttempt`。无作业引用时才可软删除并恢复。

- [ ] **Step 2: 运行并确认当前物理删除关联**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_030405_management_systems.py backend/tests/test_soft_delete_relationships.py backend/tests/test_soft_deleted_file_access.py -q`

Expected: FAIL，班级、公告、资料、作品、用户或题目仍被物理删除，且软删除文件仍可访问。

- [ ] **Step 3: 增加安全主键转换**

```python
def _coerce_resource_id(model, resource_id: str):
    python_type = model.__mapper__.primary_key[0].type.python_type
    try:
        return python_type(resource_id)
    except (TypeError, ValueError):
        raise BusinessException(400, "资源 ID 格式不正确")
```

恢复和彻底删除路由的 `resource_id` 改为 `str`，服务查询前转换；前端 `DeletedResourceItem.id` 使用 `string | number`，构建 URL 时编码字符串值。

- [ ] **Step 4: 各正式入口只做软删除**

每个服务先执行现有归属与业务约束，再调用 `soft_delete(db, item, operator, cascade=False, action=动作名)` 并只提交一次；动作名精确使用 `user.delete`、`course.delete`、`class.delete`、`announcement.delete`、`project.delete`、`material.delete`、`question.delete`。禁止在调用软删除前执行关联表 `delete()`：

- 班级仍保留“有学生不能删除”规则，但不能删除公告关联、已读、完成记录或孤立公告。
- 公告保留已读和完成记录；资料保留文件与预览；作品保留图片和点赞；用户保留全部业务数据。
- 管理员公共课程使用阶段 A 的课程级联软删除，保留阶段和同步引用以便恢复；公共资料与公共题目同样进入回收站。
- 题目删除前查询所有未删除公告的 `question_ids`，存在引用即拒绝；教师端删除继续固定返回 403，只有管理员可删除。
- 管理员“彻底删除”只允许回收站中的记录，继续执行物理删除。

- [ ] **Step 5: 恢复只恢复同一删除批次**

课程恢复只恢复 `deleted_at/deleted_by` 与课程删除批次相同的班级、资料和公告，不恢复阶段 A 已转挂的共享题目。单资源恢复只清理自身删除标记，因为关联数据从未物理删除。审计日志记录恢复的子资源数量。

- [ ] **Step 6: 补齐活跃过滤和文件权限过滤**

本轮涉及的登录、课程、班级、公告、资料、作品、题目、通知目标、进度分析和管理员列表统一过滤 `deleted_at IS NULL`。`file_service.py` 中项目、资料、课程和预览权限查询也必须过滤软删除；回收站/恢复/彻底删除是唯一允许读取已删除资源的业务入口。

- [ ] **Step 7: 运行软删除回归和前端构建**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_030405_management_systems.py backend/tests/test_soft_delete_relationships.py backend/tests/test_soft_deleted_file_access.py backend/tests/test_teacher_student_delete_scope.py backend/tests/test_project_course_scope.py backend/tests/test_public_course_delete.py -q`

Run: `npm run build --prefix frontend`

Expected: PASS。

### Task 2: 统一题干 SHA-256 并升级全部旧 MD5

**Files:**
- Create: `backend/app/services/question_hash_service.py`
- Modify: `backend/app/models/entities.py:257`
- Modify: `backend/app/services/question_service.py:20-175,341-430`
- Modify: `backend/app/services/admin_public_course_service.py`
- Modify: `backend/app/db/schema_compat.py`
- Modify: `backend/tests/test_question_duplicate_candidates.py`
- Modify: `backend/tests/test_question_import_skip.py`
- Modify: `backend/tests/test_schema_compat.py`

- [ ] **Step 1: 写编辑、导入、MD5 升级和候选规则失败测试**

断言编辑题干后哈希同步；教师创建、管理员创建和 Excel 导入使用相同哈希；旧库夹具同时包含 NULL、空字符串和 32 位 MD5，升级后全部变成与当前题干匹配的 64 位 SHA-256；同题干不同答案仍进入现有候选比较，不被哈希唯一约束提前拒绝。

- [ ] **Step 2: 运行并确认当前 MD5/空值不一致**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_question_duplicate_candidates.py backend/tests/test_question_import_skip.py backend/tests/test_schema_compat.py -q`

Expected: FAIL，编辑后保留旧哈希，或旧 MD5 不会被升级。

- [ ] **Step 3: 提取唯一规范化函数**

```python
def normalize_question_stem(stem: str) -> str:
    return " ".join((stem or "").strip().split()).casefold()


def compute_stem_hash(stem: str) -> str:
    return hashlib.sha256(normalize_question_stem(stem).encode("utf-8")).hexdigest()
```

创建、编辑、管理员创建和导入全部调用该函数；模型注释改为 SHA-256。哈希只作为候选索引，最终重复判断继续比较题型、选项和答案。

- [ ] **Step 4: 分批重算旧哈希**

兼容层补列后按主键分批读取 `id, stem, stem_hash`，对 NULL、空值或长度不为 64 的旧记录重算；首次部署会覆盖现有 32 位 MD5，后续启动跳过已升级行。使用绑定参数批量更新，不拼接题干；SQLite 与 MySQL 使用同一 Python 函数。

- [ ] **Step 5: 运行题库和兼容回归**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_question_duplicate_candidates.py backend/tests/test_question_import_skip.py backend/tests/test_schema_compat.py backend/tests/test_public_question_contribution.py -q`

Expected: PASS。

### Task 3: 重写 Redis 缓存边界并保持权限隔离

**Files:**
- Modify: `backend/.env.example`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/db/redis_client.py`
- Modify: `backend/app/core/cache.py`
- Modify: `backend/app/services/admin_public_course_service.py`
- Modify: `backend/app/services/class_service.py`
- Modify: `backend/app/services/question_service.py`
- Modify: `backend/app/services/course_response_service.py`
- Modify: `backend/app/api/v1/routes/admin_public_course_routes.py`
- Modify: `backend/app/api/v1/routes/course_routes.py`
- Create: `backend/tests/test_cache_behavior.py`
- Create: `backend/tests/test_cache_authorization.py`

- [ ] **Step 1: 写稳定键、DTO、权限、失效和降级失败测试**

FakeRedis 测试断言两个不同 Session 对同一业务请求生成同一键；缓存值能被标准 JSON 编解码且不含 ORM；`REDIS_ENABLED=false` 时不构造客户端；首次连接故障后冷却期不重复连接；模式失效只用 `scan_iter`。公共课程列表、课程详情、班级列表分别覆盖命中、更新失效、删除失效和故障降级。

权限测试先由课程所有者预热私有课程详情，再让其他教师读取同一课程，结果仍须 404；管理员、学生和教师的 DTO 不能因为共用 `course_id` 键而串数据。

- [ ] **Step 2: 运行并确认当前键和 ORM 缓存失败**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_cache_behavior.py backend/tests/test_cache_authorization.py -q`

Expected: FAIL，当前键包含 Session 地址、公共课程列表缓存 ORM，课程详情可能绕过权限检查，模式失效使用 `keys()`。

- [ ] **Step 3: 增加开关、命名空间和失败冷却**

配置增加 `REDIS_ENABLED=false`、`REDIS_FAILURE_COOLDOWN=30`、`REDIS_KEY_PREFIX=tongshi:v1`。未启用时所有缓存函数直接执行原函数；连接或命令异常后使用 `time.monotonic()` 记录下一次尝试时间，冷却期不再获取客户端。测试提供重置客户端和冷却状态的显式 helper，避免测试串扰。

- [ ] **Step 4: 只缓存最终 JSON DTO**

三个缓存场景使用显式键：

- 公共课程列表：`public-courses:all`，服务直接返回包含同步摘要的 `list[dict]`，管理员路由不再接收 `Course` ORM 后二次格式化。
- 班级列表：`classes:teacher={teacher_id}:course={course_id|all}:keyword={normalized}`，现有 `list[dict]` 保持不变。
- 课程详情：`course-detail:id={course_id}:role={role}:user={user_id}`；学生访问校验和教师所有权校验必须在缓存命中前完成，缓存的是 `build_course_detail()` 最终字典。路由和 `course_response_service` 同步改为 DTO 契约。

所有更新/软删除操作按精确前缀失效。模式失效通过 `scan_iter(match=pattern, count=100)` 增量遍历并分批删除，禁止调用 `keys()`。

- [ ] **Step 5: 运行缓存和消费者回归**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_cache_behavior.py backend/tests/test_cache_authorization.py backend/tests/test_course_pagination.py backend/tests/test_search_optimization.py backend/tests/test_public_course_delete.py -q`

Expected: PASS。

### Task 4: 忘记密码失败计数支持多 worker

**Files:**
- Modify: `backend/app/services/auth_service.py:80-145`
- Modify: `backend/tests/test_forgot_password_rate_limit.py`
- Modify: `backend/tests/test_cache_behavior.py`

- [ ] **Step 1: 写 Redis 共享计数和降级失败测试**

两个模拟 worker 使用独立 Python 内存状态但同一个 FakeRedis，累计第 6 次失败必须被限流；成功验证删除计数键；Redis 禁用或故障时回退现有进程内计数且认证流程可用。测试不得在 Redis 中存储答案、密码或完整请求体。

- [ ] **Step 2: 运行并确认当前计数按进程分裂**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_forgot_password_rate_limit.py backend/tests/test_cache_behavior.py -q`

Expected: FAIL，两个进程状态可以分别获得完整尝试次数。

- [ ] **Step 3: 使用 Redis 原子计数**

Redis 开启时使用命名空间键 `auth:forgot-failures:{user_id}`，通过事务管道或 Lua 原子执行首次 `INCR` 并设置 5 分钟 TTL；成功验证后删除键。Redis 关闭或进入失败冷却时保留现有内存实现。部署文档明确：多 worker 部署必须启用 Redis，关闭 Redis 只保证单 worker 限流语义。

- [ ] **Step 4: 运行限流和认证回归**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_forgot_password_rate_limit.py backend/tests/test_auth.py backend/tests/test_cache_behavior.py -q`

Expected: PASS。

### Task 5: 在启动锁内执行建表、兼容 DDL、哈希和索引升级

**Files:**
- Modify: `backend/main.py:30-38`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/db/schema_compat.py`
- Modify: `backend/app/models/entities.py`
- Modify: `backend/tests/test_schema_compat.py`
- Modify: `backend/tests/test_search_optimization.py`
- Create: `backend/tests/test_mysql_schema_compat_integration.py`

- [ ] **Step 1: 写旧表索引、锁覆盖和真实 MySQL 失败测试**

SQLite 旧结构夹具不创建新索引，运行初始化后用 `inspect(engine).get_indexes()` 核对目标。mock 测试断言 `GET_LOCK` 发生在 `Base.metadata.create_all()` 之前，`RELEASE_LOCK` 在成功和异常路径都执行。真实 MySQL 测试仅在 `TEST_MYSQL_URL` 存在且数据库名以 `_test` 结尾时运行，两个并发初始化连接最终只产生一套索引并释放命名锁。

- [ ] **Step 2: 运行并确认既有表未补索引、create_all 位于锁外**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_schema_compat.py backend/tests/test_search_optimization.py backend/tests/test_mysql_schema_compat_integration.py -q`

Expected: FAIL，旧表缺少目标索引，且当前 `main.py` 在锁外先执行 `create_all()`。

- [ ] **Step 3: 增加安全幂等索引助手和精确清单**

`_ensure_index()` 只接受代码内常量，使用方言 identifier preparer 引用表、索引和列名；创建后清理/重建 inspector 缓存。精确补齐：

- `ix_quiz_attempt_user_ann(user_id, announcement_id)`、`ix_quiz_attempt_user_question(user_id, question_id)`。
- `ix_lesson_progress_user_course(user_id, course_id)`、`ix_lesson_progress_status(status)`。
- `ix_questions_stem_hash(stem_hash)`。
- 七类软删除表各自的 `deleted_at`、`deleted_by` 单列索引。
- `student_notifications` 的 `user_id/category/priority/expires_at/is_read` 单列索引，以及 `ix_student_notifications_user_read_category(user_id, is_read, category)`。
- `audit_logs` 的 `user_id/action/resource_type/resource_id/status/created_at` 单列索引。

新增复合索引同步声明到 ORM `__table_args__`，`stem_hash` 继续是普通索引而非唯一约束。

- [ ] **Step 4: 把 create_all 和兼容层放进同一个 MySQL 锁**

新增 `initialize_database_schema(engine, metadata)`：MySQL 连接先执行 `SELECT GET_LOCK('tongshi_schema_compat', :timeout)`，成功后用同一连接执行 `metadata.create_all(bind=conn)`、字段/表兼容、题干哈希升级和索引补齐，`finally` 释放锁；SQLite 跳过命名锁。锁超时读取 `SCHEMA_COMPAT_LOCK_TIMEOUT`，默认 300 秒；获取失败明确终止启动，不能让 worker 带半升级结构运行。`main.py` 只调用该初始化入口，不再在锁外单独 `create_all()`。

- [ ] **Step 5: 运行兼容和后端全量测试**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_schema_compat.py backend/tests/test_search_optimization.py backend/tests/test_mysql_schema_compat_integration.py -q`

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests -q --basetemp=tmp/pytest-phase-d`

Expected: 本地业务测试全部 PASS；未配置 `TEST_MYSQL_URL` 时真实 MySQL 用例明确 SKIP，不能宣称 MySQL 已验证。

### Task 6: 隔离环境部署验收、文档和图谱

**Files:**
- Modify: `backend/docs/项目修改记录.md`
- Modify: `docs/superpowers/project-map.md`
- Modify: `docs/superpowers/redis-integration-guide.md`
- Modify: `docs/superpowers/specs/2026-07-09-03-soft-delete-mechanism.md`
- Modify: `docs/superpowers/specs/2026-07-10-code-review-remediation-design.md`

- [ ] **Step 1: Redis 双模式验收**

`REDIS_ENABLED=false` 运行课程、班级、认证和缓存测试。真实 Redis 只允许使用专门的 `TEST_REDIS_URL`、非生产 DB 和本次随机 `REDIS_KEY_PREFIX`；禁止 `FLUSHDB`，清理时只 SCAN/删除本次前缀。验证命中、失效、故障冷却和两个 worker 的忘记密码共享计数。

- [ ] **Step 2: MySQL 测试库升级验收**

只对名称以 `_test` 结尾且已备份的 `TEST_MYSQL_URL` 执行真实集成测试；核对旧 MD5 升级率、目标索引、命名锁释放、两个并发初始化和阶段 B 的并发课时上报。若没有测试库凭据，明确记录“真实 MySQL 未验证”，不能在本地 SQLite 结果上推断通过。

- [ ] **Step 3: 完整前后端验收**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests -q --basetemp=tmp/pytest-final`

Run: `$failed = $false; Get-ChildItem frontend/tests/*.test.mjs | ForEach-Object { & node $_.FullName; if ($LASTEXITCODE -ne 0) { $failed = $true } }; if ($failed) { exit 1 }`

Run: `npm run build --prefix frontend`

Expected: 全部业务测试、静态测试和构建通过，仅允许已记录且不影响功能的构建体积警告。

- [ ] **Step 4: 更新稳定事实和服务器部署步骤**

明确服务器需要备份 MySQL 与上传目录、拉代码、安装/确认 Redis 依赖、按部署形态设置 `REDIS_ENABLED`、单实例完成兼容升级、核对锁和索引后再启动多 worker、重启后端并重新构建前端；不需要调整 Nginx。多 worker 若不启用 Redis，忘记密码限流不满足共享安全语义，禁止按多 worker 验收通过。

- [ ] **Step 5: 更新图谱并核对边界**

Run: `graphify update .`

Run: `git diff --check`

Expected: 图谱增量更新成功且 diff 无空白错误。`graphify-out/` 是忽略产物，不暂存；本计划不自动执行 `git add`、提交或推送。
