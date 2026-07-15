# 七类资源统一软删除与业务数据规则实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将课程、班级、资料、作业、作品、用户、题目的正式删除统一为可恢复软删除，并在 30 天或 6 个自然月后由每周清理任务生成历史快照后安全物理清理。

**Architecture:** 保留现有 Routes -> Services -> Models 分层，在 `soft_delete_service.py` 旁增加一份七类资源固定策略清单和独立历史快照服务；各正式删除服务只负责权限/业务约束并调用统一软删除入口。自动清理只调用受限的内部清理服务，先把会受外键影响的答题、完成、已读、班级关系、点赞、文件预览等事实写入无外键快照，再按依赖顺序物理清理。题目脱离课程、标签创建和按标签练习另立规格，不在本计划实现。

**Tech Stack:** FastAPI、SQLAlchemy、SQLite/MySQL、pytest、Vue 3、Element Plus、现有本地存储适配器。

---

## 文件边界

### 新增文件

- `backend/app/services/soft_delete_policy.py`：七类资源的中文名称、保留期、课程级联名单和恢复规则；只包含固定清单，不提供泛化资源框架。
- `backend/app/services/history_snapshot_service.py`：生成和读取无外键历史快照，保存中文展示字段和必要 ID。
- `backend/app/services/soft_delete_cleanup_service.py`：按到期时间逐项执行快照、文件引用检查、物理清理和中文审计；可重复调用。
- `backend/scripts/run_soft_delete_cleanup.py`：命令行入口，供现有外部每周调度在周日 03:00 调用，不改服务器配置。
- `backend/tests/test_soft_delete_lifecycle.py`：七类正式删除、管理员恢复、权限和保留期规则。
- `backend/tests/test_soft_delete_snapshots.py`：历史快照和清理后报表读取。
- `backend/tests/test_soft_delete_cleanup.py`：到期边界、失败重试、文件引用和清理命令入口。

### 修改文件

- `backend/app/models/entities.py`：新增无外键 `history_snapshots` 表模型；补齐快照事实去重索引；不删除现有七类 `deleted_at/deleted_by` 字段。
- `backend/app/db/schema_compat.py`：为既有数据库幂等创建历史快照表和索引。
- `backend/app/services/soft_delete_service.py`：接入固定策略、字符串 ID 转换、批次恢复、禁止公开 purge、中文返回 DTO。
- `backend/app/services/class_service.py`、`announcement_service.py`、`material_service.py`、`project_service.py`、`question_service.py`：移除正式删除入口中的关联物理删除，调用统一软删除；保留原权限和业务限制。
- `backend/app/services/admin_public_course_service.py`：公共课程、公共资料、公共题目删除改为软删除；课程不再转挂/清理题目或破坏阶段和同步引用。
- `backend/app/api/v1/routes/admin_routes.py`：教师账号删除改为软删除；恢复 ID 接收字符串；公开 purge 路由固定拒绝；回收站和审计输出中文字段。
- `backend/app/api/v1/routes/admin_public_course_routes.py`、`class_routes.py`、`announcement_routes.py`、`material_routes.py`、`course_routes.py`、`question_routes.py`、`teacher_routes.py`：保持路由权限，接入新服务返回和错误文案。
- `backend/app/services/announcement_service.py`、`task_service.py`、`quiz_service.py`、`teacher_service.py`、`portfolio_service.py`、`public_learning_service.py`、`question_bank_service.py`、`file_service.py`、`access_control_service.py`：补齐活跃资源过滤，并在教师历史报表中合并快照数据。
- `backend/app/services/audit_service.py`：保留内部动作代码兼容筛选，增加中文 `action_name`、中文详情和导出列；系统自动清理记录使用系统任务身份。
- `frontend/src/api/admin.ts`、`frontend/src/views/admin/AdminRecycleBin.vue`：移除提前彻底删除按钮，显示保留截止时间、中文动作和清理状态。
- `backend/tests/test_030405_management_systems.py`、`test_public_course_delete.py`、`test_material_file_acceleration.py`、`test_soft_delete_read_filters.py`：更新旧物理删除断言并加入恢复、快照和文件引用契约。

## Task 1：先写固定策略与快照表失败测试

**Files:**
- Create: `backend/app/services/soft_delete_policy.py`
- Create: `backend/app/services/history_snapshot_service.py`
- Modify: `backend/app/models/entities.py`
- Modify: `backend/app/db/schema_compat.py`
- Test: `backend/tests/test_soft_delete_snapshots.py`

- [ ] **Step 1: 写策略和快照的失败测试**

在 `test_soft_delete_snapshots.py` 中固定测试数据和断言：

```python
def test_resource_retention_policy_uses_calendar_months():
    deleted_at = datetime(2026, 1, 15, 3, 0, tzinfo=BEIJING_TZ)
    assert retention_deadline(deleted_at, "courses") == datetime(2026, 2, 14, 3, 0, tzinfo=BEIJING_TZ)
    assert retention_deadline(deleted_at, "materials") == datetime(2026, 7, 15, 3, 0, tzinfo=BEIJING_TZ)


def test_snapshot_has_no_foreign_keys_and_preserves_chinese_payload(db_session):
    snapshot = capture_snapshot(
        db_session,
        resource_type="announcements",
        resource_id=7,
        fact_type="答题记录",
        fact_id=11,
        snapshot_kind="答题记录",
        payload={"作业标题": "第一次作业", "题目ID": 3, "学生姓名": "测试学生"},
    )
    db_session.commit()
    assert snapshot.resource_id == "7"
    assert snapshot.payload["作业标题"] == "第一次作业"
    assert snapshot.__table__.foreign_keys == set()


def test_snapshot_query_survives_source_row_delete(db_session):
    question = db_session.query(Question).first()
    capture_snapshot(
        db_session,
        resource_type="questions",
        resource_id=question.id,
        fact_type="答题记录",
        fact_id=21,
        snapshot_kind="答题记录",
        payload={"题干": "历史题目"},
    )
    db_session.delete(question)
    db_session.commit()
    assert list_snapshots(db_session, resource_type="questions", resource_id=question.id)
```

断言当前实现失败，因为策略、快照服务和表模型均不存在。

- [ ] **Step 2: 运行失败测试**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_soft_delete_snapshots.py -q`

Expected: FAIL，提示策略函数、快照模型或 `capture_snapshot` 未定义。

- [ ] **Step 3: 添加固定策略清单**

实现 `soft_delete_policy.py` 中的固定映射，不接受运行时注册：

```python
RESOURCE_POLICIES = {
    "users": ResourcePolicy("用户", "days", 30, (), "self"),
    "courses": ResourcePolicy("课程", "days", 30, ("classes", "materials", "announcements"), "same_batch"),
    "classes": ResourcePolicy("班级", "days", 30, (), "self"),
    "announcements": ResourcePolicy("作业", "days", 30, (), "self"),
    "projects": ResourcePolicy("作品", "months", 6, (), "self"),
    "materials": ResourcePolicy("资料", "months", 6, (), "self"),
    "questions": ResourcePolicy("题目", "months", 6, (), "self"),
}
```

`retention_deadline(deleted_at, resource_type)` 复用 `app.core.timezone_utils.BEIJING_TZ`，使用标准库 `calendar.monthrange` 计算自然月，使用 `timedelta(days=30)` 计算 30 天期限，不新增第三方依赖。`resource_type` 不在七类清单中时抛出中文业务异常。

- [ ] **Step 4: 添加无外键历史快照模型和兼容建表**

在 `entities.py` 增加 `HistorySnapshot`：`id`、`resource_type`、`resource_id`、`fact_type`、`fact_id`、`snapshot_kind`、`cleanup_batch_id`、`payload(JSON)`、`captured_at`、`created_at`，所有资源 ID 和事实 ID 使用字符串；不声明任何外键。增加 `(resource_type, resource_id)`、`(fact_type, fact_id)` 唯一索引、`cleanup_batch_id`、`captured_at` 索引。`schema_compat.py` 为旧 MySQL/SQLite 幂等创建表和索引，刷新 inspector 缓存。

- [ ] **Step 5: 实现快照写入/读取并验证通过**

`capture_snapshot()` 接收 `fact_type` 和 `fact_id`，按二者幂等，且只 `add/flush` 不提交；`list_snapshots()` 按批次和资源类型返回不可变字典；payload 的键使用中文业务字段，必要关联 ID 使用 `用户ID`、`题目ID` 等中文键。运行同一测试命令，Expected: PASS。

- [ ] **Step 6: 提交独立基础变更**

```bash
git add backend/app/models/entities.py backend/app/db/schema_compat.py backend/app/services/soft_delete_policy.py backend/app/services/history_snapshot_service.py backend/tests/test_soft_delete_snapshots.py
git commit -m "feat: 增加软删除策略与历史快照基础"
```

## Task 2：统一普通删除、课程批次恢复与用户删除

**Files:**
- Modify: `backend/app/services/soft_delete_service.py`
- Modify: `backend/app/services/class_service.py`
- Modify: `backend/app/services/announcement_service.py`
- Modify: `backend/app/services/material_service.py`
- Modify: `backend/app/services/project_service.py`
- Modify: `backend/app/services/question_service.py`
- Modify: `backend/app/services/admin_public_course_service.py`
- Modify: `backend/app/api/v1/routes/admin_routes.py`
- Test: `backend/tests/test_soft_delete_lifecycle.py`
- Test: `backend/tests/test_030405_management_systems.py`

> **进度（2026-07-15）**：核心入口与公共课程/资料/题目删除入口均已改为软删除；生命周期 + 管理 + 公共删除相关回归已通过。Step 1–7 代码与测试已完成；**未执行 git commit**（按当前会话“未提交任何改动”约定）。

- [x] **Step 1: 为七类正式入口写失败测试**

每项测试必须调用真实 API/服务入口而不是直接赋值 `deleted_at`：

```python
def assert_soft_deleted_and_restorable(db_session, client, admin_token, delete_request, resource_type, resource_id):
    assert delete_request()["code"] == 0
    row = db_session.get(RESOURCE_MODELS[resource_type], resource_id)
    assert row is not None and row.deleted_at is not None
    assert client.get(f"/api/admin/deleted/{resource_type}", headers=auth_header(admin_token)).json()["data"]["total"] >= 1
    assert client.post(f"/api/admin/restore/{resource_type}/{resource_id}", headers=auth_header(admin_token)).json()["code"] == 0
    assert db_session.get(RESOURCE_MODELS[resource_type], resource_id).deleted_at is None
```

覆盖课程、班级、作业、资料、作品、用户字符串 ID、题目；同时断言教师不能访问回收站，管理员不能提前 purge。

- [x] **Step 2: 运行失败测试并记录现状**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_soft_delete_lifecycle.py backend/tests/test_030405_management_systems.py -q`

Expected: FAIL，班级、作业、资料、作品、用户、题目仍物理删除或恢复 ID 仍被整数路径参数拒绝。

- [x] **Step 3: 扩展统一软删除服务**

在 `soft_delete_service.py` 增加 `_coerce_resource_id(model, resource_id: str)`，根据主键 `python_type` 转换并用中文 400 错误；`soft_delete()` 默认 `cascade=False`，只有课程按策略级联班级、资料、作业并共享同一 UTC 时间。`restore_resource()` 使用策略的 `same_batch` 规则，返回 `恢复子资源数量`；删除、恢复动作保留内部代码，同时写入中文详情。

- [x] **Step 4: 改造六类服务删除入口**

各服务保留原权限检查和业务限制，只移除关联 `delete()`：

- `class_service.delete_class()` 保留“有学生不能删除”，不删除 `AnnouncementClass`、`AnnouncementRead`、`TaskCompletion`。
- `announcement_service.delete_announcement()` 软删作业，不删除已读/完成/答题。
- `material_service.delete_material()` 软删资料，不删除文件/预览。
- `project_service.delete_project()` 软删作品，不删除图片/点赞。
- `question_service.delete_question()` 先查询所有 `Announcement.deleted_at IS NULL` 的 `question_ids`，命中即 400；不删除答题记录，不修改 JSON 题目列表。
- `admin_public_course_service` 的公共课程和公共资料/题目删除改走统一入口；课程不再 `rehome_questions_before_course_delete()`、不清理阶段和同步引用。

每个入口只在最外层提交一次，动作代码分别为 `class.delete`、`announcement.delete`、`material.delete`、`project.delete`、`question.delete`、`course.delete`。

- [x] **Step 5: 改造管理员教师删除**

`admin_routes.delete_teacher()` 删除现有 `force` 物理级联逻辑，改为查询活跃教师后调用 `soft_delete(db, teacher, current_user, action="user.delete")`；不删除课程、作品、答题、班级关系、文件或密码重置记录。`force` 查询参数移除，旧客户端额外传入时不改变软删除语义。用户软删后登录和文件访问必须返回中文错误。

- [x] **Step 6: 处理回收站路由与提前 purge**

恢复路由的 `resource_id` 改为 `str`，路径构造使用 URL 编码。`DELETE /api/admin/purge/...` 保留兼容路由但始终抛出 `BusinessException(403, "资源仍在保留期，不能提前彻底删除")`；只有内部清理服务可调用 `_purge_expired_resource()`。

- [x] **Step 7: 运行生命周期回归并提交**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_soft_delete_lifecycle.py backend/tests/test_030405_management_systems.py backend/tests/test_public_course_delete.py -q`

Expected: PASS；每类资源可恢复，用户使用字符串 ID，题目被未删除作业引用时返回 400，关联事实数量和 ID 不变。

```bash
git add backend/app/services/soft_delete_service.py backend/app/services/class_service.py backend/app/services/announcement_service.py backend/app/services/material_service.py backend/app/services/project_service.py backend/app/services/question_service.py backend/app/services/admin_public_course_service.py backend/app/api/v1/routes/admin_routes.py backend/tests/test_soft_delete_lifecycle.py backend/tests/test_030405_management_systems.py backend/tests/test_public_course_delete.py
git commit -m "feat: 统一七类资源软删除入口"
```

## Task 3：补齐正常读取、统计和文件访问过滤

**Files:**
- Modify: `backend/app/services/announcement_service.py`
- Modify: `backend/app/services/task_service.py`
- Modify: `backend/app/services/quiz_service.py`
- Modify: `backend/app/services/teacher_service.py`
- Modify: `backend/app/services/portfolio_service.py`
- Modify: `backend/app/services/public_learning_service.py`
- Modify: `backend/app/services/question_bank_service.py`
- Modify: `backend/app/services/access_control_service.py`
- Modify: `backend/app/services/file_service.py`
- Modify: `backend/app/api/v1/routes/file_routes.py`
- Test: `backend/tests/test_soft_delete_read_filters.py`
- Test: `backend/tests/test_material_file_acceleration.py`

- [ ] **Step 1: 增加漏网读路径的失败测试**

覆盖公告列表/详情/未读数、教师学生统计、作品列表、题库、课程访问、资料/作品文件申请；每个测试先创建活跃记录，再软删资源，断言普通服务返回空或 404，旧签名 URL 返回 401/404。

- [ ] **Step 2: 运行现有过滤回归**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_soft_delete_read_filters.py backend/tests/test_material_file_acceleration.py -q`

Expected: 至少公告、作品统计或用户关联路径失败，作为实现基线。

- [ ] **Step 3: 统一服务查询条件**

所有普通查询加入自身 `deleted_at.is_(None)`；跨资源读取同时过滤父资源：作业要求作业/班级/课程活跃，资料要求资料/课程活跃，作品要求作品/用户/课程活跃，题目只要求题目自身活跃并移除旧课程删除条件。教师统计只统计活跃学生、班级、作业，历史数据留到 Task 5 的快照读取。

- [ ] **Step 4: 加强文件权限二次校验**

`file_service.py` 的资料、作品、预览、课程和用户权限查询均过滤软删；`file_routes.py` 在签名 URL 解码后重新查活跃用户和资源，不能信任签发时状态。文件被软删后旧 URL 和新申请都失败，恢复后重新申请成功。

- [ ] **Step 5: 运行过滤与文件回归并提交**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_soft_delete_read_filters.py backend/tests/test_material_file_acceleration.py backend/tests/test_quiz_submit_scope.py -q`

Expected: PASS，正常读取不暴露已删除资源，公共题目不再因旧课程状态隐藏。

```bash
git add backend/app/services/announcement_service.py backend/app/services/task_service.py backend/app/services/quiz_service.py backend/app/services/teacher_service.py backend/app/services/portfolio_service.py backend/app/services/public_learning_service.py backend/app/services/question_bank_service.py backend/app/services/access_control_service.py backend/app/services/file_service.py backend/app/api/v1/routes/file_routes.py backend/tests/test_soft_delete_read_filters.py backend/tests/test_material_file_acceleration.py
git commit -m "fix: 补齐软删除正常读取与文件过滤"
```

## Task 4：实现到期快照、物理清理和每周命令入口

**Files:**
- Create: `backend/app/services/soft_delete_cleanup_service.py`
- Create: `backend/scripts/run_soft_delete_cleanup.py`
- Modify: `backend/app/services/soft_delete_service.py`
- Modify: `backend/app/services/audit_service.py`
- Test: `backend/tests/test_soft_delete_cleanup.py`
- Test: `backend/tests/test_soft_delete_snapshots.py`

- [ ] **Step 1: 写到期、失败重试和文件引用失败测试**

测试使用注入的北京时间 `now`，不得修改系统时间：

```python
def test_cleanup_runs_only_after_retention_and_next_sunday(db_session):
    deleted_at = datetime(2026, 1, 15, 3, 0, tzinfo=BEIJING_TZ)
    course = seed_deleted_course(db_session, deleted_at)
    assert cleanup_expired_resources(db_session, now=datetime(2026, 2, 14, 2, 59, tzinfo=BEIJING_TZ)) == {"cleaned_count": 0}
    result = cleanup_expired_resources(db_session, now=datetime(2026, 2, 15, 3, 0, tzinfo=BEIJING_TZ))
    assert result["cleaned_count"] == 1


def test_cleanup_failure_is_audited_and_retryable(db_session, monkeypatch):
    seed_expired_material(db_session)
    def fail_file_delete(*_args, **_kwargs):
        raise OSError("文件删除失败")

    monkeypatch.setattr(
        "app.services.soft_delete_cleanup_service._delete_file_if_unreferenced",
        fail_file_delete,
    )
    result = cleanup_expired_resources(db_session, now=FIXED_SUNDAY)
    assert result["failed_count"] == 1
    assert "文件删除失败" in latest_audit(db_session).details["失败原因"]
    assert db_session.query(Material).filter(Material.deleted_at.isnot(None)).count() == 1
```

同时测试题目/作业/用户的答题、完成、已读、班级关系、点赞、图片和预览都先生成快照。

- [ ] **Step 2: 运行失败测试**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_soft_delete_cleanup.py -q`

Expected: FAIL，因为没有到期清理服务、快照批次或失败审计实现。

- [ ] **Step 3: 实现到期判断和独立事务**

`cleanup_expired_resources(db, now=None)` 先将 `now` 转为 `BEIJING_TZ`，仅在 `weekday() == 6` 且本地时间不早于 03:00 时执行；遍历七类策略，使用 `retention_deadline <= now` 且资源仍 `deleted_at IS NOT NULL`。每个资源创建独立 savepoint/事务批次，失败只回滚当前资源。批次 ID 使用 UUID 字符串，写入快照和审计详情。

- [ ] **Step 4: 实现快照顺序和物理清理顺序**

按资源显式编排，不依赖 ORM cascade：

1. 课程：快照班级关系、作业关联/已读/完成/答题、资料预览和文件引用；只清理 `deleted_at` 与课程相同且 `deleted_by` 与课程相同的同批班级/资料/作业及其事实，保留此前单独删除的子资源，再清理课程。
2. 作业：快照作业关联/已读/完成/答题，再删关联事实和作业。
3. 题目：快照答题记录和作业题目上下文，再删答题事实和题目。
4. 用户：快照作品、答题、班级关系、点赞、通知和审计所需姓名，再删用户关联事实与用户；作品本身按作品保留期单独处理。
5. 班级：快照选课、作业关联/已读/完成，再删关联事实和班级。
6. 资料/作品：快照文件与预览/图片/点赞，再删关联行和主记录。

每个快照不保存 ORM 对象，只保存中文 JSON 字段和必要 ID。物理文件删除前调用 `collect_file_references()`，只有没有活跃资源和历史快照引用时才删除对象存储文件及 `StoredFile` 行。

- [ ] **Step 5: 写中文自动清理审计并提供命令入口**

成功记录“系统自动清理成功”，详情包含 `到期时间`、`历史快照数量`、`文件处理结果`；失败记录“系统自动清理失败”，包含 `失败原因`、`下次重试时间`。`run_soft_delete_cleanup.py` 只负责创建数据库会话、调用服务、输出中文摘要和返回非零退出码，不改服务器配置或启动服务。

- [ ] **Step 6: 运行清理回归并提交**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_soft_delete_cleanup.py backend/tests/test_soft_delete_snapshots.py -q`

Expected: PASS；30 天和 6 个自然月边界正确，失败下周可重试，手动 purge 不参与清理。

```bash
git add backend/app/services/soft_delete_cleanup_service.py backend/scripts/run_soft_delete_cleanup.py backend/app/services/soft_delete_service.py backend/app/services/audit_service.py backend/tests/test_soft_delete_cleanup.py backend/tests/test_soft_delete_snapshots.py
git commit -m "feat: 增加软删除到期快照与自动清理"
```

## Task 5：让教师历史报表读取快照并统一中文审计输出

**Files:**
- Modify: `backend/app/services/history_snapshot_service.py`
- Modify: `backend/app/services/teacher_service.py`
- Modify: `backend/app/services/task_service.py`
- Modify: `backend/app/services/portfolio_service.py`
- Modify: `backend/app/services/audit_service.py`
- Modify: `backend/app/api/v1/routes/admin_routes.py`
- Test: `backend/tests/test_soft_delete_snapshots.py`
- Test: `backend/tests/test_030405_management_systems.py`

- [ ] **Step 1: 写清理后历史报表失败测试**

先创建作业、答题、完成记录和用户，再执行到期清理；调用教师成绩列表、完成报告、学生作品/练习统计和导出，断言仍有历史数值，且响应不含可跳转的已清理详情 URL。

- [ ] **Step 2: 实现快照聚合读取**

在 `history_snapshot_service.py` 提供 `history_attempt_totals()`、`history_completion_rows()`、`history_project_rows()`，统一把快照 JSON 映射为现有报表 DTO；服务只读，不重新创建业务 ORM 行。教师报表把活跃表聚合与快照聚合相加，去重键使用 `(快照批次, 事实 ID)`。

- [ ] **Step 3: 添加中文审计字段**

在 `audit_service.py` 增加固定 `ACTION_LABELS`，`_format_log()` 返回 `action_name`，导出表头改为中文动作名称、资源类型名称、状态名称和错误信息；内部 `action` 代码保留，确保现有 `?action=course.delete` 筛选不破坏。新详情键统一使用中文。

- [ ] **Step 4: 运行历史和审计回归并提交**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_soft_delete_snapshots.py backend/tests/test_030405_management_systems.py -q`

Expected: PASS；清理后教师仍可查看历史成绩/完成情况，审计展示中文且保留必要 ID。

```bash
git add backend/app/services/history_snapshot_service.py backend/app/services/teacher_service.py backend/app/services/task_service.py backend/app/services/portfolio_service.py backend/app/services/audit_service.py backend/app/api/v1/routes/admin_routes.py backend/tests/test_soft_delete_snapshots.py backend/tests/test_030405_management_systems.py
git commit -m "feat: 保留清理后的历史成绩与中文审计"
```

## Task 6：收口管理员回收站前端和全量验收

**Files:**
- Modify: `frontend/src/api/admin.ts`
- Modify: `frontend/src/views/admin/AdminRecycleBin.vue`
- Modify: `backend/docs/项目修改记录.md`
- Modify: `backend/tests/test_soft_delete_lifecycle.py`
- Modify: `frontend/tests/admin-question-batch-delete-static.test.mjs`
- Create: `frontend/tests/admin-recycle-bin-soft-delete-static.test.mjs`

- [ ] **Step 1: 写回收站 UI 失败契约**

静态测试断言：资源 ID 类型为 `string | number`；API 只有列表/恢复调用；组件显示中文资源类型、删除时间、保留截止时间和恢复按钮；源码不包含 `purge` 请求、`彻底删除`按钮或提前清理确认弹窗。

- [ ] **Step 2: 实现前端收口**

`admin.ts` 的恢复 URL 使用 `encodeURIComponent(String(id))`；删除 `purge` API 导出。`AdminRecycleBin.vue` 根据资源类型显示“用户/课程/班级/作业/资料/作品/题目”，计算并展示截止时间，恢复失败使用后端中文消息，不添加教师恢复入口。

- [ ] **Step 3: 运行前端静态检查**

Run: `node frontend/tests/admin-recycle-bin-soft-delete-static.test.mjs`

Expected: PASS。

- [ ] **Step 4: 执行后端全量和前端构建**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests -q --basetemp=tmp/pytest-soft-delete-final`

Expected: 既有业务测试全部通过；未配置真实 MySQL 的集成测试只能明确 SKIP。

Run: `npm.cmd run type-check --prefix frontend`

Expected: PASS。

Run: `npm.cmd run build --prefix frontend`

Expected: PASS，允许已有体积警告，不允许编译错误。

- [ ] **Step 5: 检查范围和文档一致性**

Run: `git diff --check -- backend/app backend/tests frontend/src frontend/tests backend/docs/项目修改记录.md`

检查 `docs/superpowers/2026-07-15-project-consistency-assessment.md`、`docs/superpowers/plans/2026-07-10-remediation-phase-d-soft-delete-cache-db.md` 和本设计的事实没有互相冲突；确认没有修改服务器配置、缓存、多 worker、题目标签化或无关前端页面。

- [ ] **Step 6: 提交最终实现并记录验证**

```bash
git add frontend/src/api/admin.ts frontend/src/views/admin/AdminRecycleBin.vue frontend/tests/admin-recycle-bin-soft-delete-static.test.mjs backend/docs/项目修改记录.md
git commit -m "test: 完成七类软删除生命周期验收"
```

在 `backend/docs/项目修改记录.md` 追加中文验证记录：七类删除/恢复、自动清理、历史快照、文件权限、中文审计、后端测试和前端构建结果；不记录未执行的服务器部署或真实 MySQL 验证。

## 验收门

只有以下条件全部满足才可声称完成：

- 七类资源正式删除均只产生软删除，课程只级联班级/资料/作业。
- 教师不能读回收站或恢复，管理员可恢复，公开手动 purge 永远拒绝。
- 30 天和 6 个自然月边界正确，每周日清理逐项执行并可重试。
- 物理清理前生成无外键历史快照，清理后教师历史成绩和完成情况仍可读。
- 删除期间关联事实、文件和预览规则符合设计，旧文件 URL 立即失效，恢复后可重新申请。
- 正常列表、详情、统计、练习、作业和文件访问不暴露已删除资源。
- 管理员审计展示中文动作/详情，必要资源 ID 保留。
- 后端全量测试、前端静态测试、类型检查和构建均有新鲜命令输出；真实 MySQL 未配置时明确标注未验证。
