# 资料原位恢复与注册下线 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 资料从回收站恢复时回到删除时的阶段位置（阶段不在则同课程重建同名阶段）；并彻底移除学生自助注册前后端入口，账号仅靠管理员/教师导入创建。

**Architecture:** 在 `materials` 表增加删除时阶段快照三字段；`soft_delete` 写快照，`delete_stage` 级联时不再抹定位；`restore_resource` 对资料按快照挂回或 get-or-create 同名阶段。注册面删除路由/页面/API/服务与仅服务注册的 Schema，测试改为断言接口不存在。

**Tech Stack:** Python FastAPI + SQLAlchemy、Vue 3 + TypeScript、pytest、现有 `schema_compat.ensure_schema_compatibility`。

**设计依据:** `docs/superpowers/specs/2026-07-18-material-restore-original-position-and-remove-register-design.md`

---

## 文件结构（将创建/修改）

| 文件 | 职责 |
|---|---|
| `backend/app/models/entities.py` | `Material` 增加 `deleted_stage_id` / `deleted_stage_name` / `deleted_stage_sort_order` |
| `backend/app/db/schema_compat.py` | 旧库启动时补齐三列 |
| `backend/app/services/soft_delete_service.py` | 软删写快照；恢复时挂回/重建阶段并清空快照 |
| `backend/app/services/course_stage_service.py` | 级联删阶段时先软删（触发快照），去掉主动 `stage_id=None` 抹定位 |
| `backend/tests/test_material_restore_original_position.py` | 原位恢复与 cascade 场景测试（新建） |
| `backend/tests/test_stage_material_delete_cascade.py` | 如有断言与新语义冲突则微调；可增快照断言 |
| `backend/app/api/v1/routes/auth_routes.py` | 删除 `POST /register` |
| `backend/app/services/auth_service.py` | 删除 `register_user` |
| `backend/app/schemas/common.py` | 删除 `RegisterRequest` |
| `backend/tests/test_auth.py` | 注册用例改为“接口不可用” |
| `frontend/src/views/RegisterView.vue` | 删除 |
| `frontend/src/router/index.ts` | 删除 `/register` 路由 |
| `frontend/src/api/auth.ts` | 删除 `RegisterPayload` / `register()` |
| `frontend/src/stores/auth.ts` | 删除 `register` |
| `backend/docs/项目修改记录.md` | 本轮修改与服务器部署影响 |
| `docs/superpowers/specs/2026-07-18-material-restore-original-position-and-remove-register-design.md` | 状态改为已落地（实现完成后） |
| 验收清单（若改 outputs 内 xlsx 则可选） | G-10 标为不适用/已下线 |

**工作区注意:** 当前已有与本任务无关的未提交改动（登录页、页头页脚、教师成绩导出等）。实现时**只暂存本任务文件**，禁止 `git add -A` 或把无关文件打进提交。

---

### Task 1: 资料阶段快照字段 + schema 兼容

**Files:**
- Modify: `backend/app/models/entities.py`（`Material` 类）
- Modify: `backend/app/db/schema_compat.py`（`materials` 列补齐处，约 `stage_id` 附近）

- [ ] **Step 1: 在 Material 模型增加三字段**

在 `Material` 中 `stage_id` 字段之后增加：

```python
    # 软删时阶段定位快照；活跃资料忽略；恢复挂回后清空
    deleted_stage_id = Column(Integer, nullable=True)
    deleted_stage_name = Column(String(64), nullable=True)
    deleted_stage_sort_order = Column(Integer, nullable=True)
```

不要给 `deleted_stage_id` 加指向 `course_stages` 的外键（阶段会物理删除，快照 ID 仅作参考）。

- [ ] **Step 2: schema_compat 补齐三列**

在 `materials.stage_id` 补齐逻辑附近增加：

```python
        if "materials" in table_names:
            _add_column_if_missing(conn, inspector, "materials", "stage_id", "INTEGER NULL")
            # ... 现有 stage_id 索引 ...
            _add_column_if_missing(conn, inspector, "materials", "deleted_stage_id", "INTEGER NULL")
            _add_column_if_missing(conn, inspector, "materials", "deleted_stage_name", "VARCHAR(64) NULL")
            _add_column_if_missing(conn, inspector, "materials", "deleted_stage_sort_order", "INTEGER NULL")
```

注意：该文件里可能已有 `if "materials" in table_names:` 块；**合并进现有块**，避免重复 `if` 或重复加 `stage_id`。

- [ ] **Step 3: 快速语法检查**

Run:

```bash
cd backend && python -c "from app.models.entities import Material; assert hasattr(Material, 'deleted_stage_name'); from app.db.schema_compat import ensure_schema_compatibility; print('ok')"
```

Expected: 打印 `ok`，无 ImportError。

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/entities.py backend/app/db/schema_compat.py
git commit -m "feat: 资料软删阶段快照字段与 schema 兼容"
```

---

### Task 2: soft_delete 写入阶段快照（TDD）

**Files:**
- Create: `backend/tests/test_material_restore_original_position.py`
- Modify: `backend/app/services/soft_delete_service.py`

- [ ] **Step 1: 写失败测试 — 软删资料时写入快照**

创建 `backend/tests/test_material_restore_original_position.py`：

```python
"""资料原位恢复：删除写阶段快照，恢复挂回或重建同名阶段。"""
from app.models.entities import Course, CourseStage, Material
from app.schemas.common import AuthUser
from app.services.soft_delete_service import restore_resource, soft_delete
from tests.conftest import auth_header


def _teacher_token(client) -> str:
    resp = client.post("/api/token", json={"id": "T001", "password": "abc123"})
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def _admin_token(client) -> str:
    resp = client.post("/api/token", json={"id": "admin", "password": "Admin#2026"})
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def _owned_course(db_session) -> Course:
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    assert course is not None
    return course


def test_soft_delete_material_writes_stage_snapshot(db_session):
    course = _owned_course(db_session)
    stage = CourseStage(course_id=course.id, name="原位阶段A", sort_order=3)
    db_session.add(stage)
    db_session.flush()
    mat = Material(
        course_id=course.id,
        stage_id=stage.id,
        type="pdf",
        title="待删PDF",
        url="/a.pdf",
        size="1 MB",
    )
    db_session.add(mat)
    db_session.commit()

    soft_delete(
        db_session,
        mat,
        AuthUser(id="T001", name="测试教师", role="teacher"),
        action="material.delete",
    )
    db_session.commit()
    db_session.expire_all()

    row = db_session.get(Material, mat.id)
    assert row is not None
    assert row.deleted_at is not None
    assert row.deleted_stage_id == stage.id
    assert row.deleted_stage_name == "原位阶段A"
    assert row.deleted_stage_sort_order == 3
```

- [ ] **Step 2: 运行确认失败**

Run:

```bash
cd backend && python -m pytest tests/test_material_restore_original_position.py::test_soft_delete_material_writes_stage_snapshot -v
```

Expected: FAIL（字段为空或断言失败，因尚未写快照逻辑）。

- [ ] **Step 3: 在 soft_delete 写入快照**

在 `soft_delete` 中，于 `if was_active:` 设置 `deleted_at` **之前或同时**，对 `Material`：

```python
    if was_active:
        if isinstance(item, Material):
            stage = None
            if getattr(item, "stage_id", None) is not None:
                stage = db.query(CourseStage).filter(CourseStage.id == item.stage_id).first()
            if stage is not None:
                item.deleted_stage_id = stage.id
                item.deleted_stage_name = stage.name
                item.deleted_stage_sort_order = stage.sort_order
            else:
                item.deleted_stage_id = None
                item.deleted_stage_name = None
                item.deleted_stage_sort_order = None
        deleted_at = now_utc()
        item.deleted_at = deleted_at
        item.deleted_by = operator.id
```

需要增加 import：

```python
from app.models.entities import Announcement, Class, Course, CourseStage, Material, Project, Question, User
```

若 `item` 已是二次软删（`was_active` 为 False），不要覆盖已有快照。

- [ ] **Step 4: 运行确认通过**

Run:

```bash
cd backend && python -m pytest tests/test_material_restore_original_position.py::test_soft_delete_material_writes_stage_snapshot -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_material_restore_original_position.py backend/app/services/soft_delete_service.py
git commit -m "feat: 资料软删时写入阶段定位快照"
```

---

### Task 3: 恢复时挂回原阶段（阶段仍在）

**Files:**
- Modify: `backend/tests/test_material_restore_original_position.py`
- Modify: `backend/app/services/soft_delete_service.py`（`restore_resource`）

- [ ] **Step 1: 写失败测试 — 单删后恢复 stage_id 一致**

追加到测试文件：

```python
def test_restore_material_returns_to_existing_stage(client, db_session):
    course = _owned_course(db_session)
    stage = CourseStage(course_id=course.id, name="恢复挂回阶段", sort_order=1)
    db_session.add(stage)
    db_session.flush()
    mat = Material(
        course_id=course.id,
        stage_id=stage.id,
        type="pdf",
        title="可恢复资料",
        url="/r.pdf",
        size="1 MB",
    )
    db_session.add(mat)
    db_session.commit()
    mat_id, stage_id, course_id = mat.id, stage.id, course.id

    soft_delete(
        db_session,
        mat,
        AuthUser(id="T001", name="测试教师", role="teacher"),
        action="material.delete",
    )
    db_session.commit()

    admin = _admin_token(client)
    resp = client.post(
        f"/api/admin/restore/materials/{mat_id}",
        headers=auth_header(admin),
    ).json()
    assert resp["code"] == 0

    db_session.expire_all()
    row = db_session.get(Material, mat_id)
    assert row.deleted_at is None
    assert row.course_id == course_id
    assert row.stage_id == stage_id
    assert row.deleted_stage_name is None
    assert row.deleted_stage_id is None
```

- [ ] **Step 2: 运行确认失败**

Run:

```bash
cd backend && python -m pytest tests/test_material_restore_original_position.py::test_restore_material_returns_to_existing_stage -v
```

Expected: 可能 PASS 若 stage_id 未被清空；若当前路径已丢 stage 则 FAIL。若因快照未清空导致 FAIL，下一步实现清空逻辑。

- [ ] **Step 3: 实现 restore 阶段挂回核心**

在 `restore_resource` 中，课程 remount 逻辑之后、`item.deleted_at = None` 之前/之后，对 `Material` 调用阶段解析（建议抽局部函数，放在同文件）：

```python
def _resolve_material_stage_on_restore(db: Session, item: Material, target_course_id: int) -> dict[str, Any]:
    """按当前 stage 或删除快照，将资料挂回目标课程下的阶段。"""
    info: dict[str, Any] = {"阶段处理": "无快照", "重建阶段": False}
    # 1) 当前 stage_id 仍有效且属于目标课程
    if item.stage_id is not None:
        stage = (
            db.query(CourseStage)
            .filter(CourseStage.id == item.stage_id, CourseStage.course_id == target_course_id)
            .first()
        )
        if stage is not None:
            info["阶段处理"] = "保留原阶段"
            info["阶段ID"] = stage.id
            info["阶段名称"] = stage.name
            return info
        item.stage_id = None

    name = (item.deleted_stage_name or "").strip()
    if not name:
        info["阶段处理"] = "无阶段快照"
        item.stage_id = None
        return info

    existing = (
        db.query(CourseStage)
        .filter(CourseStage.course_id == target_course_id, CourseStage.name == name)
        .first()
    )
    if existing is not None:
        item.stage_id = existing.id
        info["阶段处理"] = "复用同名阶段"
        info["阶段ID"] = existing.id
        info["阶段名称"] = existing.name
        return info

    sort_order = item.deleted_stage_sort_order
    if sort_order is None:
        sort_order = 0
    stage = CourseStage(
        course_id=target_course_id,
        name=name,
        sort_order=sort_order,
    )
    db.add(stage)
    db.flush()
    item.stage_id = stage.id
    info["阶段处理"] = "重建同名阶段"
    info["重建阶段"] = True
    info["阶段ID"] = stage.id
    info["阶段名称"] = stage.name
    return info
```

**注意:** 不要调用 `create_stage(..., teacher_id=...)` 做恢复——它在同名时会 `BusinessException(400)`；恢复必须“先查后建”，与 `create_stage` 的“同名拒绝”产品规则不同。

在 `restore_resource` 主体中（伪代码位置）：

```python
    # 现有：course_id 为空时 target 重挂 ...
    remount_course_id = None
    if isinstance(item, Material) and item.course_id is None:
        ...  # 现有逻辑
        remount_course_id = target.id

    stage_restore_info: dict[str, Any] = {}
    if isinstance(item, Material):
        target_cid = item.course_id
        if target_cid is None:
            raise BusinessException(400, "原课程已清理，请选择恢复到的课程")
        stage_restore_info = _resolve_material_stage_on_restore(db, item, target_cid)
        item.deleted_stage_id = None
        item.deleted_stage_name = None
        item.deleted_stage_sort_order = None

    item.deleted_at = None
    item.deleted_by = None
    # ... 课程同批 children 逻辑不变 ...
    # details 合并 stage_restore_info
```

确保 `details` 与返回 `result` 带上阶段处理信息（便于前端提示，测试可只断言 DB）。

- [ ] **Step 4: 运行确认通过**

Run:

```bash
cd backend && python -m pytest tests/test_material_restore_original_position.py::test_restore_material_returns_to_existing_stage -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_material_restore_original_position.py backend/app/services/soft_delete_service.py
git commit -m "feat: 恢复资料时挂回仍存在的原阶段"
```

---

### Task 4: 阶段级联删除后恢复重建同名阶段

**Files:**
- Modify: `backend/app/services/course_stage_service.py`
- Modify: `backend/tests/test_material_restore_original_position.py`
- Modify: `backend/tests/test_stage_material_delete_cascade.py`（必要时）

- [ ] **Step 1: 写失败测试 — cascade 删阶段后恢复重建阶段**

```python
def test_restore_material_rebuilds_stage_after_cascade_delete(client, db_session):
    token = _teacher_token(client)
    course = _owned_course(db_session)
    stage = CourseStage(course_id=course.id, name="级联原阶段", sort_order=5)
    db_session.add(stage)
    db_session.flush()
    mat = Material(
        course_id=course.id,
        stage_id=stage.id,
        type="pdf",
        title="级联内资料",
        url="/c.pdf",
        size="1 MB",
    )
    db_session.add(mat)
    db_session.commit()
    stage_id, mat_id, course_id = stage.id, mat.id, course.id
    stage_name = "级联原阶段"

    resp = client.delete(
        f"/api/stages/{stage_id}?cascade_materials=true",
        headers=auth_header(token),
    ).json()
    assert resp["code"] == 0
    db_session.expire_all()
    assert db_session.get(CourseStage, stage_id) is None
    dead = db_session.get(Material, mat_id)
    assert dead.deleted_at is not None
    assert dead.deleted_stage_name == stage_name

    admin = _admin_token(client)
    restored = client.post(
        f"/api/admin/restore/materials/{mat_id}",
        headers=auth_header(admin),
    ).json()
    assert restored["code"] == 0

    db_session.expire_all()
    row = db_session.get(Material, mat_id)
    assert row.deleted_at is None
    assert row.course_id == course_id
    assert row.stage_id is not None
    new_stage = db_session.get(CourseStage, row.stage_id)
    assert new_stage is not None
    assert new_stage.course_id == course_id
    assert new_stage.name == stage_name
```

- [ ] **Step 2: 运行确认失败或暴露 cascade 未写快照**

Run:

```bash
cd backend && python -m pytest tests/test_material_restore_original_position.py::test_restore_material_rebuilds_stage_after_cascade_delete -v
```

Expected: FAIL，若 cascade 仍 `stage_id=None` 且 soft_delete 前未保留阶段信息。

- [ ] **Step 3: 修改 delete_stage 级联逻辑**

`course_stage_service.delete_stage` 中改为：

```python
    if active_materials and cascade_materials:
        op_id = operator_id or teacher_id or ""
        operator = AuthUser(id=op_id, name="", role=operator_role)
        for material in list(active_materials):
            # soft_delete 内写阶段快照；不要再 material.stage_id = None
            soft_delete(db, material, operator, action="material.delete")

    db.delete(stage)
    db.flush()
    return True
```

说明：物理删阶段后，DB 的 `ON DELETE SET NULL` 可能把 `materials.stage_id` 置空，但 `deleted_stage_*` 快照必须仍在。确保 soft_delete **在** `db.delete(stage)` **之前**完成并 flush。

管理员公共课删阶段路径若自己循环 soft_delete，同样不得清空快照；检查 `admin_public_course_routes` 中 cascade 分支是否直接改 `stage_id`，有则去掉。

- [ ] **Step 4: 补充复用同名阶段测试**

```python
def test_restore_material_reuses_existing_same_name_stage(client, db_session):
    token = _teacher_token(client)
    course = _owned_course(db_session)
    stage = CourseStage(course_id=course.id, name="同名阶段", sort_order=1)
    db_session.add(stage)
    db_session.flush()
    mat = Material(
        course_id=course.id, stage_id=stage.id, type="pdf",
        title="同名复用", url="/s.pdf", size="1 MB",
    )
    db_session.add(mat)
    db_session.commit()
    stage_id, mat_id = stage.id, mat.id

    assert client.delete(
        f"/api/stages/{stage_id}?cascade_materials=true",
        headers=auth_header(token),
    ).json()["code"] == 0

    # 管理员/教师再建同名阶段
    recreated = CourseStage(course_id=course.id, name="同名阶段", sort_order=9)
    db_session.add(recreated)
    db_session.commit()
    recreated_id = recreated.id

    admin = _admin_token(client)
    assert client.post(
        f"/api/admin/restore/materials/{mat_id}",
        headers=auth_header(admin),
    ).json()["code"] == 0

    db_session.expire_all()
    row = db_session.get(Material, mat_id)
    assert row.stage_id == recreated_id
    # 同课程下仅一个「同名阶段」
    count = db_session.query(CourseStage).filter(
        CourseStage.course_id == course.id, CourseStage.name == "同名阶段"
    ).count()
    assert count == 1
```

- [ ] **Step 5: 无快照兼容测试**

```python
def test_restore_material_without_snapshot_leaves_stage_null(client, db_session):
    course = _owned_course(db_session)
    mat = Material(
        course_id=course.id, stage_id=None, type="pdf",
        title="无阶段旧数据", url="/n.pdf", size="1 MB",
    )
    db_session.add(mat)
    db_session.commit()
    soft_delete(
        db_session, mat,
        AuthUser(id="T001", name="测试教师", role="teacher"),
        action="material.delete",
    )
    # 模拟历史数据：无快照
    mat.deleted_stage_id = None
    mat.deleted_stage_name = None
    mat.deleted_stage_sort_order = None
    db_session.commit()
    mat_id = mat.id

    admin = _admin_token(client)
    assert client.post(
        f"/api/admin/restore/materials/{mat_id}",
        headers=auth_header(admin),
    ).json()["code"] == 0
    db_session.expire_all()
    row = db_session.get(Material, mat_id)
    assert row.deleted_at is None
    assert row.stage_id is None
```

- [ ] **Step 6: 跑本文件全部测试 + cascade 回归**

Run:

```bash
cd backend && python -m pytest tests/test_material_restore_original_position.py tests/test_stage_material_delete_cascade.py -v
```

Expected: 全部 PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/course_stage_service.py backend/app/services/soft_delete_service.py backend/tests/test_material_restore_original_position.py backend/tests/test_stage_material_delete_cascade.py
git commit -m "feat: 阶段级联删后恢复资料可重建同名阶段"
```

---

### Task 5: 后端移除注册接口（TDD）

**Files:**
- Modify: `backend/tests/test_auth.py`
- Modify: `backend/app/api/v1/routes/auth_routes.py`
- Modify: `backend/app/services/auth_service.py`
- Modify: `backend/app/schemas/common.py`

- [ ] **Step 1: 改写注册相关测试为“接口不存在”**

删除/替换 `TestAuth` 中 5 个 `test_register_*` 为例如：

```python
    def test_register_endpoint_removed(self, client):
        resp = client.post(
            "/api/register",
            json={
                "id": "2025100",
                "name": "新学生",
                "password": "abc123",
                "role": "student",
                "major": "测试",
            },
        )
        # 路由已删除：Starlette/FastAPI 返回 404
        assert resp.status_code == 404
```

保留 `test_login_*`、`test_get_me` 等。

全仓检索 `backend/tests` 是否还有 `/api/register` 或 `register_user`，一并改掉。

- [ ] **Step 2: 运行确认当前仍“非 404”（旧接口还在）**

Run:

```bash
cd backend && python -m pytest tests/test_auth.py::TestAuth::test_register_endpoint_removed -v
```

Expected: FAIL（status_code 不是 404）。

- [ ] **Step 3: 删除后端注册面**

1. `auth_routes.py`：删除 `register` 路由函数；去掉 `RegisterRequest`、`register_user` 的 import。
2. `auth_service.py`：删除 `register_user` 及对 `RegisterRequest` 的 import；更新模块 docstring。
3. `schemas/common.py`：删除 `RegisterRequest` 类（确认无其它引用后再删）。

Run:

```bash
cd backend && rg -n "register_user|RegisterRequest|/register" app -g '*.py'
```

Expected: 无业务引用（测试除外）。

- [ ] **Step 4: 运行认证测试**

Run:

```bash
cd backend && python -m pytest tests/test_auth.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/routes/auth_routes.py backend/app/services/auth_service.py backend/app/schemas/common.py backend/tests/test_auth.py
git commit -m "feat: 移除学生自助注册后端接口"
```

---

### Task 6: 前端移除注册页与引用

**Files:**
- Delete: `frontend/src/views/RegisterView.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/api/auth.ts`
- Modify: `frontend/src/stores/auth.ts`
- 全仓扫: 其它指向 `/register` 的链接

- [ ] **Step 1: 删除路由**

从 `frontend/src/router/index.ts` 移除：

```ts
      path: '/register',
      name: 'register',
      component: () => import('../views/RegisterView.vue'),
      meta: { title: '注册 · AI 通识课程平台', public: true },
```

整段 route 对象删除。

- [ ] **Step 2: 删除 API 与 store**

`frontend/src/api/auth.ts`：删除 `RegisterPayload` 与 `register` 函数。

`frontend/src/stores/auth.ts`：
- import 去掉 `register as apiRegister`
- 删除 `register` 异步函数
- `return { ... }` 去掉 `register`

- [ ] **Step 3: 删除页面文件**

```bash
git rm frontend/src/views/RegisterView.vue
```

- [ ] **Step 4: 扫尾**

```bash
cd frontend && rg -n "register|RegisterView|/register" src -g '*.ts' -g '*.vue'
```

Expected: 无业务引用（注释/历史文案除外，有则删）。

- [ ] **Step 5: 类型检查与构建**

Run:

```bash
cd frontend && npm run type-check && npm run build
```

Expected: 成功退出码 0。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/router/index.ts frontend/src/api/auth.ts frontend/src/stores/auth.ts
git add -u frontend/src/views/RegisterView.vue
git commit -m "feat: 移除学生自助注册前端页面与路由"
```

---

### Task 7: 回归、文档与部署说明

**Files:**
- Modify: `backend/docs/项目修改记录.md`（文首追加新一轮）
- Modify: `docs/superpowers/specs/2026-07-18-material-restore-original-position-and-remove-register-design.md`（状态改为已落地）
- Optional: `AGENTS.md` 仅当长期规则需写“无自助注册”时一行补充；勿写临时过程
- Optional: 验收清单 G-10 文案（`outputs/` 一般不入库则跳过提交）

- [ ] **Step 1: 后端相关回归**

Run:

```bash
cd backend && python -m pytest tests/test_material_restore_original_position.py tests/test_stage_material_delete_cascade.py tests/test_auth.py tests/test_soft_delete_lifecycle.py tests/test_soft_delete_relationships.py -v
```

Expected: PASS

若时间允许再跑更广 soft_delete 套件。

- [ ] **Step 2: 写修改记录（中文，含服务器部署影响）**

在 `backend/docs/项目修改记录.md` 文首追加一轮，至少包含：

- G-05：快照字段、删除写快照、恢复挂回/重建、cascade 不再抹定位
- G-10：注册前后端删除，导入建号保留
- 验证命令与结果
- **服务器部署影响：**
  - 需要：拉代码；启动时 `schema_compat` 补列（或等价迁移）；重启后端
  - 需要：重新构建并发布前端
  - 不需要：新环境变量
  - 说明：已在回收站且无快照的历史资料恢复不保证原位

- [ ] **Step 3: 更新设计文档状态行**

将 design 顶部状态改为：已按本计划落地（并注明日期）。

- [ ] **Step 4: Commit 文档**

```bash
git add backend/docs/项目修改记录.md docs/superpowers/specs/2026-07-18-material-restore-original-position-and-remove-register-design.md
git commit -m "docs: 记录资料原位恢复与注册下线"
```

- [ ] **Step 5: 最终自检**

```bash
git status -sb
git log -5 --oneline
```

确认无把无关工作区改动误提交。

---

## Spec 覆盖自检

| Spec 要求 | 对应 Task |
|---|---|
| materials 阶段快照字段 + 兼容 | Task 1 |
| 软删写快照 | Task 2 |
| 恢复挂回仍存在阶段 | Task 3 |
| cascade 后重建同名阶段 / 复用同名 / 无快照兼容 | Task 4 |
| 删除 cascade 抹 `stage_id` 逻辑 | Task 4 |
| 后端注册删除 | Task 5 |
| 前端注册删除 | Task 6 |
| 测试、修改记录、部署影响 | Task 7 |
| 不做阶段完整回收站 | 全计划未引入 stages 回收站类型 |
| 保留登录/导入 | Task 5–6 不触碰导入与 login |

## Placeholder 扫描

计划中无 TBD/TODO；测试与实现代码块完整；提交命令只 add 本任务路径。

## 类型/命名一致性

- 字段固定：`deleted_stage_id` / `deleted_stage_name` / `deleted_stage_sort_order`
- 恢复辅助：`_resolve_material_stage_on_restore`
- 同名策略：目标课程内按 `name` 精确匹配复用
