# 权限与核心数据正确性修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复作业完成误判、密码与 JWT 失效、教师通知越权、课程删除误伤共享题库四类高风险问题。

**Architecture:** 保持 Routes -> Services -> Models 分层。内部辅助函数只修改会话并 `flush`，最外层业务服务沿用项目现有模式只提交一次并负责异常回滚；权限判断在写入前完成，所有修复先用失败测试复现。后端改密 Token 轮换与前端接收新 Token 在本阶段一起交付。

**Tech Stack:** FastAPI、SQLAlchemy、Pydantic、python-jose、pytest、SQLite 内存测试库。

**Design:** `docs/superpowers/specs/2026-07-10-code-review-remediation-design.md`

---

### Task 1: 修复作业完成记录提前创建

**Files:**
- Modify: `backend/tests/test_assignment_practice_flow.py:200-241`
- Modify: `backend/tests/test_assignment_scoring.py`
- Modify: `backend/app/services/quiz_service.py:19-58,238-293`
- Modify: `backend/app/services/task_service.py:111-137`

- [x] **Step 1: 固化部分答题不能完成的失败测试**

在 `test_assignment_requires_all_questions_answered_before_completion` 中，在提交第一题后增加数据库断言：

```python
assert db_session.query(TaskCompletion).filter(
    TaskCompletion.announcement_id == announcement_id,
    TaskCompletion.user_id == "2025001",
).count() == 0
```

- [x] **Step 2: 运行测试并确认按预期失败**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_assignment_practice_flow.py::test_assignment_requires_all_questions_answered_before_completion -q`

Expected: FAIL，部分答题后 `TaskCompletion` 数量实际为 1。

- [x] **Step 3: 把评分更新改为“全部答完后才创建完成记录”**

在 `quiz_service.py` 增加并使用：

```python
def _answered_question_ids(db: Session, user_id: str, announcement_id: int) -> set[int]:
    return {
        row[0]
        for row in db.query(QuizAttempt.question_id)
        .filter(
            QuizAttempt.user_id == user_id,
            QuizAttempt.announcement_id == announcement_id,
        )
        .distinct()
        .all()
    }


def _assignment_is_fully_answered(db: Session, user_id: str, announcement: Announcement) -> bool:
    question_ids = set(announcement.question_ids if isinstance(announcement.question_ids, list) else [])
    return bool(question_ids) and question_ids.issubset(
        _answered_question_ids(db, user_id, announcement.id)
    )
```

`_update_assignment_score()` 在 `False` 时只返回计算结果，不创建 `TaskCompletion`；在 `True` 时创建或更新完成记录，而且函数内只允许 `flush`。`submit_answer()` 添加 `QuizAttempt` 后先 `flush`，调用评分辅助函数后只 `commit` 一次；捕获 `SQLAlchemyError` 时 `rollback` 并返回现有中文业务错误，提交后再 `refresh(attempt)`。这样即使只答了一题，答题事实也会提交，但完成记录不会创建。

- [x] **Step 4: 让完成接口始终先校验再返回已有记录**

把 `task_service.mark_completed()` 中 `existing` 的提前返回移动到题目完整性校验之后：

```python
question_ids = set(ann.question_ids if isinstance(ann.question_ids, list) else [])
if question_ids:
    answered_ids = _answered_question_ids_for_assignment(db, user_id, announcement_id)
    if not question_ids.issubset(answered_ids):
        raise BusinessException(400, "请先完成全部题目后再标记完成")
if existing:
    return existing
```

创建完成记录时使用 `db.begin_nested()` 包住 `flush()`；捕获 `IntegrityError` 后重新查询唯一键 `(user_id, announcement_id)` 对应记录并继续，不回滚同一外层事务中的 `QuizAttempt`。在 `test_assignment_scoring.py` 增加 `test_concurrent_final_answers_keep_attempt_and_single_completion`，使用两个独立 Session 模拟最后一题竞争，断言两次答题均保留且完成记录只有一条。

- [x] **Step 5: 运行作业回归测试**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_assignment_practice_flow.py backend/tests/test_assignment_scoring.py -q`

Expected: PASS，且不再出现“只答一题即完成”。

- [x] **Step 6: 检查单事务边界**

Run: `rg -n "db\.commit\(\)" backend/app/services/quiz_service.py`

Expected: `submit_answer()` 的写入路径只有一个提交点，`_update_assignment_score()` 中没有提交。

### Task 2: 统一密码变更与 Token 轮换

**Files:**
- Modify: `backend/tests/test_auth.py`
- Modify: `backend/tests/test_030405_management_systems.py:134-151`
- Modify: `backend/app/core/security.py:35-85`
- Modify: `backend/app/services/auth_service.py:19-32,174-200,277-302`
- Modify: `backend/app/services/audit_service.py:16-48`
- Modify: `backend/app/api/v1/routes/auth_routes.py:43-60`
- Modify: `backend/app/api/v1/routes/admin_routes.py:188-217,359-405`
- Modify: `backend/app/api/v1/routes/teacher_routes.py:450-490`

- [x] **Step 1: 写旧 JWT 失效与软删除登录失败测试**

在 `test_auth.py` 新增以下独立用例：

- `test_change_password_rotates_token_and_returns_replacement`：旧 Token 改密成功，响应含非空 `access_token`，旧 Token 请求 `/api/me` 返回 401，新 Token 返回 0。
- `test_security_answer_reset_invalidates_existing_token`：密保答案重置后旧 Token 返回 401。
- `test_soft_deleted_user_cannot_login_or_reuse_token`：先登录取得 Token，再软删除用户，登录和旧 Token 请求均返回 401。

在 `test_030405_management_systems.py` 增加 `test_admin_teacher_reset_and_manual_approval_rotate_tokens`，分别覆盖管理员直接重置教师密码、教师审批学生重置、管理员审批学生重置，断言目标用户原 Token 全部失效。软删除登录请求使用夹具真实密码：

```python
login_resp = client.post(
    "/api/token",
    json={"id": "2025001", "password": "abc123"},
).json()
assert login_resp["code"] == 401
```

- [x] **Step 2: 运行测试并确认旧 Token 仍可用**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_auth.py backend/tests/test_030405_management_systems.py -q`

Expected: FAIL，旧 Token 或软删除用户仍通过认证。

- [x] **Step 3: 统一用户有效性、Token scope 和版本递增**

登录、当前用户、密保重置目标和人工重置目标查询增加 `User.deleted_at.is_(None)`；`get_current_user` 拒绝带有非空 `scope` 的专用 Token，避免阶段 C 的文件 Token 调用普通 API。在 `auth_service.py` 增加：

```python
def rotate_user_tokens(user: User) -> int:
    user.token_version = (user.token_version or 0) + 1
    return user.token_version
```

所有写入新密码的路径调用 `rotate_user_tokens(user)`，具体包括登录态修改密码、密保答案重置、教师审批、管理员审批和管理员直接重置教师密码。

- [x] **Step 4: 登录态改密返回新 Token，并统一审计事务**

把 `auth_routes.py` 中的改密业务下沉为 `auth_service.change_password()`。该服务校验旧密码、更新密码和 `needs_password_change`、调用 `rotate_user_tokens()`、写入 `user.password_change` 审计日志，然后只提交一次并返回：

```python
new_token = create_access_token({"sub": user.id, "token_version": user.token_version})
return {
    "message": "密码修改成功",
    "access_token": new_token,
}
```

路由只执行 `return success(change_password(db, current_user.id, req.old_password, req.new_password, current_user))`，不能在服务中再次包装统一响应。`verify_answers_and_reset_password()` 在同一提交中写入匿名重置审计。`approve_reset_request()` 移除内部 `commit()`、改为 `flush()`；教师和管理员审批路由都必须写入 `user.password_reset` 审计后提交，任一环节异常时回滚，不能出现密码已改但审计未落库。

- [x] **Step 5: 运行认证与审批回归**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_auth.py backend/tests/test_forgot_password_rate_limit.py backend/tests/test_teacher_password_reset_scope.py backend/tests/test_030405_management_systems.py -q`

Expected: PASS。

### Task 3: 所有前端改密入口保存新 Token

**Files:**
- Modify: `frontend/src/api/auth.ts`
- Modify: `frontend/src/api/admin.ts`
- Modify: `frontend/src/stores/auth.ts:123-137`
- Modify: `frontend/src/views/ChangePasswordView.vue:79-165`
- Modify: `frontend/src/views/LoginView.vue:180-215`
- Modify: `frontend/src/views/ProfileView.vue:20-55`
- Create: `frontend/tests/password-rotation-static.test.mjs`

- [x] **Step 1: 写三个改密调用方的失败测试**

静态测试必须同时断言：`auth.changePassword` 和 `admin.changePassword` 的返回类型含 `access_token`；store 的 `changePassword()` 使用 API 返回值调用 `replaceAccessToken()`；`ChangePasswordView` 不再自行丢弃返回值；`LoginView` 与 `ProfileView` 继续通过 store 改密。测试还要检查新 Token 写入发生在密保请求或后续导航之前。

- [x] **Step 2: 运行并确认 store 当前丢弃 Token**

Run: `node frontend/tests/password-rotation-static.test.mjs`

Expected: FAIL，现有 store 和页面只清除 `needs_password_change`，没有保存响应中的 `access_token`。

- [x] **Step 3: 统一 Token 替换**

在 auth store 增加并导出：

```typescript
function replaceAccessToken(accessToken: string) {
  token.value = accessToken
  localStorage.setItem('auth_token', accessToken)
}
```

两份 API 的返回类型统一为 `{ message: string; access_token: string }`。store 的 `changePassword()` 获取响应后先调用 `replaceAccessToken(result.access_token)`，再更新用户的 `needs_password_change` 并持久化；`ChangePasswordView` 改用 store 的改密函数，不能继续直接调用 `admin.ts` 后丢弃响应。失败时不得清除当前 Token。

- [x] **Step 4: 运行三个调用方测试、类型检查和构建**

Run: `node frontend/tests/password-rotation-static.test.mjs`

Run: `npm run type-check --prefix frontend`

Run: `npm run build --prefix frontend`

Expected: 全部 PASS；改密后当前设备继续携带新 Token，密保设置不再返回 401。

### Task 4: 限制教师通知到自己的学生

**Files:**
- Modify: `backend/tests/test_030405_management_systems.py`
- Modify: `backend/app/schemas/common.py:643-700`
- Modify: `backend/app/api/v1/routes/notification_routes.py:35-50`
- Modify: `backend/app/services/notification_service.py:185-249`

- [x] **Step 1: 写跨教师通知拒绝测试**

使用夹具 `T001 -> 2025001`、`T002 -> 2025002`：T001 通知 2025002 应返回 403；T001 通知 2025001 成功；管理员通知任意学生成功。另测 `action_url="https://example.com"` 返回 422 或 400。

- [x] **Step 2: 运行通知测试并确认越权请求当前成功**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_030405_management_systems.py -k "notification" -q`

Expected: FAIL，T001 当前可通知 2025002。

- [x] **Step 3: 增加站内路径校验**

在 Schema 中复用校验器：

```python
def validate_internal_action_url(value: str) -> str:
    value = value.strip()
    if value and (not value.startswith("/") or value.startswith("//")):
        raise ValueError("跳转地址必须是站内路径")
    return value
```

`NotificationSendIn` 和 `NotificationBatchSendIn` 的 `action_url` 均调用该校验器。

- [x] **Step 4: 服务层校验教师学生归属**

服务签名改为：

```python
def send_notification(db: Session, data: NotificationSendIn, operator: AuthUser) -> dict:
    """仅向当前操作人有权管理的未删除学生发送单条通知。"""

def send_batch_notifications(db: Session, data: NotificationBatchSendIn, operator: AuthUser) -> dict:
    """批量过滤无权访问、已删除或偏好关闭的学生并返回发送/跳过数量。"""
```

教师目标查询必须连接 `StudentClassEnrollment` 与 `Class` 并过滤 `Class.created_by == operator.id`、`Class.deleted_at.is_(None)`、`User.deleted_at.is_(None)`；管理员只过滤学生角色和未删除状态。

- [x] **Step 5: 运行通知回归**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_030405_management_systems.py -k "notification" -q`

Expected: PASS。

### Task 5: 删除课程时保留共享题库

**Files:**
- Modify: `backend/tests/test_030405_management_systems.py:13-59`
- Modify: `backend/tests/test_integration_bugfixes.py`
- Modify: `backend/app/services/question_service.py:292-322`
- Modify: `backend/app/services/question_bank_service.py`
- Modify: `backend/app/services/admin_public_course_service.py:120-175`
- Modify: `backend/app/services/soft_delete_service.py:79-143`

- [x] **Step 1: 把原有错误级联测试改为共享题保留与权限稳定测试**

课程删除前记录题目 ID 和 `created_by`；删除后断言题目 `deleted_at is None` 且 `course_id` 已转挂到未删除的共享题库根课程；恢复课程后题目不重复、不转回。另断言原贡献教师仍可编辑该题，承接课程的其他教师不能因为 `course_id` 变化而获得编辑权。

- [x] **Step 2: 运行测试并确认题目当前被软删除**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_030405_management_systems.py::test_course_soft_delete_cascades_to_core_children -q`

Expected: FAIL，新断言看到题目已被软删除。

- [x] **Step 3: 转挂后再软删除课程**

把转挂实现集中为 `question_bank_service.rehome_questions_before_course_delete(db, course)`，教师课程删除和管理员公共课程删除都必须在删除课程前调用。转挂目标优先使用未删除的公共共享题库根；没有公共根时选择其他未删除课程作为外键锚点。教师编辑权限改为依据 `Question.created_by`，不能依据承接课程所有者。若课程存在题目且没有任何可用锚点，抛出：

```python
raise BusinessException(400, "当前没有可承接共享题库的课程，暂时无法删除该课程")
```

`soft_delete_service` 的课程子资源列表移除 `Question`；恢复列表同步移除 `Question`。

- [x] **Step 4: 运行课程、题库和公共课程删除回归**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_030405_management_systems.py backend/tests/test_integration_bugfixes.py backend/tests/test_public_course_delete.py backend/tests/test_public_question_contribution.py -q`

Expected: PASS。

### Task 6: 阶段 A 全量验证与记录

**Files:**
- Modify: `backend/docs/项目修改记录.md`
- Modify: `docs/superpowers/specs/2026-07-09-01-assignment-grading-system.md`
- Modify: `docs/superpowers/specs/2026-07-09-03-soft-delete-mechanism.md`
- Modify: `docs/superpowers/specs/2026-07-09-04-notification-system-extension.md`

- [x] **Step 1: 运行后端全量测试**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests -q --basetemp=tmp/pytest-phase-a`

Expected: 全部业务测试 PASS；显式可写临时目录避免 Windows 系统临时目录权限错误掩盖业务结果。

- [x] **Step 2: 更新文档**

记录四类根因、最终语义、测试命令和服务器部署影响：需要拉代码、重启后端、重新构建前端并备份数据库；阶段 A 不需要数据库迁移、环境变量或 Nginx 修改。

- [x] **Step 3: 更新图谱并核对改动边界**

Run: `graphify update .`

Run: `git diff --check`

Expected: 图谱增量更新成功，diff 无空白错误；本计划不自动暂存或提交，只有用户明确要求时才按精确文件清单执行 Git 操作。
