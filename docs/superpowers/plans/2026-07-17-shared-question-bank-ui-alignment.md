# 共享题库两端展示与入库对齐 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development`（推荐）或 `executing-plans` 按任务逐步实施。步骤使用 checkbox（`- [ ]`）跟踪。  
> **状态：** 本轮 P1/P2 整改已实施并完成最终自动化回归（2026-07-17 工作区）：后端 `488 passed, 1 deselected, 1 warning`（292.23s），前端静态测试 `44/44`、`npm run type-check`、`npm run build` 均通过；当前未配置真实 MySQL 验证变量。  
> **日期：** 2026-07-17  
> **关联：** 用户确认范围（中文题型 / 星标 / 去课程列 / 标签入库 / 统一命名 / 全局序号）；`docs/superpowers/plans/2026-07-16-admin-question-star-rating.md`、`docs/superpowers/plans/2026-07-17-shared-question-bank-followups.md`

**Goal:** 教师端与管理员端共享题库在展示与主流程入库上对齐：统一命名「共享题库」、中文题型、星标（默认 3 星可见）、全局连续序号、列表去掉课程列、新增题目不强制挂载课程（标签即可入库）；权限差异（删题/批量/贡献）保持管理员独有。

**Architecture:** 不改共享题库数据主体与软删规则。后端仅放宽教师创建/更新 Schema 与 `create_question` 对 `course_id` 的强制；列表序号与中文题型/星标为前端展示层。两端继续使用既有 API（教师 `/api/questions`、管理 `/api/admin/question-bank`），不合并路由。

**Tech Stack:** Vue 3 + TypeScript + Element Plus；FastAPI + Pydantic + SQLAlchemy；pytest；Node 静态测试。

---

## 范围与非范围

### 做

1. 题型列表展示统一中文：选择题 / 多选题 / 填空题。  
2. 星级列表统一 `el-rate` 星标；无值时按 3 星展示。  
3. 删除列表「所属课程 / 原挂载课程」列。  
4. 手工新增题目：不要求选课程；标签沿用现有手工表单规则，`course_id` 允许为空。Excel 导入的“标签”列、每行有效标签和有效答案必须填写，课程名称仍可选。  
5. 两端菜单/页标题统一为「共享题库」。  
6. 列表序号跨页连续：`(page - 1) * pageSize + index + 1`，不展示数据库主键 ID。  
7. 同步静态测试、受影响后端测试、修改记录与 `AGENTS.md` 原则一句。

### 不做

- 不统一两端整页皮肤/布局框架。  
- 不给教师端加删除/批量删除/贡献记录。  
- 不改学生练习池、公共课程阶段资料、删阶段级联（另线）。  
- 不强制历史题回填 `course_id`；不新增星级筛选/排序。  
- 不改数据库结构（`Question.course_id` 已可空、`star_rating` 已有）。  
- Excel 导入：课程名称为**可选**（空则 `course_id=null`）；“标签”列、每行有效标签和有效答案为必填，不重做整套导入模板产品。
- 管理员独立题库导入：行内课程名称优先于默认挂载，只有唯一活跃公共课程可挂载；未知、私有或同名歧义课程按行失败，不降级为独立题；空课程值才回退默认挂载。

### 权限保持

| 能力 | 教师 | 管理员 |
|------|------|--------|
| 列表/筛选/新增/编辑 | ✅（编辑仅本人题） | ✅（可编全部） |
| 星级展示与编辑 | ✅ | ✅ |
| 删除/批量/一键清空/贡献 | ❌ | ✅ |

---

## 文件地图

| 文件 | 职责 |
|------|------|
| `backend/app/schemas/common.py` | `QuestionCreate.course_id` 改为可选 |
| `backend/app/services/question_service.py` | `create_question` 不强制课程；导入课程名可选 |
| `backend/app/api/v1/routes/question_routes.py` | OpenAPI 文案：新增可不挂课程 |
| `frontend/src/views/teacher/TeacherQuestions.vue` | 命名、序号、去课程列/表单、星标兜底 |
| `frontend/src/views/teacher/TeacherLayout.vue` | 菜单名 |
| `frontend/src/router/index.ts` | `meta.title` |
| `frontend/src/views/teacher/TeacherAnnouncements.vue` | 空状态「题库管理」→「共享题库」 |
| `frontend/src/views/admin/AdminQuestionBank.vue` | 中文题型、星标列、连续序号、去课程列、弱化挂载 |
| `frontend/tests/teacher-question-bank-static.test.mjs` | 教师静态断言 |
| `frontend/tests/admin-question-star-rating-static.test.mjs` | 管理端星标断言加强 |
| `frontend/tests/admin-question-bank-static.test.mjs` | 管理端列表断言 |
| `frontend/tests/copy-consistency-static.test.mjs` | 文案「共享题库」 |
| `backend/tests/test_teacher_question_optional_course.py` | 新建：教师无 course 创建 |
| `backend/tests/test_question_import_requirements.py` | 导入标签与答案必填、课程可选及贡献日志回归 |
| `backend/tests/test_verify_course_cleanup_mysql.py` | MySQL 验证脚本安全门单元测试 |
| `backend/app/db/base.py` | 独立 ORM 元数据基类，避免验证脚本导入 session 时加载运行时配置 |
| `backend/docs/项目修改记录.md` | 第 72 轮 |
| `AGENTS.md` | 长期约定一句 |
| `docs/superpowers/project-map.md` | 简短状态 |

---

## 本轮实施与验收状态

- 两端共享题库命名、中文题型、星标、跨页序号和去课程列已实施；教师/管理员创建题目可不挂课程。
- Excel 导入已补齐“标签”列、有效标签和有效答案必填，课程名称可选，独立题与公共课程贡献日志分开聚合；教师模板明确“题型、标签、题干、答案”四项必填。管理员经 `/api/questions/import` 遇同名课程歧义会明确拒绝；管理员独立题库导入仅允许唯一活跃公共课程挂载，行内课程优先、错误不降级、空值才回退默认挂载。
- 教师、管理员和旧公共课程兼容导入服务三条路径均以行级嵌套事务隔离真实 `flush` 失败；教师/管理员重复主键失败回归确保同批成功行不会被回滚。
- 阶段资料删除与读路径过滤属于并行整改，已完成后端和前端静态回归；本计划不改变其产品范围。
- 前端 `ElRate` 已补入按需注册。`Settings` 连续实例的 `DATABASE_URL` 与 `SECRET_KEY` 环境隔离回归各通过一条；新增 `app/db/base.py` 解耦 session 与 entities，验证脚本导入不读取项目 `.env`。验证 DSN 与管理员 DSN 必须同一 `host/port`，DSN query 覆盖禁用，报告和控制台均脱敏查询参数的敏感值，验证变量仅供 CI 或人工流程使用。
- 自动化验证：题库定向后端 `41 passed, 1 warning`；MySQL 验证脚本单元测试 `12 passed`，五条拒绝路径均以非零退出码正确拒绝；验证脚本与重复题限定组 `14 passed`，独立复审无阻断项。教师、管理员和旧公共课程兼容导入服务已补“答案不能为空”和真实 `flush` 失败隔离回归；最终后端完整回归为 `488 passed, 1 deselected, 1 warning`（292.23s），前端静态测试 `44/44`、`npm run type-check`、`npm run build` 均通过。
- 页面验收：教师 `/teacher/questions`、管理员 `/admin/question-bank`、管理员 `/admin/public-courses` 均可打开且无中文乱码；教师确认课程名称可选、标签必填和新增无课程字段，管理员确认独立题与标签必填。资料/阶段删除未点击确认，删除语义仅源码确认。当前未配置 `MYSQL_VERIFY_URL` / `MYSQL_VERIFY_ADMIN_URL`，真实 MySQL 验证脚本本轮未运行。

---

## Task 1: 后端 — 教师创建题目 `course_id` 可选

**Files:**
- Modify: `backend/app/schemas/common.py`
- Modify: `backend/app/services/question_service.py`
- Modify: `backend/app/api/v1/routes/question_routes.py`
- Create: `backend/tests/test_teacher_question_optional_course.py`

- [ ] **Step 1: 写失败测试（无 course_id 创建应成功）**

创建 `backend/tests/test_teacher_question_optional_course.py`：

```python
"""教师共享题库：新增题目可不挂课程。"""


def test_teacher_can_create_question_without_course(client, teacher_token):
    resp = client.post(
        "/api/questions",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={
            "type": "choice",
            "stem": "无挂载课程的共享题-测试用",
            "options": ["A. 一", "B. 二", "C. 三", "D. 四"],
            "answer": "A",
            "explanation": "",
            "tags": ["共享标签"],
            "star_rating": 3,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 0
    assert "id" in body["data"]

    listed = client.get(
        "/api/questions",
        headers={"Authorization": f"Bearer {teacher_token}"},
        params={"keyword": "无挂载课程的共享题-测试用", "page": 1, "page_size": 20},
    )
    assert listed.status_code == 200
    items = listed.json()["data"]["items"]
    assert len(items) >= 1
    hit = next(i for i in items if "无挂载课程的共享题-测试用" in i["stem"])
    assert hit.get("course_id") in (None, 0) or hit.get("course_id") is None
    assert hit.get("star_rating") == 3
    assert "共享标签" in (hit.get("tags") or [])


def test_teacher_create_still_accepts_optional_course(client, teacher_token):
    courses = client.get(
        "/api/courses",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert courses.status_code == 200
    course_list = courses.json()["data"]
    if isinstance(course_list, dict):
        course_list = course_list.get("items") or course_list.get("list") or []
    # 无自有课时跳过挂载断言
    owned = [c for c in course_list if c.get("is_owner")]
    if not owned:
        return
    course_id = owned[0]["id"]
    resp = client.post(
        "/api/questions",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={
            "type": "fill",
            "course_id": course_id,
            "stem": "可选挂载仍可用-测试用",
            "options": [],
            "answer": "北京",
            "tags": [],
            "star_rating": 4,
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["code"] == 0
```

> 若项目 fixture 中 `teacher_token` / `courses` 响应形状不同，按 `backend/tests/test_public_question_contribution.py` 中 `_create_teacher_course` 与现有断言改写，保持「无 course_id 可创建」为核心。

- [ ] **Step 2: 跑测试确认当前失败**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_teacher_question_optional_course.py -v
```

Expected: FAIL（`course_id` 校验 422 或服务层「课程不存在」）。

- [ ] **Step 3: 改 Schema**

`backend/app/schemas/common.py` 中 `QuestionCreate`：

```python
class QuestionCreate(BaseModel):
    type: str = "choice"
    course_id: Optional[int] = None  # 可选：共享题库以标签为主，可不挂课程
    stem: str
    options: List[str] = []
    answer: str
    explanation: str = ""
    tags: List[str] = []
    star_rating: int = Field(default=3, ge=1, le=5)
```

确认文件顶部已 `from typing import Optional`（或 `Optional` 已从既有 import 可用）。

- [ ] **Step 4: 改 `create_question`**

`backend/app/services/question_service.py` 的 `create_question` 改为：

```python
def create_question(db: Session, data: dict, teacher_id: str):
    course = None
    course_id = data.get("course_id")
    if course_id is not None:
        course = _get_owned_course(db, course_id, teacher_id)
        if not course:
            raise BusinessException(404, "课程不存在")
    data["tags"] = _normalize_tags(data.get("tags"))

    stem = data.get("stem", "").strip()
    stem_hash = compute_stem_hash(stem)

    existing = find_same_stem_question(db, stem)
    if existing:
        raise BusinessException(400, f"题库中已存在相同题目（ID: {existing.id}），请勿重复添加")

    duplicate = find_duplicate_question(
        db,
        data["type"],
        data["stem"],
        data.get("options"),
        data["answer"],
    )
    if duplicate:
        raise BusinessException(400, "题库中已存在相同题目")

    question_data = {
        k: v
        for k, v in data.items()
        if k not in ["created_by", "stem_hash", "star_rating", "mount_course_name_snapshot"]
        and v is not None
    }
    # 显式允许 course_id 为空
    if course is None:
        question_data["course_id"] = None

    q = Question(
        **question_data,
        created_by=teacher_id,
        stem_hash=stem_hash,
        star_rating=data.get("star_rating", 3),
        mount_course_name_snapshot=(course.name if course else "") or "",
    )
    db.add(q)
    db.flush()
    if course is not None and course.is_public:
        record_question_contribution(db, course, teacher_id, "teacher", "create", 1)
    db.commit()
    db.refresh(q)
    return q
```

- [ ] **Step 5: 导入时课程名称可选、标签与答案必填**

同文件 `import_questions_from_excel` 中解析课程段改为：

```python
course_name = str(_row_value(row, "课程名称", "课程", "course", "course_name")).strip()
course = None
if course_name:
    query = db.query(Course).filter(
        Course.name == course_name,
        Course.deleted_at.is_(None),
    )
    if role != "admin":
        query = query.filter(Course.created_by == teacher_id)
    course = query.first()
    if not course:
        raise BusinessException(400, f"未找到课程: {course_name}")
# course_name 为空：独立共享题，course_id=None
```

导入模板必须包含“标签”列；每行标签经规范化后为空时只记录该行失败，不能写入空标签题目。每行“答案”也必须为有效非空值，不能把空答案单元格写入题库。课程列可省略或为空；但若填写课程名称却找不到对应课程，必须按该行失败处理，不能静默降级为独立题。

创建 `Question(...)` 时：

```python
q = Question(
    type=q_type,
    course_id=course.id if course else None,
    stem=stem,
    options=option_list,
    answer=answer,
    explanation=explanation,
    tags=tags,
    created_by=teacher_id,
    stem_hash=stem_hash,
    star_rating=3,
    mount_course_name_snapshot=(course.name if course else "") or "",
)
```

贡献日志仅在 `course is not None and course.is_public` 时累计（保持原逻辑）。

- [ ] **Step 6: 路由文案**

`question_routes.py`：

```python
@router.post("", summary="新增题目", description="教师端：创建共享题；course_id 可选，不传则写入独立共享题（仅标签归属）")
```

- [ ] **Step 7: 跑测试通过**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_teacher_question_optional_course.py backend/tests/test_admin_question_bank.py backend/tests/test_public_question_contribution.py -q
```

Expected: 相关用例 PASS（若旧用例强制 `course_id` 仍传，应继续通过）。

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/common.py backend/app/services/question_service.py backend/app/api/v1/routes/question_routes.py backend/tests/test_teacher_question_optional_course.py
git commit -m "feat(question): 教师共享题创建允许不挂载课程"
```

---

## Task 2: 教师端前端 — 命名 / 列表 / 表单

**Files:**
- Modify: `frontend/src/views/teacher/TeacherQuestions.vue`
- Modify: `frontend/src/views/teacher/TeacherLayout.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/views/teacher/TeacherAnnouncements.vue`

- [ ] **Step 1: 菜单与路由标题**

`TeacherLayout.vue`：

```ts
{ name: '共享题库', path: '/teacher/questions', icon: '&#9998;' },
```

`router/index.ts` 中 teacher-questions 的 `meta.title`：

```ts
meta: { title: '共享题库' },
```

- [ ] **Step 2: 页头与计数文案**

`TeacherQuestions.vue`：

```vue
<h1>共享题库</h1>
...
<span class="filter-count">共享题库 共 {{ total }} 题</span>
```

- [ ] **Step 3: 全局连续序号 + 去掉课程列**

表格列：

```vue
<el-table-column label="序号" width="70">
  <template #default="{ $index }">
    {{ (page - 1) * pageSize + $index + 1 }}
  </template>
</el-table-column>
```

删除：

```vue
<el-table-column prop="course_name" label="所属课程" min-width="160" />
```

保留题型中文映射与星级：

```vue
<el-table-column label="题型" width="100">
  <template #default="{ row }">
    <el-tag :type="getQuestionTagType(row.type)" size="small" effect="plain">
      {{ row.type === 'choice' ? '选择题' : row.type === 'multi_choice' ? '多选题' : '填空题' }}
    </el-tag>
  </template>
</el-table-column>
<el-table-column label="星级" width="140">
  <template #default="{ row }">
    <el-rate :model-value="Number(row.star_rating) || 3" disabled :max="5" />
  </template>
</el-table-column>
```

- [ ] **Step 4: 新增/编辑表单去掉所属课程**

- 从 `form` 移除 `course_id`（或保留但不提交/不展示）。  
- 删除「所属课程」`el-select`、`deletedMountLabel` 相关 UI 与逻辑。  
- `openNew` / `openEdit` 不再设置 `course_id`。  
- `handleSave` 去掉「请选择所属课程」校验；payload **不传** `course_id`（或仅当未来需要再传）：

```ts
const payload = {
  type: form.type,
  stem: form.stem.trim(),
  options: form.type === 'choice' || form.type === 'multi_choice'
    ? form.options.map(item => item.trim()).filter(Boolean)
    : [],
  answer: form.answer.trim(),
  explanation: form.explanation.trim(),
  tags: form.tags.map(item => item.trim()).filter(Boolean),
  star_rating: form.star_rating || 3,
}
```

- 若 `loadCourses` / `writableCourses` / `getCourses` 仅服务于课程下拉，一并删除无用 import 与调用。  
- 导入说明：课程名称改为「可选；不填则写入独立共享题」；题型仍说明英文码（Excel 技术列）。

- [ ] **Step 5: 作业页空状态文案**

`TeacherAnnouncements.vue`：

```text
题库暂无题目，请先到共享题库中新增或导入题目。
```

- [ ] **Step 6: 浏览器手测清单（本地）**

1. 菜单显示「共享题库」。  
2. 第 1 页序号 1…N，第 2 页从 N+1 起。  
3. 无「所属课程」列；题型中文；星级可见（至少 3 星）。  
4. 新增不选课、填标签可保存。  
5. 非本人题编辑仍禁用。

- [ ] **Step 7: Commit**

```bash
git add frontend/src/views/teacher/TeacherQuestions.vue frontend/src/views/teacher/TeacherLayout.vue frontend/src/router/index.ts frontend/src/views/teacher/TeacherAnnouncements.vue
git commit -m "feat(teacher): 共享题库列表与标签入库对齐"
```

---

## Task 3: 管理员端前端 — 展示与教师对齐

**Files:**
- Modify: `frontend/src/views/admin/AdminQuestionBank.vue`

- [ ] **Step 1: 序号列替换 ID 列**

删除：

```vue
<el-table-column prop="id" label="ID" width="80" />
```

改为：

```vue
<el-table-column label="序号" width="70">
  <template #default="{ $index }">
    {{ (page - 1) * pageSize + $index + 1 }}
  </template>
</el-table-column>
```

（`page` / `pageSize` 使用页面已有分页状态变量名；若变量名不同则对齐现有 `ref`。）

- [ ] **Step 2: 题型中文 + 星标**

```vue
<el-table-column label="题型" width="100">
  <template #default="{ row }">
    <el-tag size="small" effect="plain">
      {{ row.type === 'choice' ? '选择题' : row.type === 'multi_choice' ? '多选题' : row.type === 'fill' ? '填空题' : row.type }}
    </el-tag>
  </template>
</el-table-column>
<el-table-column label="星级" width="140">
  <template #default="{ row }">
    <el-rate :model-value="Number(row.star_rating) || 3" disabled :max="5" />
  </template>
</el-table-column>
```

删除数字列 `prop="star_rating"` 与「原挂载课程」列。

- [ ] **Step 3: 新增表单弱化挂载课**

- 删除或折叠「原始挂载公共课」为非必填；默认不展示强依赖文案。  
- 推荐：**直接去掉新建时的挂载选择**，始终 `mountCourseId = null` 创建独立题（与「只靠标签」一致）。  
- 导入区：挂载公共课改为可选说明「可不选」；勿再强调必须挂课。  
- 列表筛选区题型 option 文案与教师端统一（选择题/多选题/填空题）。

- [ ] **Step 4: 页标题确认**

保持 `h1`「共享题库」（已有）；副文案改为强调标签维度，例如：

```text
全站共享题目维护；以标签、题型、星级组织，不按课程划分。
```

- [ ] **Step 5: 手测**

1. 无 ID 列、无原挂载课程列。  
2. 中文题型 + 星标默认 3。  
3. 序号跨页连续。  
4. 删除/批量删除/贡献 Tab 仍可用。  
5. 新增不选课成功。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/admin/AdminQuestionBank.vue
git commit -m "feat(admin): 共享题库列表展示与教师端对齐"
```

---

## Task 4: 静态测试与文案断言

**Files:**
- Modify: `frontend/tests/teacher-question-bank-static.test.mjs`
- Modify: `frontend/tests/admin-question-star-rating-static.test.mjs`
- Modify: `frontend/tests/admin-question-bank-static.test.mjs`
- Modify: `frontend/tests/copy-consistency-static.test.mjs`

- [ ] **Step 1: 教师静态测试更新**

在 `teacher-question-bank-static.test.mjs` 追加/替换为：

```js
assert.match(page, /共享题库/, '教师端页标题或文案应使用共享题库')
assert.doesNotMatch(page, /label="所属课程"/, '共享题库列表不应再展示所属课程列')
assert.match(page, /选择题/, '题型应中文展示')
assert.match(page, /<el-rate[\s\S]*disabled[\s\S]*:max="5"/, '列表星级应使用只读 el-rate')
assert.match(page, /\(page\s*-\s*1\)\s*\*\s*pageSize/, '序号应跨页连续计算')
assert.doesNotMatch(page, /请选择所属课程/, '新增不应强制选择所属课程')
```

- [ ] **Step 2: 管理端星级/列表静态测试**

`admin-question-star-rating-static.test.mjs`：

```js
assert.match(page, /<el-rate[\s\S]*disabled[\s\S]*:max="5"|:model-value="Number\(row\.star_rating\)/, '列表应用星标展示星级')
assert.doesNotMatch(page, /prop="id"\s+label="ID"/, '列表不应再暴露数据库 ID 列')
assert.doesNotMatch(page, /label="原挂载课程"/, '列表应去掉原挂载课程列')
assert.match(page, /选择题|多选题|填空题/, '题型应中文展示')
```

`admin-question-bank-static.test.mjs`：按文件现有风格补充「序号跨页」「无 course 列」断言，避免与批量删除断言冲突。

- [ ] **Step 3: 文案一致性**

`copy-consistency-static.test.mjs`：

```js
assert.match(
  teacherAnnouncements,
  /请先到共享题库中新增或导入题目/,
  '作业选题空状态应指向共享题库',
)
// 删除或改写旧断言：
// /请先到题库管理中新增或导入题目/
```

若有断言依赖教师页「题库管理」标题，改为「共享题库」。

- [ ] **Step 4: 跑前端静态测试**

```powershell
node frontend/tests/teacher-question-bank-static.test.mjs
node frontend/tests/admin-question-star-rating-static.test.mjs
node frontend/tests/admin-question-bank-static.test.mjs
node frontend/tests/copy-consistency-static.test.mjs
```

Expected: 全部 passed。

- [ ] **Step 5: type-check + build**

```powershell
cd frontend
npm run type-check
npm run build
```

Expected: 通过。

- [ ] **Step 6: Commit**

```bash
git add frontend/tests
git commit -m "test: 共享题库对齐静态断言"
```

---

## Task 5: 文档与知识图

**Files:**
- Modify: `backend/docs/项目修改记录.md`
- Modify: `AGENTS.md`
- Modify: `docs/superpowers/project-map.md`（简短一条）

- [ ] **Step 1: 修改记录第 72 轮**

在 `backend/docs/项目修改记录.md` 文首或最新轮次后追加：

```markdown
## 第 72 轮：共享题库两端展示与标签入库对齐

### 变更
- 教师/管理端统一命名「共享题库」
- 列表：中文题型、el-rate 星标（默认 3）、跨页连续序号；去掉课程列
- 教师新增题目 `course_id` 可选；导入课程名称可选
- 权限差异保留：仅管理员删除/批量/贡献

### 服务器部署影响
- 需要：拉取代码、重启后端、重新构建并发布前端
- 不需要：数据库迁移、Nginx、环境变量（以服务器库已含 star_rating 与 course_id 可空为准；若极旧库缺列再跑既有 schema_compat）
```

- [ ] **Step 2: AGENTS.md 原则**

在「原则」列表增加/改写：

```markdown
- 教师端与管理员端共享题库统一命名「共享题库」；列表展示对齐（中文题型、星标、跨页连续序号、不以课程列组织）；新增题目以标签为主、不强制挂载课程。删除/批量删除/贡献记录仅管理员具备；教师可新增并编辑本人题目。
```

更新「进行中/待实施」：本计划路径写入待实施或完成后勾选。

- [ ] **Step 3: project-map 一条**

记录 2026-07-17 共享题库 UI 对齐与可选 `course_id` 创建。

- [ ] **Step 4: graphify**

```bash
graphify update .
```

- [ ] **Step 5: Commit**

```bash
git add backend/docs/项目修改记录.md AGENTS.md docs/superpowers/project-map.md docs/superpowers/plans/2026-07-17-shared-question-bank-ui-alignment.md
git commit -m "docs: 共享题库两端对齐计划与修改记录"
```

---

## Task 6: 回归与验收门

- [ ] **Step 1: 后端回归**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_teacher_question_optional_course.py backend/tests/test_admin_question_bank.py backend/tests/test_public_question_contribution.py backend/tests/test_question_import_skip.py -q
```

Expected: PASS。

- [ ] **Step 2: 前端回归**

```powershell
$tests = @(
  'teacher-question-bank-static.test.mjs',
  'admin-question-star-rating-static.test.mjs',
  'admin-question-bank-static.test.mjs',
  'admin-question-batch-delete-static.test.mjs',
  'copy-consistency-static.test.mjs'
)
foreach ($t in $tests) { node "frontend/tests/$t" }
cd frontend; npm run type-check; npm run build
```

Expected: 全部通过。

- [ ] **Step 3: 验收勾选**

| # | 项 | 通过 |
|---|----|------|
| 1 | 两端名称均为「共享题库」 | ☐ |
| 2 | 题型中文 | ☐ |
| 3 | 星标展示，默认可见 3 星 | ☐ |
| 4 | 无课程列 | ☐ |
| 5 | 新增不强制课程，标签可入库 | ☐ |
| 6 | 序号跨页连续 | ☐ |
| 7 | 教师无删除；管理有删除/批量/贡献 | ☐ |
| 8 | 测试与 build 通过 | ☐ |

- [ ] **Step 4: 服务器部署说明（写入总结）**

- 需要：`git pull`、重启 `tongshi-backend`、前端 `npm run build` 并同步静态资源。  
- 不需要：新迁移（正常库）。  
- 线上星级不显示：优先确认本轮前端已部署，而非清 MySQL 缓存。

---

## 风险与回滚

| 风险 | 处理 |
|------|------|
| 旧前端仍传 `course_id` | Schema 仍接受可选 int，兼容 |
| 导入模板仍含课程列 | 列保留为可选，空则独立题 |
| 静态测试过严误伤管理删除能力 | 不断言删除按钮消失 |
| `QuestionUpdate` 继承 `QuestionCreate` 后 `course_id` 可选 | 更新时不传则 `exclude_unset` 不改挂载，符合预期 |
| 线上缺 `star_rating` 列 | 启动 `schema_compat` / 既有迁移路径；本计划不新写迁移 |

回滚：还原本计划涉及 commit；数据层无破坏性迁移。

---

## 自检（对照用户需求）

| 需求 | 任务 |
|------|------|
| 题型中文标签 | Task 2、3 |
| 星标展示（默认 3） | Task 2、3；线上靠部署 |
| 删除课程列 | Task 2、3 |
| 新增只要标签（不强制课） | Task 1、2、3 |
| 统一叫共享题库 | Task 2、4、5 |
| 全局连续序号 | Task 2、3 |
| 部分功能差异保留 | 范围「不做」+ 验收 #7 |

无 TBD 占位；未纳入删阶段级联与整页换肤。

---

## 执行方式建议

Plan complete and saved to `docs/superpowers/plans/2026-07-17-shared-question-bank-ui-alignment.md`.

**Two execution options:**

1. **Subagent-Driven（推荐）** — 每任务新开子代理，任务间复核  
2. **Inline Execution** — 本会话按 `executing-plans` 连续执行并设检查点  

Which approach?
