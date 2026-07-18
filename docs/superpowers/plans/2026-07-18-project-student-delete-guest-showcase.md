# 学生作品删除与游客作品展示 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让学生可软删除自己的待审/驳回作品，并让游客只读浏览已通过作品且可匿名点赞（只加不减）。

**Architecture:** 复用现有 `Project.status` 与 `soft_delete`；列表/详情改为可选登录且仍只返回/放行 `approved`（作者本人可看自己的未通过）；新增学生删除接口与游客 `guest-like` 计数接口；前端将 `/create` 与作品详情标为公开路由，游客点赞用 localStorage 防连点。

**Tech Stack:** FastAPI、SQLAlchemy、Vue 3 + TypeScript、Element Plus、pytest、Node 静态测试

**设计依据：** `docs/superpowers/specs/2026-07-18-project-student-delete-guest-showcase-design.md`

---

## 文件与职责地图

| 文件 | 职责 |
|---|---|
| `backend/app/core/security.py` | 新增通用 `get_optional_user`（无 token 返回 `None`，有 token 走现有校验） |
| `backend/app/services/project_service.py` | 学生自删、游客可读详情、游客点赞 `+1` |
| `backend/app/api/v1/routes/project_routes.py` | 可选登录列表/详情、学生删除、guest-like |
| `backend/tests/test_project_guest_and_student_delete.py` | 后端权限与计数回归 |
| `frontend/src/api/project.ts` | `deleteMyProject`、`guestLikeProject` |
| `frontend/src/router/index.ts` | `/create`、`/create/project/:id` 设 `public: true`；上传仍需登录 |
| `frontend/src/views/ProjectDetailView.vue` | 游客点赞、作者删除入口 |
| `frontend/src/views/PortfolioView.vue` | 「我的作品」待审/驳回删除入口（若卡片无状态则详情删除为主，卡片按数据字段补） |
| `frontend/src/views/CreateView.vue` | 未登录可加载列表；上传按钮可保留登录跳转 |
| `frontend/tests/project-guest-delete-static.test.mjs` | 前端静态约束 |
| `backend/docs/项目修改记录.md` | 第 N 轮修改记录与服务器部署影响 |

**明确不改：** 教师 `DELETE /api/teacher/projects/{id}` 语义、审核通过/驳回流程、数据库表结构、上传即全量展示。

---

### Task 1: 可选登录依赖 + 学生删除服务（后端 TDD）

**Files:**
- Modify: `backend/app/core/security.py`
- Modify: `backend/app/services/project_service.py`
- Create: `backend/tests/test_project_guest_and_student_delete.py`

- [x] **Step 1: 写失败测试（学生删除矩阵）**

在 `backend/tests/test_project_guest_and_student_delete.py` 写入：

```python
"""学生删除与游客作品展示回归。"""
from app.core.security import get_password_hash
from app.models.entities import Course, Project, User
from tests.conftest import auth_header


def _create_project(client, token: str, course_id: int, title: str = "测试作品") -> int:
    resp = client.post(
        "/api/projects",
        json={
            "course_id": course_id,
            "title": title,
            "description": "说明",
            "tags": ["AI"],
            "image_urls": [],
            "image_file_ids": [],
        },
        headers=auth_header(token),
    ).json()
    assert resp["code"] == 0
    return resp["data"]["id"]


def test_student_can_delete_own_pending_project(client, db_session, student_token):
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    project_id = _create_project(client, student_token, course.id, "待审可删")

    resp = client.delete(f"/api/projects/{project_id}", headers=auth_header(student_token)).json()
    assert resp["code"] == 0

    mine = client.get("/api/projects/mine", headers=auth_header(student_token)).json()
    assert all(item["id"] != project_id for item in mine["data"]["items"])


def test_student_can_delete_own_rejected_project(client, db_session, student_token):
    rejected = Project(
        title="驳回可删",
        author_id="2025001",
        description="x",
        status="rejected",
        reject_reason="补充材料",
    )
    db_session.add(rejected)
    db_session.commit()

    resp = client.delete(f"/api/projects/{rejected.id}", headers=auth_header(student_token)).json()
    assert resp["code"] == 0


def test_student_cannot_delete_approved_project(client, db_session, student_token):
    approved = Project(
        title="已通过不可删",
        author_id="2025001",
        description="x",
        status="approved",
    )
    db_session.add(approved)
    db_session.commit()

    resp = client.delete(f"/api/projects/{approved.id}", headers=auth_header(student_token)).json()
    assert resp["code"] == 400
    assert "已通过" in resp["message"]


def test_student_cannot_delete_others_project(client, db_session, student_token):
    other = User(
        id="2025999",
        name="其他学生",
        role="student",
        hashed_password=get_password_hash("abc123"),
    )
    db_session.add(other)
    db_session.flush()
    project = Project(
        title="别人的待审",
        author_id="2025999",
        description="x",
        status="pending",
    )
    db_session.add(project)
    db_session.commit()

    resp = client.delete(f"/api/projects/{project.id}", headers=auth_header(student_token)).json()
    assert resp["code"] in (403, 404)
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_project_guest_and_student_delete.py -q --tb=short
```

Expected: 失败（路由 404 或删除函数不存在）

- [ ] **Step 3: 实现 `get_optional_user`**

在 `backend/app/core/security.py` 的 `get_current_user` 后新增：

```python
async def get_optional_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> AuthUser | None:
    """可选登录：无 token 返回 None；有 token 则完整校验。"""
    if not token:
        return None
    return authenticate_bearer_token(token, db)
```

- [ ] **Step 4: 实现学生自删服务**

在 `backend/app/services/project_service.py` 增加（放在教师 `delete_project` 附近）：

```python
def delete_own_project(db: Session, project_id: int, user_id: str):
    """学生软删除自己的待审/驳回作品。"""
    project = get_project(db, project_id)
    if not project or project.deleted_at is not None:
        return None
    if project.author_id != user_id:
        raise BusinessException(403, "只能删除自己的作品")
    if project.status == "approved":
        raise BusinessException(400, "已通过作品不可删除，请联系教师处理")
    if project.status not in ("pending", "rejected"):
        raise BusinessException(400, "当前作品状态不可删除")

    from app.schemas.common import AuthUser
    from app.services.soft_delete_service import soft_delete

    operator = AuthUser(id=user_id, name="", role="student")
    soft_delete(db, project, operator, action="project.delete")
    db.commit()
    logger.info("学生删除作品: project_id=%s, user_id=%s", project_id, user_id)
    return project
```

并确保文件顶部已导入 `BusinessException`（若无则补 `from app.core.exceptions import BusinessException`）。

- [ ] **Step 5: 注册删除路由**

在 `backend/app/api/v1/routes/project_routes.py`：

```python
from app.services.project_service import (
    list_approved_projects, get_project, get_accessible_project, get_user_projects,
    create_project, toggle_like, update_project, format_project, batch_load_liked_set,
    delete_own_project,
)

@router.delete("/{project_id}", summary="删除我的作品", description="学生端：软删除自己的待审或驳回作品")
def delete_my_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    p = delete_own_project(db, project_id, current_user.id)
    if not p:
        raise BusinessException(404, "作品不存在")
    return success({"id": project_id})
```

注意：该路由必须放在会与 `/{project_id}` 冲突的声明之后且不遮挡 `/mine`；现有 `/mine` 已在 `/{project_id}` 前，保持该顺序。

- [ ] **Step 6: 跑通删除测试**

Run:

```bash
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_project_guest_and_student_delete.py -q --tb=short
```

Expected: 删除相关用例 PASS（游客用例若尚未写可先只跑上述四个）

- [ ] **Step 7: Commit（仅在用户明确要求提交时执行）**

```bash
git add backend/app/core/security.py backend/app/services/project_service.py backend/app/api/v1/routes/project_routes.py backend/tests/test_project_guest_and_student_delete.py
git commit -m "feat: 支持学生软删除待审与驳回作品"
```

---

### Task 2: 游客只读列表/详情 + 匿名点赞（后端 TDD）

**Files:**
- Modify: `backend/app/services/project_service.py`
- Modify: `backend/app/api/v1/routes/project_routes.py`
- Modify: `backend/tests/test_project_guest_and_student_delete.py`

- [ ] **Step 1: 追加失败测试**

```python
def test_guest_can_list_only_approved_projects(client, db_session, student_token):
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    pending_id = _create_project(client, student_token, course.id, "待审隐藏")
    approved = Project(
        title="公开作品",
        author_id="2025001",
        description="x",
        status="approved",
    )
    db_session.add(approved)
    db_session.commit()

    resp = client.get("/api/projects?page=1&page_size=50").json()
    assert resp["code"] == 0
    ids = [item["id"] for item in resp["data"]["items"]]
    assert approved.id in ids
    assert pending_id not in ids


def test_guest_can_view_approved_detail_but_not_pending(client, db_session, student_token):
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    pending_id = _create_project(client, student_token, course.id, "待审详情")
    approved = Project(
        title="公开详情",
        author_id="2025001",
        description="x",
        status="approved",
    )
    db_session.add(approved)
    db_session.commit()

    ok = client.get(f"/api/projects/{approved.id}").json()
    assert ok["code"] == 0
    assert ok["data"]["title"] == "公开详情"
    assert ok["data"].get("is_liked") is False

    denied = client.get(f"/api/projects/{pending_id}").json()
    assert denied["code"] == 404


def test_guest_like_increments_counter_only(client, db_session):
    approved = Project(
        title="可赞作品",
        author_id="2025001",
        description="x",
        status="approved",
        likes=3,
    )
    db_session.add(approved)
    db_session.commit()

    resp = client.post(f"/api/projects/{approved.id}/guest-like").json()
    assert resp["code"] == 0
    assert resp["data"]["liked"] is True
    assert resp["data"]["likes"] == 4

    # 不写 ProjectLike 行（无 user_id）
    from app.models.entities import ProjectLike
    assert db_session.query(ProjectLike).filter(ProjectLike.project_id == approved.id).count() == 0


def test_guest_like_rejects_non_approved(client, db_session, student_token):
    course = db_session.query(Course).filter(Course.created_by == "T001").first()
    pending_id = _create_project(client, student_token, course.id, "不可赞")
    resp = client.post(f"/api/projects/{pending_id}/guest-like").json()
    assert resp["code"] in (400, 404)
```

- [ ] **Step 2: 运行确认失败**

```bash
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_project_guest_and_student_delete.py -q --tb=short
```

Expected: 游客相关 FAIL

- [ ] **Step 3: 服务层游客点赞与可读详情**

```python
def guest_like_project(db: Session, project_id: int):
    project = get_project(db, project_id)
    if not project or project.status != "approved":
        return None
    db.execute(
        Project.__table__.update()
        .where(Project.id == project_id)
        .values(likes=Project.likes + 1)
    )
    db.commit()
    db.refresh(project)
    return {"liked": True, "likes": project.likes}


def get_public_or_accessible_project(db: Session, project_id: int, user_id: str | None):
    """游客仅已通过；登录用户沿用 get_accessible_project。"""
    if user_id:
        return get_accessible_project(db, project_id, user_id)
    project = get_project(db, project_id)
    if not project or project.status != "approved":
        return None
    return project
```

- [ ] **Step 4: 路由改为可选登录并挂 guest-like**

```python
from app.core.security import get_current_user, get_optional_user
from app.services.project_service import (
    list_approved_projects, get_project, get_accessible_project, get_user_projects,
    create_project, toggle_like, update_project, format_project, batch_load_liked_set,
    delete_own_project, guest_like_project, get_public_or_accessible_project,
)

@router.get("", summary="作品广场", description="浏览所有已通过审核的项目作品；游客可访问")
def get_projects(
    page: int = 1,
    page_size: int = 12,
    db: Session = Depends(get_db),
    current_user: AuthUser | None = Depends(get_optional_user),
):
    projects, total = list_approved_projects(db, page, page_size)
    user_id = current_user.id if current_user else None
    liked = batch_load_liked_set(db, [p.id for p in projects], user_id) if user_id else set()
    return paginated_success(
        [format_project(db, p, user_id, liked_set=liked) for p in projects],
        total, page, page_size,
    )


@router.get("/{project_id}", summary="作品详情", description="已通过作品游客可看；未通过仅作者可看")
def get_project_detail(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser | None = Depends(get_optional_user),
):
    user_id = current_user.id if current_user else None
    p = get_public_or_accessible_project(db, project_id, user_id)
    if not p:
        raise BusinessException(404, "作品不存在")
    return success(format_project(db, p, user_id))


@router.post("/{project_id}/guest-like", summary="游客点赞", description="匿名点赞，仅增加计数，不可取消")
def guest_like(project_id: int, db: Session = Depends(get_db)):
    result = guest_like_project(db, project_id)
    if result is None:
        raise BusinessException(404, "作品不存在")
    return success(result)
```

`format_project` 在 `user_id is None` 时应返回 `is_liked: false`（核对现有实现；若 `user_id` 为空已如此则不动）。

- [ ] **Step 5: 全量跑本文件测试 + 既有作品范围测试**

```bash
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_project_guest_and_student_delete.py backend/tests/test_project_course_scope.py -q --tb=short
```

Expected: 全部 PASS

- [ ] **Step 6: Commit（仅用户要求时）**

```bash
git add backend/app/services/project_service.py backend/app/api/v1/routes/project_routes.py backend/app/core/security.py backend/tests/test_project_guest_and_student_delete.py
git commit -m "feat: 游客可浏览已通过作品并匿名点赞"
```

---

### Task 3: 前端 API + 路由公开

**Files:**
- Modify: `frontend/src/api/project.ts`
- Modify: `frontend/src/router/index.ts`
- Create: `frontend/tests/project-guest-delete-static.test.mjs`

- [ ] **Step 1: 写静态失败测试**

```javascript
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = (p) => readFileSync(resolve(root, p), 'utf8')

const api = read('src/api/project.ts')
const router = read('src/router/index.ts')
const detail = read('src/views/ProjectDetailView.vue')

assert.match(api, /export function deleteMyProject/)
assert.match(api, /export function guestLikeProject/)
assert.match(api, /guest-like/)
assert.match(router, /path: '\/create'[\s\S]*public:\s*true/)
assert.match(router, /path: '\/create\/project\/:id'[\s\S]*public:\s*true/)
assert.match(detail, /deleteMyProject|确认删除/)
assert.match(detail, /guestLikeProject|guest_liked_/)
```

- [ ] **Step 2: 运行静态测试确认失败**

```bash
node --test frontend/tests/project-guest-delete-static.test.mjs
```

Expected: FAIL

- [ ] **Step 3: 扩展 `project.ts`**

```typescript
export function deleteMyProject(projectId: number) {
  return http.delete<any, { id: number }>(`/projects/${projectId}`)
}

export function guestLikeProject(projectId: number) {
  return http.post<any, { liked: boolean; likes: number }>(`/projects/${projectId}/guest-like`)
}
```

- [ ] **Step 4: 路由公开只读页**

在 `frontend/src/router/index.ts`：

```typescript
{
  path: '/create',
  name: 'create',
  component: () => import('../views/CreateView.vue'),
  meta: { title: '践 · 智创未来', public: true },
},
{
  path: '/create/project/:id',
  name: 'project-detail',
  component: () => import('../views/ProjectDetailView.vue'),
  meta: { title: '作品详情', public: true },
},
// /create/upload 保持非 public
```

- [ ] **Step 5: 再跑静态测试（此时 detail 断言仍可能失败，可接受；API/router 断言应过）**

```bash
node --test frontend/tests/project-guest-delete-static.test.mjs
```

---

### Task 4: 详情页删除 + 游客点赞 UI

**Files:**
- Modify: `frontend/src/views/ProjectDetailView.vue`
- Modify: `frontend/src/views/CreateView.vue`（未登录加载列表容错/上传引导）
- Modify: `frontend/src/views/PortfolioView.vue`（可选：卡片删除；若 portfolio 接口无 status，则以详情删除为验收主路径）

- [ ] **Step 1: 详情页逻辑**

在 `ProjectDetailView.vue`：

```typescript
import { getProject, toggleLike as apiToggleLike, deleteMyProject, guestLikeProject, type Project } from '@/api/project'
import { ElMessage, ElMessageBox } from 'element-plus'

const guestLikeKey = computed(() => `guest_liked_${projectId.value}`)

const canDelete = computed(() => {
  if (!project.value || !authStore.user) return false
  return project.value.author_id === authStore.user.id
    && (project.value.status === 'pending' || project.value.status === 'rejected')
})

onMounted(async () => {
  try {
    project.value = await getProject(projectId.value)
    if (authStore.isLoggedIn) {
      liked.value = project.value?.is_liked ?? false
    } else {
      liked.value = localStorage.getItem(guestLikeKey.value) === '1'
    }
  } finally {
    loading.value = false
  }
})

async function toggleLike() {
  if (!project.value) return
  if (!authStore.isLoggedIn) {
    if (localStorage.getItem(guestLikeKey.value) === '1') return
    const result = await guestLikeProject(project.value.id)
    project.value.likes = result.likes
    liked.value = true
    localStorage.setItem(guestLikeKey.value, '1')
    return
  }
  const result = await apiToggleLike(project.value.id)
  project.value.likes = result.likes
  liked.value = result.liked
}

async function handleDelete() {
  if (!project.value) return
  try {
    await ElMessageBox.confirm(
      `将删除「${project.value.title}」。删除后不可在「我的作品」中恢复，如需再次展示请重新上传。`,
      '确认删除作品？',
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' },
    )
    await deleteMyProject(project.value.id)
    ElMessage.success('已删除')
    router.push('/create')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      // 拦截器已提示业务错误时可省略；否则：
      // ElMessage.error('删除失败，请稍后重试')
    }
  }
}
```

模板在 `canResubmit` 操作条旁增加：

```vue
<div v-if="canDelete || canResubmit" class="resubmit-bar">
  <el-button v-if="canResubmit" type="warning" round @click="goResubmit">修改后重新提交</el-button>
  <el-button v-if="canDelete" type="danger" round plain @click="handleDelete">删除作品</el-button>
</div>
```

点赞按钮：游客已赞时禁用或保持 `liked` 样式且点击 no-op。

- [ ] **Step 2: CreateView 未登录**

确认 `getProjects` 在无 token 时可用；上传按钮点击若未登录则 `router.push('/login')`（若现有已跳转则不动）。不要强制整页登录墙。

- [ ] **Step 3: Portfolio（可选增强）**

若 `portfolio` 返回的项目含 `status`/`id`，为 `pending|rejected` 增加删除按钮并复用 `deleteMyProject`；若无 status，本 Task 可只做详情删除，并在验证中注明。

- [ ] **Step 4: 静态测试全绿**

```bash
node --test frontend/tests/project-guest-delete-static.test.mjs
```

Expected: PASS

- [ ] **Step 5: 前端类型/构建（能跑则跑）**

```bash
npm run type-check --prefix frontend
npm run build --prefix frontend
```

Expected: 通过；若环境缺依赖，记录未验证路径。

---

### Task 5: 文档与收尾验证

**Files:**
- Modify: `backend/docs/项目修改记录.md`
- Optional: `docs/superpowers/project-map.md`（仅当稳定入口变化需登记时）

- [ ] **Step 1: 后端定向回归**

```bash
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_project_guest_and_student_delete.py backend/tests/test_project_course_scope.py -q --tb=short
```

Expected: PASS

- [ ] **Step 2: 前端静态 + 构建**

```bash
node --test frontend/tests/project-guest-delete-static.test.mjs
npm run build --prefix frontend
```

- [ ] **Step 3: 手测清单（本地有服务时）**

1. 学生上传作品（pending）→ 详情可删 → 删除后列表消失  
2. 驳回作品可删  
3. 已通过详情无删除按钮；直调 API 被拒  
4. 游客打开 `/create` 与已通过详情  
5. 游客点赞 +1，刷新仍为已赞且不连加  
6. 登录用户点赞仍可取消  
7. 教师审核删除仍可用  

- [ ] **Step 4: 写修改记录**

在 `backend/docs/项目修改记录.md` 顶部追加一轮，至少包含：

- 学生删除待审/驳回  
- 游客列表/详情  
- guest-like  
- 验证命令与结果  
- **服务器部署影响：** 需拉代码、重启后端、重建前端；不需迁移/环境变量/Nginx 结构变更  

- [ ] **Step 5: graphify 更新（代码改完后）**

```bash
graphify update .
```

不提交 `graphify-out/`。

---

## Spec 覆盖自检

| 设计要求 | 对应任务 |
|---|---|
| 学生删 pending/rejected | Task 1 |
| 学生不可删 approved | Task 1 测试 + 服务校验 |
| 教师删除保持 | 明确不改 teacher 路由 |
| 游客仅 approved 列表/详情 | Task 2 |
| 游客匿名点赞只加不减 | Task 2 + Task 4 |
| 登录点赞不变 | Task 2 不改 `/like` 语义 |
| 路由游客可进广场/详情 | Task 3 |
| 删除确认弹窗 | Task 4 |
| 修改记录与部署影响 | Task 5 |
| 不做上传即展示/可取消游客赞 | 范围声明 |

## 风险

- 游客点赞可刷：产品已接受。  
- 作品图片/报告若仍走需登录的文件接口，游客详情可能图裂：若手测出现，在同轮用现有公开文件/短时 token 模式补齐只读资源，不扩大到上传权限。  
- `DELETE /api/projects/{id}` 与教师路径不同，注意前端不要误调 teacher API。

## 服务器部署影响（实施完成后）

- 需要拉代码  
- 需要重启后端  
- 需要重建并部署前端  
- 不需要数据库迁移  
- 不需要新生产环境变量  
