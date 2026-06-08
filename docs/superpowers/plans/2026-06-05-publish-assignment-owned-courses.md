# 发布作业自有课程范围实施计划

> **状态：✅ 已完成**（2026-06-05 提交 `7653723`，announcement_service.py 已只按 created_by 过滤）

> **给 agentic workers：** 必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` 按任务逐项实施。本计划使用复选框跟踪进度。

**目标：** 教师发布作业时，课程下拉框只显示教师自己的课程；公共课程源不显示，也不能被后端直接用于发布。

**架构：** 前端在发布作业页复用现有 `getCourses()` 返回的 `is_owner` 字段，按教师自有课程过滤下拉框。后端在发布服务中把课程校验从“自有或公共”收紧为“仅自有”，防止绕过前端直接提交公共课程源。测试优先覆盖公共课程源不可发布、添加公共课程后生成的教师副本可发布。

**技术栈：** Vue 3 `<script setup lang="ts">`、Element Plus、FastAPI、SQLAlchemy、pytest。

---

## 文件结构

- 修改：`frontend/src/views/teacher/TeacherAnnouncements.vue`
  - 负责发布作业页面的课程下拉框、默认课程选择、题目加载触发。
- 修改：`backend/app/services/announcement_service.py`
  - 负责发布作业的服务层权限校验，必须作为最终权限边界。
- 修改：`backend/tests/test_integration_bugfixes.py`
  - 增加发布作业课程范围回归测试。
- 验证：`frontend` 下执行 `npm run build`，`backend` 下执行受影响 pytest。

## 范围

本次只处理发布作业入口的课程范围。

范围内：
- 发布作业弹窗“所属课程”只显示 `is_owner === true` 的课程。
- 默认选择第一门自有课程。
- 没有自有课程时，不自动选择公共课程。
- 后端拒绝教师直接用公共课程源发布作业。
- 教师添加公共课程后生成的自有副本仍可发布作业。

范围外：
- 不改变课程管理页公共课程添加流程。
- 不改变 `/courses` 通用列表接口的返回结构。
- 不调整题库、资料、班级管理页的现有过滤逻辑。
- 不处理公共课程同步机制。

## 验收口径

- 发布作业下拉框中不出现 `is_public=true && is_owner=false` 的公共课程源。
- 教师不能通过接口直接提交公共课程源 `course_id` 发布作业。
- 教师添加公共课程后，使用生成的自有副本 `course_id` 可以发布作业。
- 前端构建通过。
- 受影响后端测试通过。

---

### Task 1: 写后端失败测试

**文件：**
- 修改：`backend/tests/test_integration_bugfixes.py`
- 测试：`backend/tests/test_integration_bugfixes.py::TestTeacherRefactor::test_publish_assignment_rejects_public_source_course`
- 测试：`backend/tests/test_integration_bugfixes.py::TestTeacherRefactor::test_publish_assignment_allows_owned_copy_of_public_course`

- [x] **Step 1: 添加公共课程源不可发布测试**

在 `TestTeacherRefactor` 中添加测试，位置建议放在 `test_publish_questions_supports_multiple_classes_and_completion_report` 附近：

```python
    def test_publish_assignment_rejects_public_source_course(self, client, db_session, teacher_token):
        public_course = Course(name="不可直接发布公共课程", created_by="admin", is_public=True)
        db_session.add(public_course)
        db_session.flush()
        public_question = Question(
            type="choice",
            course_id=public_course.id,
            stem="公共课程源题目",
            options=["A", "B"],
            answer="A",
        )
        db_session.add(public_question)
        db_session.commit()

        resp = client.post(
            "/api/announcements",
            json={
                "course_id": public_course.id,
                "class_ids": [1],
                "title": "不应发布",
                "question_ids": [public_question.id],
            },
            headers=auth_header(teacher_token),
        )
        data = resp.json()

        assert data["code"] == 404
        assert "课程不存在" in data["message"]
```

- [x] **Step 2: 添加公共课程副本可发布测试**

继续在 `TestTeacherRefactor` 中添加测试：

```python
    def test_publish_assignment_allows_owned_copy_of_public_course(self, client, db_session, teacher_token):
        public_course = Course(name="可发布公共课程副本", created_by="admin", is_public=True)
        db_session.add(public_course)
        db_session.flush()
        db_session.add(Question(
            type="choice",
            course_id=public_course.id,
            stem="公共课程源同步题目",
            options=["A", "B"],
            answer="A",
        ))
        db_session.commit()

        copy_resp = client.post(
            f"/api/questions/courses/{public_course.id}/add",
            headers=auth_header(teacher_token),
        ).json()
        assert copy_resp["code"] == 0
        copied_course_id = copy_resp["data"]["id"]

        copied_question = db_session.query(Question).filter(
            Question.course_id == copied_course_id,
            Question.source_question_id.isnot(None),
        ).first()
        assert copied_question is not None

        cls = Class(name="公共副本班级", course_id=copied_course_id, created_by="T001")
        db_session.add(cls)
        db_session.commit()

        resp = client.post(
            "/api/announcements",
            json={
                "course_id": copied_course_id,
                "class_ids": [cls.id],
                "title": "公共副本作业",
                "question_ids": [copied_question.id],
            },
            headers=auth_header(teacher_token),
        )
        data = resp.json()

        assert data["code"] == 0
        assert data["data"]["course_id"] == copied_course_id
```

- [x] **Step 3: 运行新测试确认至少第一条失败**

```powershell
cd backend
pytest tests/test_integration_bugfixes.py::TestTeacherRefactor::test_publish_assignment_rejects_public_source_course -q
```

预期：当前实现会返回 `400` 的“目标班级必须属于所选课程”或其他非 `404` 结果，说明公共课程源仍通过了课程存在校验。

---

### Task 2: 收紧后端发布课程权限

**文件：**
- 修改：`backend/app/services/announcement_service.py`
- 测试：`backend/tests/test_integration_bugfixes.py`

- [x] **Step 1: 移除发布服务中的公共课程访问条件**

把 `create_announcement()` 中课程查询从：

```python
    course = db.query(Course).filter(
        Course.id == course_id,
        or_(Course.created_by == teacher_id, Course.is_public.is_(True)),
    ).first()
```

改为：

```python
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.created_by == teacher_id,
    ).first()
```

- [x] **Step 2: 清理无用导入**

如果 `announcement_service.py` 中 `or_` 不再被使用，删除：

```python
from sqlalchemy import or_
```

- [x] **Step 3: 运行后端发布范围测试**

```powershell
cd backend
pytest tests/test_integration_bugfixes.py::TestTeacherRefactor::test_publish_assignment_rejects_public_source_course tests/test_integration_bugfixes.py::TestTeacherRefactor::test_publish_assignment_allows_owned_copy_of_public_course -q
```

预期：两条测试都通过。

- [x] **Step 4: 运行相关发布作业回归测试**

```powershell
cd backend
pytest tests/test_integration_bugfixes.py::TestTeacherRefactor::test_publish_questions_supports_multiple_classes_and_completion_report -q
```

预期：通过。

---

### Task 3: 过滤发布作业页课程下拉框

**文件：**
- 修改：`frontend/src/views/teacher/TeacherAnnouncements.vue`

- [x] **Step 1: 增加自有课程计算属性**

在 `courses` 定义后增加：

```ts
const ownedCourses = computed(() => courses.value.filter(course => course.is_owner))
```

- [x] **Step 2: 默认选择自有课程**

把 `openCreate()` 里的：

```ts
    course_id: courses.value[0]?.id || '',
```

改为：

```ts
    course_id: ownedCourses.value[0]?.id || '',
```

- [x] **Step 3: 下拉框改用自有课程列表**

把模板中的课程选项：

```vue
          <el-option v-for="course in courses" :key="course.id" :label="course.name" :value="course.id" />
```

改为：

```vue
          <el-option v-for="course in ownedCourses" :key="course.id" :label="course.name" :value="course.id" />
```

- [x] **Step 4: 保持已有题目加载和班级联动**

不改 `targetClasses`、`watch(() => form.course_id, ...)` 和 `loadQuestions()` 的数据流。它们会基于新的自有课程选项继续工作。

- [x] **Step 5: 前端构建验证**

```powershell
cd frontend
npm run build
```

预期：构建通过，且没有 TypeScript 类型错误。

---

### Task 4: 总体验证和图谱同步

**文件：**
- 修改：`graphify-out/graph.json` 等图谱输出文件，具体由 `graphify update .` 自动生成。

- [x] **Step 1: 运行受影响后端测试**

```powershell
cd backend
pytest tests/test_integration_bugfixes.py::TestTeacherRefactor::test_publish_assignment_rejects_public_source_course tests/test_integration_bugfixes.py::TestTeacherRefactor::test_publish_assignment_allows_owned_copy_of_public_course tests/test_integration_bugfixes.py::TestTeacherRefactor::test_publish_questions_supports_multiple_classes_and_completion_report -q
```

预期：全部通过。

- [x] **Step 2: 运行前端构建**

```powershell
cd frontend
npm run build
```

预期：构建通过。

- [x] **Step 3: 同步代码图谱**

```powershell
graphify update .
```

预期：图谱更新完成。如本地 `graphify` 命令不可用，记录无法同步图谱的原因。

- [x] **Step 4: 检查工作区差异**

```powershell
git status --short
git diff -- frontend/src/views/teacher/TeacherAnnouncements.vue backend/app/services/announcement_service.py backend/tests/test_integration_bugfixes.py
```

预期：只出现本任务相关改动；已有用户改动不被回滚。

## 风险点

- `/courses` 仍会给课程管理页返回公共课程源，这是预期行为，不应在本任务中改接口结构。
- `getCourseQuestions()` 对教师仍允许查看公共课程题目，这是题库浏览/添加公共课程流程的一部分，本任务不收紧该权限。
- 发布作业必须以后端服务层为最终边界，前端过滤只是交互层优化。

## 自检结果

- 需求覆盖：下拉框过滤、后端拒绝公共源、公共副本可发布、验证命令均已覆盖。
- 占位符扫描：未发现占位内容。
- 类型一致性：使用现有 `Course.is_owner`、`Question.source_question_id`、`Class.course_id` 字段，未引入新接口字段。
