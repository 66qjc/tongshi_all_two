# 安全风险按序修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 `docs/superpowers/2026-07-03-project-pages-stability-security-review.md` 的修复顺序，先关闭 P0 权限漏洞，再处理 P1 核心安全边界。

**Architecture:** 本轮采用最小服务层授权修复，不新增业务目录，不新增数据库字段，不搬迁路由结构。文件访问授权优先复用 `StoredFile`、`Material`、`Project`、`ShowcaseItem`、`Course`、`Class`、`StudentClassEnrollment` 的现有关系；无法证明归属的通用文件访问默认拒绝。若发现必须新增 `visibility` 字段、迁移历史数据或重做文件目录结构，立即停下确认。

**Tech Stack:** FastAPI、SQLAlchemy、pytest、Vue 3 `<script setup lang="ts">`、Element Plus、Node 静态测试。

---

## 范围

本计划覆盖：
- P0-1：锁住 `/api/files/{file_id}`，新增登录鉴权、业务归属授权、公开文件白名单。
- P0-2：禁止公开注册教师账号，前端注册页只保留学生注册。
- P0-3：修复教师跨班级审批或驳回密码重置申请。
- P1-1：移除临时密码在列表接口中的长期明文暴露。
- P1-2：统一本地文件读取路径边界校验。
- P1-3：教师批量删除学生改为解除本教师班级关系，或保留全站删除仅管理员执行。

本计划暂不做：
- 不新增 `StoredFile.visibility` 字段。
- 不新增 Alembic 迁移。
- 不重构路由目录或服务目录。
- 不重做文件上传存储结构。
- 不在本轮改 query token 为一次性票据；该项排到后续专项。
- 不调整 Nginx 真实服务器目录，除非后续服务器验收明确目录不一致。

## 当前证据

- `backend/app/api/v1/routes/file_routes.py` 的 `GET /files/{file_id}` 当前没有 `get_current_user` 或 `require_role` 依赖。
- `backend/app/services/file_service.py` 的 `resolve_file_stream()` 只按 `file_id` 取文件并打开流，没有业务授权判断。
- `backend/app/services/auth_service.py` 的 `register_user()` 当前允许 `student` 和 `teacher`。
- `frontend/src/views/RegisterView.vue` 当前暴露学生/教师单选，并会把 `teacher` 提交给公开注册接口。
- `backend/app/services/auth_service.py` 的 `approve_reset_request()`、`reject_reset_request()` 只按 `request_id` 查询申请，没有校验申请人是否属于当前教师班级。
- `get_reset_requests_for_teacher()` 已有教师班级范围查询，可作为教师审批授权的业务依据。
- `backend/tests/conftest.py` 已有 `T001`、`T002`、`2025001`、`2025002` 两组教师/学生/班级数据，可直接构造跨班级回归测试。

## 涉及文件

后端测试：
- Modify: `backend/tests/test_auth.py`
- Modify: `backend/tests/test_material_file_acceleration.py`
- Create: `backend/tests/test_teacher_password_reset_scope.py`
- Create: `backend/tests/test_local_storage_boundaries.py` 或并入现有文件测试

后端实现：
- Modify: `backend/app/api/v1/routes/file_routes.py`
- Modify: `backend/app/services/file_service.py`
- Modify: `backend/app/services/auth_service.py`
- Modify: `backend/app/api/v1/routes/teacher_routes.py`
- Modify: `backend/app/services/storage_local.py`
- 可能 Modify: `backend/app/services/material_service.py`
- 可能 Modify: `backend/app/services/project_service.py`

前端实现与静态测试：
- Modify: `frontend/src/views/RegisterView.vue`
- Create: `frontend/tests/register-student-only-static.test.mjs`
- 可能 Modify: `frontend/src/stores/auth.ts`

文档同步：
- Modify: `docs/superpowers/project-map.md` 或新增阶段记录
- Modify: `backend/docs/项目修改记录.md`（若当前文件编码状态允许安全追加）
- 本计划执行完成总结必须包含“服务器部署影响”。

---

## Task 1: P0 文件访问接口鉴权与归属授权

**Files:**
- Modify: `backend/tests/test_material_file_acceleration.py`
- Modify: `backend/app/api/v1/routes/file_routes.py`
- Modify: `backend/app/services/file_service.py`

- [ ] **Step 1: 写测试辅助：为 StoredFile 写入真实本地文件**

在 `backend/tests/test_material_file_acceleration.py` 顶部补充导入：

```python
from pathlib import Path

from app.core.config import settings
```

追加辅助函数：

```python
def _write_local_file(object_key: str, content: bytes = b"test file"):
    target = Path(settings.local_upload_dir) / object_key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
```

- [ ] **Step 2: 写 RED 测试：未登录不能访问通用文件接口**

追加：

```python
def test_generic_file_rejects_anonymous_user(client, db_session):
    stored = _stored_file(db_session)
    _write_local_file(stored.object_key)

    response = client.get(f"/api/files/{stored.id}")
    data = response.json()

    assert response.status_code == 200
    assert data["code"] == 401
```

- [ ] **Step 3: 运行 RED**

Run:

```powershell
cd backend
py -m pytest tests/test_material_file_acceleration.py::test_generic_file_rejects_anonymous_user -q
```

Expected: FAIL，因为当前匿名访问会尝试返回文件流或文件缺失错误，不会返回 `401`。

- [ ] **Step 4: 写 RED 测试：课程外学生不能通过 `/api/files/{id}` 绕过资料授权**

追加：

```python
def test_generic_file_rejects_student_outside_material_course(client, db_session, student_token):
    other_course = db_session.query(Course).filter(Course.created_by == "T002").first()
    stored = _stored_file(db_session, created_by="T002", object_key="course/other.pdf")
    _write_local_file(stored.object_key)
    _material(db_session, course_id=other_course.id, file_id=stored.id)

    response = client.get(f"/api/files/{stored.id}", headers=auth_header(student_token))
    data = response.json()

    assert response.status_code == 200
    assert data["code"] == 404
```

- [ ] **Step 5: 运行 RED**

Run:

```powershell
cd backend
py -m pytest tests/test_material_file_acceleration.py::test_generic_file_rejects_student_outside_material_course -q
```

Expected: FAIL，因为当前通用文件接口不检查资料课程归属。

- [ ] **Step 6: 写目标测试：课程内学生和归属教师可访问资料文件**

追加：

```python
def test_generic_file_allows_enrolled_student_for_material(client, db_session, student_token):
    stored = _stored_file(db_session)
    _write_local_file(stored.object_key)
    _material(db_session, file_id=stored.id)

    response = client.get(f"/api/files/{stored.id}", headers=auth_header(student_token))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")


def test_generic_file_allows_owner_teacher_for_material(client, db_session, teacher_token):
    stored = _stored_file(db_session)
    _write_local_file(stored.object_key)
    _material(db_session, file_id=stored.id)

    response = client.get(f"/api/files/{stored.id}", headers=auth_header(teacher_token))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
```

说明：这两个目标测试用于防止修复时把合法文件访问一并挡掉。

- [ ] **Step 7: 实现最小授权入口**

在 `backend/app/api/v1/routes/file_routes.py` 中引入 `get_current_user` 和 `AuthUser`，把路由签名改为：

```python
def get_file(
    file_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """通过 file_id 统一访问文件，先校验登录态和业务归属。"""
    record, stream = resolve_file_stream(db, file_id, current_user)
```

在 `backend/app/services/file_service.py` 中把 `resolve_file_stream()` 改为接收可选当前用户，并在打开文件前调用授权函数：

```python
from app.core.exceptions import BusinessException


def resolve_file_stream(db: Session, file_id: int, current_user=None) -> tuple[StoredFile, BinaryIO]:
    record = db.query(StoredFile).filter(StoredFile.id == file_id).first()
    if record is None:
        return None, None
    if current_user is not None and not can_current_user_read_file(db, record, current_user):
        raise BusinessException(404, "文件不存在")
    ...
```

新增 `can_current_user_read_file()`，授权矩阵：
- 管理员允许读取存在的文件。
- `record.created_by == current_user.id` 允许读取本人上传文件。
- `Material.file_id == record.id` 时复用 `can_view_course_materials()`。
- `Project.report_file_id`、`Project.cover_file_id`、`ProjectImage.file_id` 时允许作者本人、管理员、已通过公开作品的登录用户、或拥有该作品课程审核权限的教师。
- `ShowcaseItem.cover_file_id`、`ShowcaseItemImage.file_id` 时仅允许 `is_active=True` 的公开展示图片，或管理员/上传者。
- `MaterialPreview.cover_file_id` 时仅当用户可访问对应资料时允许。
- 其他无法证明归属的文件默认拒绝。

- [ ] **Step 8: 保持旧内部调用兼容**

`backend/app/api/v1/routes/teacher_routes.py` 中下载已通过作品报告会调用 `resolve_file_stream(db, report_file_id)`。该内部教师路由已在外层做审核范围过滤，本轮可以让 `current_user=None` 保持内部兼容；若后续发现无外层授权的内部调用，改为传入 `current_user`。

- [ ] **Step 9: 跑文件相关 GREEN**

Run:

```powershell
cd backend
py -m pytest tests/test_material_file_acceleration.py -q
```

Expected: PASS。

## Task 2: P0 禁止公开教师注册

**Files:**
- Modify: `backend/tests/test_auth.py`
- Modify: `backend/app/services/auth_service.py`
- Modify: `frontend/src/views/RegisterView.vue`
- Create: `frontend/tests/register-student-only-static.test.mjs`

- [ ] **Step 1: 写 RED 后端测试**

在 `TestAuth` 中追加：

```python
def test_register_rejects_teacher_role(self, client):
    resp = client.post(
        "/api/register",
        json={
            "id": "T9001",
            "name": "非法教师注册",
            "password": "abc123456",
            "role": "teacher",
            "major": "",
        },
    )
    data = resp.json()

    assert resp.status_code == 200
    assert data["code"] == 400
    assert "角色" in data["message"]
```

- [ ] **Step 2: 运行 RED**

Run:

```powershell
cd backend
py -m pytest tests/test_auth.py::TestAuth::test_register_rejects_teacher_role -q
```

Expected: FAIL，因为当前后端允许 `teacher`。

- [ ] **Step 3: 后端实现**

在 `backend/app/services/auth_service.py` 中把公开注册角色改为只允许学生：

```python
allowed_roles = {"student"}
```

错误码与现有 `admin`、未知角色保持一致，继续抛 `BusinessException(400, "注册角色不合法")`。

- [ ] **Step 4: 前端静态 RED 测试**

新增 `frontend/tests/register-student-only-static.test.mjs`：

```javascript
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import assert from 'node:assert/strict'

const root = resolve(process.cwd())
const view = readFileSync(resolve(root, 'src/views/RegisterView.vue'), 'utf8')

assert.doesNotMatch(view, /value="teacher"/, '公开注册页不应提供教师注册选项')
assert.doesNotMatch(view, /form\.role\s*===\s*'teacher'/, '公开注册页不应按教师角色跳转')
assert.match(view, /role:\s*'student'/, '公开注册默认角色应固定为学生')
assert.match(view, /authStore\.register\([\s\S]*'student'/, '公开注册提交时应固定传 student')

console.log('register student only static checks passed')
```

Run:

```powershell
cd frontend
node tests/register-student-only-static.test.mjs
```

Expected: FAIL，因为当前页面有教师选项。

- [ ] **Step 5: 前端实现**

在 `frontend/src/views/RegisterView.vue` 中：
- 把 `form.role` 类型改为固定学生，不再暴露教师选项。
- 移除身份单选区域。
- 学号输入文案改为学生语境。
- 调用 `authStore.register()` 时固定传 `'student'`。
- 注册成功后固定跳转 `/`。

- [ ] **Step 6: 跑 GREEN**

Run:

```powershell
cd backend
py -m pytest tests/test_auth.py::TestAuth::test_register_rejects_teacher_role tests/test_auth.py::TestAuth::test_register_rejects_admin_role tests/test_auth.py::TestAuth::test_register_rejects_unknown_role -q

cd ..\frontend
node tests/register-student-only-static.test.mjs
```

Expected: PASS。

## Task 3: P0 教师密码重置审批范围

**Files:**
- Create: `backend/tests/test_teacher_password_reset_scope.py`
- Modify: `backend/app/services/auth_service.py`
- Modify: `backend/app/api/v1/routes/teacher_routes.py`

- [ ] **Step 1: 写 RED 测试：教师不能审批其他班级学生申请**

创建 `backend/tests/test_teacher_password_reset_scope.py`：

```python
from app.models.entities import PasswordResetRequest
from tests.conftest import auth_header


def _reset_request(db_session, user_id="2025002"):
    req = PasswordResetRequest(user_id=user_id, message="忘记密码")
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)
    return req


def test_teacher_cannot_approve_reset_request_for_other_class_student(client, db_session, teacher_token):
    req = _reset_request(db_session, "2025002")

    response = client.post(
        f"/api/teacher/password-reset-requests/{req.id}/approve",
        headers=auth_header(teacher_token),
    )
    data = response.json()

    assert response.status_code == 200
    assert data["code"] == 404
```

- [ ] **Step 2: 写 RED 测试：教师不能驳回其他班级学生申请**

追加：

```python
def test_teacher_cannot_reject_reset_request_for_other_class_student(client, db_session, teacher_token):
    req = _reset_request(db_session, "2025002")

    response = client.post(
        f"/api/teacher/password-reset-requests/{req.id}/reject",
        json={"reason": "信息不匹配"},
        headers=auth_header(teacher_token),
    )
    data = response.json()

    assert response.status_code == 200
    assert data["code"] == 404
```

- [ ] **Step 3: 写允许本班学生的 GREEN 目标测试**

追加：

```python
def test_teacher_can_approve_reset_request_for_own_class_student(client, db_session, teacher_token):
    req = _reset_request(db_session, "2025001")

    response = client.post(
        f"/api/teacher/password-reset-requests/{req.id}/approve",
        headers=auth_header(teacher_token),
    )
    data = response.json()

    assert response.status_code == 200
    assert data["code"] == 0
    assert data["data"]["temp_password"]
```

- [ ] **Step 4: 运行 RED**

Run:

```powershell
cd backend
py -m pytest tests/test_teacher_password_reset_scope.py -q
```

Expected: 前两个测试 FAIL，因为当前教师可跨班级审批/驳回。

- [ ] **Step 5: 实现教师范围校验 helper**

在 `backend/app/services/auth_service.py` 中新增：

```python
def _teacher_can_resolve_reset_request(db: Session, teacher_id: str, request_id: int) -> PasswordResetRequest | None:
    from app.models.entities import Class, StudentClassEnrollment

    return (
        db.query(PasswordResetRequest)
        .join(StudentClassEnrollment, StudentClassEnrollment.user_id == PasswordResetRequest.user_id)
        .join(Class, Class.id == StudentClassEnrollment.class_id)
        .filter(
            PasswordResetRequest.id == request_id,
            Class.created_by == teacher_id,
        )
        .first()
    )
```

新增教师专用 wrapper：

```python
def approve_reset_request_for_teacher(db: Session, request_id: int, teacher_id: str) -> dict:
    req = _teacher_can_resolve_reset_request(db, teacher_id, request_id)
    if not req:
        raise BusinessException(404, "申请不存在")
    return approve_reset_request(db, request_id, teacher_id)


def reject_reset_request_for_teacher(db: Session, request_id: int, teacher_id: str, reason: str) -> dict:
    req = _teacher_can_resolve_reset_request(db, teacher_id, request_id)
    if not req:
        raise BusinessException(404, "申请不存在")
    return reject_reset_request(db, request_id, teacher_id, reason)
```

- [ ] **Step 6: 路由改用教师专用 wrapper**

在 `backend/app/api/v1/routes/teacher_routes.py` 中把教师审批和驳回调用改为：

```python
return success(approve_reset_request_for_teacher(db, request_id, current_user.id))
```

和：

```python
return success(reject_reset_request_for_teacher(db, request_id, current_user.id, data.reason))
```

管理员端继续使用原 `approve_reset_request()`、`reject_reset_request()`，保留全局审批能力。

- [ ] **Step 7: 跑 GREEN**

Run:

```powershell
cd backend
py -m pytest tests/test_teacher_password_reset_scope.py -q
```

Expected: PASS。

## Task 4: P1 临时密码不再在列表长期明文返回

**Files:**
- Modify: `backend/tests/test_teacher_password_reset_scope.py`
- Modify: `backend/app/services/auth_service.py`
- 可能 Modify: `frontend/src/views/admin/AdminPasswordReset.vue`

- [ ] **Step 1: 写 RED 测试：列表接口不返回历史临时密码**

在 `backend/tests/test_teacher_password_reset_scope.py` 追加：

```python
def test_teacher_reset_request_list_does_not_return_temp_password_after_approval(client, db_session, teacher_token):
    req = _reset_request(db_session, "2025001")
    approve = client.post(
        f"/api/teacher/password-reset-requests/{req.id}/approve",
        headers=auth_header(teacher_token),
    )
    assert approve.json()["code"] == 0
    assert approve.json()["data"]["temp_password"]

    listing = client.get("/api/teacher/password-reset-requests", headers=auth_header(teacher_token))
    item = next(row for row in listing.json()["data"] if row["id"] == req.id)

    assert item["temp_password"] == ""
```

- [ ] **Step 2: 运行 RED**

Run:

```powershell
cd backend
py -m pytest tests/test_teacher_password_reset_scope.py::test_teacher_reset_request_list_does_not_return_temp_password_after_approval -q
```

Expected: FAIL，因为当前 `_reset_request_out()` 返回 `req.temp_password`。

- [ ] **Step 3: 实现最小变更**

在 `_reset_request_out()` 中固定返回空字符串：

```python
"temp_password": "",
```

审批响应仍一次性返回 `temp_password`，不改变教师端审批成功后的即时展示能力。

- [ ] **Step 4: 跑 GREEN**

Run:

```powershell
cd backend
py -m pytest tests/test_teacher_password_reset_scope.py -q
```

Expected: PASS。

## Task 5: P1 本地文件路径边界统一校验

**Files:**
- Create: `backend/tests/test_local_storage_boundaries.py`
- Modify: `backend/app/services/storage_local.py`
- Modify: `backend/app/services/file_service.py`

- [ ] **Step 1: 写 RED 测试：本地适配器拒绝目录穿越**

创建 `backend/tests/test_local_storage_boundaries.py`：

```python
import pytest

from app.services.storage_local import LocalStorageAdapter


def test_local_storage_rejects_path_traversal(tmp_path):
    adapter = LocalStorageAdapter(tmp_path)

    with pytest.raises(ValueError):
        adapter.exists(object_key="../secret.txt")

    with pytest.raises(ValueError):
        adapter.open_stream(object_key="../secret.txt")
```

- [ ] **Step 2: 运行 RED**

Run:

```powershell
cd backend
py -m pytest tests/test_local_storage_boundaries.py -q
```

Expected: FAIL，因为当前适配器直接拼接路径。

- [ ] **Step 3: 实现 `_resolve_safe_path()`**

在 `backend/app/services/storage_local.py` 中新增私有方法：

```python
def _resolve_safe_path(self, object_key: str) -> Path:
    cleaned = object_key.replace("\\", "/").lstrip("/")
    if cleaned.startswith("uploads/"):
        cleaned = cleaned[len("uploads/"):]
    target = (self.root_dir / cleaned).resolve()
    root = self.root_dir.resolve()
    if target != root and root not in target.parents:
        raise ValueError("文件路径不合法")
    return target
```

把 `save_bytes()`、`open_write_stream()`、`open_stream()`、`exists()`、`delete()` 全部改为使用 `_resolve_safe_path()`。

- [ ] **Step 4: 通用文件流复用规范化**

在 `resolve_file_stream()` 的 local 分支中使用 `normalize_local_object_key()`：

```python
try:
    object_key = normalize_local_object_key(record.object_key)
except ValueError:
    raise BusinessException(400, "文件路径不合法")
```

- [ ] **Step 5: 跑 GREEN**

Run:

```powershell
cd backend
py -m pytest tests/test_local_storage_boundaries.py tests/test_material_file_acceleration.py -q
```

Expected: PASS。

## Task 6: P1 教师批量删除学生语义降级

**Files:**
- Modify: `backend/tests/test_integration_bugfixes.py` 或 Create: `backend/tests/test_teacher_student_delete_scope.py`
- Modify: `backend/app/services/class_service.py`
- 可能 Modify: `backend/app/api/v1/routes/teacher_routes.py`
- 可能 Modify: `frontend/src/views/teacher/TeacherStudents.vue` 或 `TeacherStudentAdmin.vue`

- [ ] **Step 1: 先定位当前批量删除入口**

Run:

```powershell
cd backend
rg "delete_student|batch|students" app/api/v1/routes app/services tests -n
```

Expected: 找到教师批量删除路由、`_delete_student_data()` 和调用链。

- [ ] **Step 2: 写 RED 测试：共享学生不能被教师全站删除**

测试构造：
- 让 `2025001` 同时加入 `T001` 和 `T002` 的班级。
- 由 `T001` 执行教师端删除/批量删除。
- 断言 `User(id="2025001")` 仍存在。
- 断言 `2025001` 与 `T002` 班级关系仍存在。
- 断言 `2025001` 与 `T001` 班级关系已解除。

示例断言：

```python
assert db_session.query(User).filter(User.id == "2025001").first() is not None
assert db_session.query(StudentClassEnrollment).filter(
    StudentClassEnrollment.user_id == "2025001",
    StudentClassEnrollment.class_id == other_class.id,
).first() is not None
assert db_session.query(StudentClassEnrollment).filter(
    StudentClassEnrollment.user_id == "2025001",
    StudentClassEnrollment.class_id == own_class.id,
).first() is None
```

- [ ] **Step 3: 实现教师端只解除本教师班级关系**

服务层拆分语义：
- 管理员全站删除保留 `_delete_student_data()`。
- 教师端新增 `remove_students_from_teacher_classes(db, teacher_id, student_ids)`。
- 删除范围只包含 `Class.created_by == teacher_id` 的 `StudentClassEnrollment`。
- 不删除 `User`。
- 不删除作品、答题、任务、消息等全站数据。

- [ ] **Step 4: 前端文案同步**

教师端按钮和确认弹窗从“删除学生”改为“移出班级”或“从我的班级移除”，明确“不删除学生账号和其他课程数据”。

- [ ] **Step 5: 跑 GREEN**

Run:

```powershell
cd backend
py -m pytest tests/test_teacher_student_delete_scope.py -q
```

Expected: PASS。

---

## 分阶段验证

P0 后端最小验证：

```powershell
cd backend
py -m pytest tests/test_auth.py tests/test_material_file_acceleration.py tests/test_teacher_password_reset_scope.py -q
```

P1 后端最小验证：

```powershell
cd backend
py -m pytest tests/test_local_storage_boundaries.py tests/test_material_file_acceleration.py tests/test_teacher_password_reset_scope.py tests/test_teacher_student_delete_scope.py -q
```

前端最小验证：

```powershell
cd frontend
node tests/register-student-only-static.test.mjs
npm run build
```

全量建议：

```powershell
cd backend
py -m pytest tests/ -q

cd ..\frontend
npm run build
```

## 风险与停机点

必须停下确认的情况：
- 需要新增、删除或迁移数据库字段。
- 需要批量迁移历史 `StoredFile.biz_type`、`biz_id` 或真实上传目录。
- 需要改动 Nginx alias、生产上传目录或服务器环境变量。
- 发现 `/api/files/{file_id}` 的现有生产依赖必须允许匿名访问且无法用公开资料专用接口替代。
- 发现教师批量删除学生当前被业务定义为“删除账号”，与本计划的“移出班级”冲突。

可继续的情况：
- 只是在现有 route/service/test 文件中增加授权 helper。
- 只新增测试文件或前端静态测试。
- 只修改注册页文案和提交角色。
- 只修改列表响应不再返回 `temp_password`。

## 服务器部署影响

本计划执行完成后预计需要：
- 服务器拉取代码。
- 重启后端 FastAPI 服务。
- 重新构建并部署前端静态资源。
- 不需要数据库迁移，除非执行过程中触发“停机点”并经确认改为字段级方案。
- 不需要修改环境变量。
- 若本地文件路径边界修复影响历史异常 `object_key`，服务器需要清点并修正这些历史记录后才能访问对应文件。
