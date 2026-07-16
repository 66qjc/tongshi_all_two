# 移除课程「课时」功能实施计划

> **面向执行代理：** 必须按复选框逐项执行；开始编码前使用 `test-driven-development`，分任务执行时使用 `subagent-driven-development` 或 `executing-plans`，完成前使用 `verification-before-completion`。本文件仅是实施计划，当前未授权修改业务代码。

**目标：** 从产品界面、前端调用和后端公开接口中完整移除「课时」及课时级学习进度，让课程学习统一围绕阶段化资料（PDF、视频、链接）展开。

**架构：** 采用“产品与 API 全链路下线、历史数据暂留”的一次性切换方案。前端只保留资料目录和 `MaterialInlineReader`；后端注销课时与进度路由并清理对应服务，但保留 `lessons`、`lesson_progress`、`course_progress` 表、ORM 和历史迁移，保证数据可回滚且本轮不做数据库变更。

**技术栈：** Vue 3、TypeScript、Vite、Element Plus、FastAPI、SQLAlchemy、Pytest、Node.js 静态回归测试。

**计划状态：** 方案已收敛，等待用户明确说“执行计划”或“开始写代码”后实施。

---

## 一、问题与已核实现状

当前「课时」不是孤立页面，而是一条已经贯通的业务链：

- 教师端 `TeacherCourseDetail.vue` 提供课时增删改、排序、富文本编辑和课时学习分析。
- 学生端 `CourseDetailView.vue` 默认进入课时模式，包含目录、正文阅读、上一课/下一课、完成本课、30 秒心跳和离页补报。
- `LearnView.vue` 对每门已加入课程额外请求课时列表与课时进度，用 `lesson_id` 恢复阅读位置。
- 后端 `lessons.py -> lesson_service.py -> Lesson` 提供课时 CRUD；`progress.py -> progress_service.py -> LessonProgress/CourseProgress` 提供课时进度、班级学生进度和课程分析。
- 公开学习接口提供已发布课时列表，并在公开课程列表和详情中返回 `lesson_count`。
- 现有删除课时逻辑已经会清空 `course_progress.last_lesson_id` 并删除对应 `lesson_progress`；本计划不是补做删除功能，而是退役整条产品能力。

移除课时后，阶段 `CourseStage` 仍然保留。阶段是资料目录结构，不等同于课时，也不在本次删除范围内。

## 二、已确定决策

本计划不再保留需要执行者临场选择的分支，统一按以下决策实施：

1. **采用全链路下线方案。** 教师、学生、游客均不再看到或调用课时能力。
2. **教师端学习分析一并移除。** 当前分析完全依赖 `LessonProgress`，本轮不返回空结构、不显示“已下线”占位，也不伪装成资料分析。
3. **后端路由直接注销。** 退役路径从 OpenAPI 中消失，并返回真实 HTTP 404；不保留固定返回 0、空数组或兼容成功响应。
4. **公开课程响应删除 `lesson_count`。** 前后端类型同步移除，不保留固定为 0 的废字段。
5. **课程详情只保留资料直读。** 不再保留单选项 Tab；页面直接展示阶段资料目录、正文阅读区和资料导读。
6. **旧链接平滑降级。** `/learn/course/:id?lesson_id=...` 和 `?tab=lessons` 不报错、不显示空白页。新页面不读取这些废弃查询参数，由 Vue Router 自然忽略并直接进入资料阅读。
7. **历史数据只读保留。** 不清空、不迁移、不回填 `lessons`、`lesson_progress`、`course_progress`，也不删除 ORM、兼容建表逻辑和历史迁移。
8. **不新增资料级进度。** 页面不得继续出现“登录后可保存学习进度”“继续上次课时”“已学百分比”等无法兑现的文案。

## 三、范围边界

### 本轮包含

- 教师端课时 CRUD、排序、富文本编辑器和课时学习分析下线。
- 学生端/游客端课时目录、课时阅读器、课时导航、课时完成和进度上报下线。
- 课时 API、课时进度 API、班级课时进度 API、课程课时分析 API 下线。
- 公开课程 `lesson_count` 和公开课时列表下线。
- wangEditor 依赖、专用分包配置、专用类型声明和专用测试清理。
- 全站直接描述「课时」或课时进度的有效文案同步。
- 后端、前端、文档、知识图谱和服务器部署影响同步记录。

### 本轮不包含

- 不新增资料完成状态、资料观看百分比、资料学习时长或资料级分析。
- 不删除 `Lesson`、`LessonProgress`、`CourseProgress` ORM。
- 不执行 `DROP TABLE`、数据清理、数据迁移或历史课时转资料。
- 不删除 `backend/migrations/versions/20260629_add_lessons_course_progress.py`。
- 不删除 `schema_compat.py` 中历史表兼容逻辑，也不修改对应兼容测试。
- 不修改阶段、资料上传、资料预览、作业、题库、作品、班级等业务语义。
- 不改 Nginx、Redis、环境变量或文件存储配置。
- 不改写历史设计/实施文档的原始结论；只在当前稳定文档中标注课时能力已退役。

## 四、退役接口契约

实施完成后，下列路径不得出现在 `/openapi.json` 中，直接访问必须返回 HTTP 404：

| 方法 | 路径 | 原能力 |
|---|---|---|
| `GET` / `POST` | `/api/courses/{course_id}/lessons` | 课时列表 / 新增课时 |
| `GET` / `PUT` / `DELETE` | `/api/lessons/{lesson_id}` | 课时详情 / 编辑 / 删除 |
| `POST` | `/api/courses/{course_id}/lessons/reorder` | 课时排序 |
| `GET` / `POST` | `/api/courses/{course_id}/progress` | 课时级课程进度 |
| `POST` | `/api/courses/{course_id}/lessons/{lesson_id}/progress` | 课时心跳与完成上报 |
| `GET` | `/api/classes/{class_id}/students/{student_id}/progress` | 教师查看学生课时进度 |
| `GET` | `/api/courses/{course_id}/analytics` | 课时学习分析 |
| `GET` | `/api/public/learning/courses/{course_id}/lessons` | 游客读取公开课时 |

仍保留的公开学习接口：

- `GET /api/public/learning/courses`
- `GET /api/public/learning/courses/{course_id}`
- `GET /api/public/learning/materials`
- `GET /api/public/learning/materials/{material_id}/file`

公开课程列表和详情继续返回 `material_count`，但不再返回 `lesson_count`。

## 五、文件变更清单

### 后端删除

- `backend/app/api/v1/routes/lessons.py`
- `backend/app/api/v1/routes/progress.py`
- `backend/app/services/lesson_service.py`
- `backend/app/services/progress_service.py`
- `backend/app/core/html_sanitizer.py`
- `backend/tests/test_lessons_progress.py`
- `backend/tests/test_progress_analytics_scale.py`
- `backend/tests/test_progress_concurrency.py`

### 后端新增或修改

- 修改 `backend/app/api/v1/__init__.py`：移除 `lessons_router`、`progress_router` 的导入和注册。
- 修改 `backend/app/api/v1/routes/public_learning_routes.py`：删除公开课时路由和服务导入。
- 修改 `backend/app/services/public_learning_service.py`：移除 `Lesson`、`lesson_count` 和 `list_public_lessons`，只统计/输出资料。
- 修改 `backend/app/schemas/common.py`：删除 `LessonCreate`、`LessonUpdate`、`LessonOut`、`LessonReorderItem`、`CourseProgressIn/Out`、`LessonProgressIn/Out`、`CourseProgressSummaryOut`。
- 修改 `backend/app/services/notification_service.py`：移除 `course_lesson_published` 事件映射，保留资料与课程公告通知。
- 修改 `backend/tests/test_public_learning.py`：删除课时夹具和课时断言，增加响应无 `lesson_count` 的断言。
- 新增 `backend/tests/test_removed_lesson_endpoints.py`：锁定全部退役路径均为 HTTP 404。

### 前端删除

- `frontend/src/api/lesson.ts`
- `frontend/src/api/progress.ts`
- `frontend/src/components/lesson/CourseToc.vue`
- `frontend/src/components/lesson/LessonEditor.vue`
- `frontend/src/components/lesson/LessonReader.vue`
- `frontend/src/components/lesson/PrevNextNav.vue`
- `frontend/src/components/lesson/AuthenticatedLessonVideo.vue`
- `frontend/tests/lesson-completion-static.test.mjs`
- `frontend/tests/lesson-progress-reporting-static.test.mjs`
- `frontend/tests/teacher-course-analytics-static.test.mjs`
- `frontend/tests/editor-vendor-splitting-static.test.mjs`

### 前端新增或修改

- 修改 `frontend/src/views/CourseDetailView.vue`：删除课时和进度分支，资料直读成为唯一主路径。
- 修改 `frontend/src/views/LearnView.vue`：删除课时/进度请求、课时数、完成率和 `lesson_id` 跳转，仅展示资料数并进入课程资料。
- 修改 `frontend/src/views/teacher/TeacherCourseDetail.vue`：删除课时、分析和富文本编辑逻辑，只保留课程信息、阶段与资料管理。
- 修改 `frontend/src/api/publicLearning.ts`：删除 `Lesson` 依赖、`getPublicLessons`、`normalizeLesson` 和 `lesson_count` 类型归一化。
- 修改 `frontend/package.json`、`frontend/package-lock.json`：移除两个 `@wangeditor` 依赖。
- 修改 `frontend/env.d.ts`：删除 wangEditor 专用模块声明。
- 修改 `frontend/vite.config.ts`：删除 `vendor-wangeditor` 手工分包规则，保留其他分包配置。
- 修改 `frontend/tests/public-learning-static.test.mjs`：从课时阅读断言改为资料唯一主路径断言。
- 修改 `frontend/tests/course-detail-layout-static.test.mjs`：改为验证 `material-doc-shell` 三栏和移动端资料布局。
- 修改 `frontend/tests/local-file-preview-static.test.mjs`：删除课时视频断言，保留资料直读、预览和私有文件鉴权断言。
- 修改 `frontend/tests/chunk-optimization-static.test.mjs`：删除 LessonEditor 动态分包断言，保留 ECharts 和 Element Plus 优化断言。
- 新增 `frontend/tests/material-only-learning-static.test.mjs`：锁定课时文件不存在、学习页不再发起课时/进度请求。
- 修改有效产品文案：`TeacherDashboard.vue`、`TeacherLayout.vue`、`InboxView.vue`、`AboutView.vue`、`PrivacyView.vue`、`components/home/HeroSection.vue`、`CoursePreview.vue`、`StatsSection.vue`、`ModuleShowcase.vue`。

### 明确保留

- `backend/app/models/entities.py` 中 `Course.lessons`、`Lesson`、`CourseProgress`、`LessonProgress`。
- `backend/app/db/schema_compat.py` 中 `lessons`、`course_progress`、`lesson_progress` 兼容建表逻辑。
- `backend/tests/test_schema_compat.py` 中相应兼容测试。
- `backend/migrations/versions/20260629_add_lessons_course_progress.py`。
- `frontend/src/components/learn/MaterialInlineReader.vue` 及资料文件鉴权、Range、预览生成相关能力。

## 六、实施任务

### Task 1：先建立退役契约测试

**文件：**

- 新增：`backend/tests/test_removed_lesson_endpoints.py`
- 新增：`frontend/tests/material-only-learning-static.test.mjs`

- [ ] **Step 1：编写后端退役路径测试**

核心用例使用真实 HTTP 状态码，不能只检查业务响应中的 `code`：

```python
"""课时与课时进度接口退役回归测试。"""

import pytest


RETIRED_ENDPOINTS = [
    ("GET", "/api/courses/1/lessons", "/api/courses/{course_id}/lessons"),
    ("POST", "/api/courses/1/lessons", "/api/courses/{course_id}/lessons"),
    ("GET", "/api/lessons/1", "/api/lessons/{lesson_id}"),
    ("PUT", "/api/lessons/1", "/api/lessons/{lesson_id}"),
    ("DELETE", "/api/lessons/1", "/api/lessons/{lesson_id}"),
    ("POST", "/api/courses/1/lessons/reorder", "/api/courses/{course_id}/lessons/reorder"),
    ("GET", "/api/courses/1/progress", "/api/courses/{course_id}/progress"),
    ("POST", "/api/courses/1/progress", "/api/courses/{course_id}/progress"),
    (
        "POST",
        "/api/courses/1/lessons/1/progress",
        "/api/courses/{course_id}/lessons/{lesson_id}/progress",
    ),
    (
        "GET",
        "/api/classes/1/students/2025001/progress",
        "/api/classes/{class_id}/students/{student_id}/progress",
    ),
    ("GET", "/api/courses/1/analytics", "/api/courses/{course_id}/analytics"),
    (
        "GET",
        "/api/public/learning/courses/1/lessons",
        "/api/public/learning/courses/{course_id}/lessons",
    ),
]


@pytest.mark.parametrize(("method", "path", "template"), RETIRED_ENDPOINTS)
def test_retired_lesson_endpoint_returns_http_404(
    client,
    method: str,
    path: str,
    template: str,
):
    response = client.request(method, path)
    assert response.status_code == 404


def test_retired_lesson_paths_are_absent_from_openapi(client):
    paths = client.get("/openapi.json").json()["paths"]
    retired_templates = {template for _, _, template in RETIRED_ENDPOINTS}
    assert retired_templates.isdisjoint(paths)
```

- [ ] **Step 2：运行后端新测试，确认在旧路由仍注册时失败**

工作目录：`backend`

```powershell
pytest tests/test_removed_lesson_endpoints.py -q
```

预期：至少一个用例失败，证明测试能识别仍存在的课时路由。

- [ ] **Step 3：编写前端资料唯一主路径静态测试**

测试必须覆盖：`api/lesson.ts`、`api/progress.ts` 和五个课时组件不存在；`LearnView` 不含 `lesson_id`、`lesson_count` 和课时进度请求；`CourseDetailView` 只引用 `MaterialInlineReader`，且不读取旧课时查询参数。

```javascript
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = relativePath => readFileSync(resolve(root, relativePath), 'utf8')

const retiredFiles = [
  'src/api/lesson.ts',
  'src/api/progress.ts',
  'src/components/lesson/CourseToc.vue',
  'src/components/lesson/LessonEditor.vue',
  'src/components/lesson/LessonReader.vue',
  'src/components/lesson/PrevNextNav.vue',
  'src/components/lesson/AuthenticatedLessonVideo.vue',
]

for (const relativePath of retiredFiles) {
  assert.equal(existsSync(resolve(root, relativePath)), false, `${relativePath} 应已删除`)
}

const learn = read('src/views/LearnView.vue')
assert.doesNotMatch(
  learn,
  /lesson_id|lesson_count|getLessons|getCourseProgress|progressMap|课时/,
  '教程列表不得再依赖课时和课时进度',
)
assert.match(learn, /material_count/, '教程卡片应继续展示资料数量')

const detail = read('src/views/CourseDetailView.vue')
assert.match(detail, /MaterialInlineReader/, '课程详情应保留资料直读器')
assert.doesNotMatch(
  detail,
  /CourseToc|LessonReader|PrevNextNav|reportLessonProgress|lesson_id|activeTab|完成本课|课时/,
  '课程详情不得再读取或渲染课时能力',
)

const publicApi = read('src/api/publicLearning.ts')
assert.doesNotMatch(
  publicApi,
  /getPublicLessons|normalizeLesson|lesson_count|from ['"]\.\/lesson['"]/,
  '公开学习 API 不得保留课时契约',
)

const packageJson = read('package.json')
const viteConfig = read('vite.config.ts')
assert.doesNotMatch(packageJson, /@wangeditor/, '前端依赖应移除 wangEditor')
assert.doesNotMatch(viteConfig, /vendor-wangeditor|@wangeditor/, 'Vite 应移除 wangEditor 专用分包')

console.log('资料唯一学习主路径静态检查通过')
```

- [ ] **Step 4：运行前端新测试，确认在旧课时代码仍存在时失败**

工作目录：`frontend`

```powershell
node tests/material-only-learning-static.test.mjs
```

预期：因课时文件或课时调用仍存在而失败。

### Task 2：下线后端课时与进度能力

**文件：**

- 修改：`backend/app/api/v1/__init__.py`
- 修改：`backend/app/api/v1/routes/public_learning_routes.py`
- 修改：`backend/app/services/public_learning_service.py`
- 修改：`backend/app/schemas/common.py`
- 修改：`backend/app/services/notification_service.py`
- 修改：`backend/tests/test_public_learning.py`
- 删除：本计划“后端删除”中的路由、服务、清洗器和三个专用测试文件

- [ ] **Step 1：注销课时和进度 Router**

从 `backend/app/api/v1/__init__.py` 同时移除 import 与 `include_router`；不创建兼容 Router。保留 `public_learning_router`，只从中删除公开课时子路由。

- [ ] **Step 2：收窄公开学习服务**

`_format_public_course` 只接收 `material_count`；列表和详情不再查询 `Lesson`，响应中不再出现 `lesson_count`。`list_public_lessons` 和 `format_lesson_out` 依赖一并删除。

- [ ] **Step 3：删除仅由退役路由消费的 Schema 与服务代码**

删除课时/进度 Pydantic Schema、两个路由文件、两个服务文件和 `html_sanitizer.py`。完成后运行导入扫描，保证不存在悬空 import。

- [ ] **Step 4：清理通知事件映射**

从 `NOTIFICATION_PREFERENCE_FIELD_MAP` 删除 `course_lesson_published`，但保留 `enable_course_update`、`course_material_added` 和 `course_announcement`。

- [ ] **Step 5：调整后端测试**

删除三个只验证已退役能力的测试文件；`test_public_learning.py` 保留公开课程、阶段资料、软删除过滤和文件访问测试，新增：

```python
assert "lesson_count" not in course
assert "lesson_count" not in detail
```

- [ ] **Step 6：运行后端定向测试**

工作目录：`backend`

```powershell
pytest tests/test_removed_lesson_endpoints.py tests/test_public_learning.py tests/test_schema_compat.py -q
```

预期：全部通过；兼容表测试继续通过，证明本轮没有误删历史数据库兼容能力。

### Task 3：将学生与游客学习路径收敛为资料直读

**文件：**

- 修改：`frontend/src/views/CourseDetailView.vue`
- 修改：`frontend/src/views/LearnView.vue`
- 修改：`frontend/src/api/publicLearning.ts`
- 删除：`frontend/src/api/lesson.ts`
- 删除：`frontend/src/api/progress.ts`
- 删除：`frontend/src/components/lesson/`

- [ ] **Step 1：先清理 API 类型与调用**

删除课时和进度 API 文件；`PublicCourse` 不再扩展 `lesson_count`，公开课程归一化只处理现有课程计数和阶段资料。全局搜索不得再出现 `getLessons`、`getPublicLessons`、`getCourseProgress`、`reportLessonProgress`、`getCourseAnalytics`。

- [ ] **Step 2：简化 `LearnView.vue`**

删除 `CourseProgressView`、`progressMap`、`loadProgressForCourses`、`courseLessonCount` 和 `lesson_id` 跳转。课程卡片只展示 `material_count`，动作统一为“查看教程”或“查看资料”，所有课程统一进入 `/learn/course/{id}`。

公开课和已加入课程仍按课程 ID 合并；已加入私有课程继续走认证课程详情，公开课程仍可游客访问。移除逐课程请求课时和进度的 N+1 调用。

- [ ] **Step 3：简化 `CourseDetailView.vue` 数据流**

保留两种数据源：登录学生优先读取认证课程详情与资料，失败后再读取公开课程详情。删除 `Lesson`、`CourseProgress`、课时计时器、心跳、离页补报、`activeTab` 和课时查询参数状态。

加载成功后直接计算并选择默认资料；无资料时显示中文空状态。新代码不读取 `lesson_id` 或 `tab`，旧查询参数即使仍在地址栏中也不参与数据选择。

- [ ] **Step 4：简化课程详情模板与样式**

移除课时 Tab、`booksite-layout`、课时目录抽屉、课时正文、上一课/下一课、完成本课和登录保存进度提示。直接渲染现有 `material-doc-shell` 三栏；保留阶段折叠、默认资料选择、上一份/下一份资料、公开/认证文件 URL、预览生成轮询和中文空/错状态。

- [ ] **Step 5：删除课时组件目录并运行静态测试**

工作目录：`frontend`

```powershell
node tests/material-only-learning-static.test.mjs
node tests/public-learning-static.test.mjs
node tests/course-detail-layout-static.test.mjs
node tests/local-file-preview-static.test.mjs
```

预期：资料主路径断言通过，且公开资料和私有文件访问能力没有回退。

### Task 4：清理教师端、学习分析与 wangEditor

**文件：**

- 修改：`frontend/src/views/teacher/TeacherCourseDetail.vue`
- 修改：`frontend/src/views/teacher/TeacherDashboard.vue`
- 修改：`frontend/src/views/teacher/TeacherLayout.vue`
- 修改：`frontend/package.json`
- 修改：`frontend/package-lock.json`
- 修改：`frontend/env.d.ts`
- 修改：`frontend/vite.config.ts`
- 修改：`frontend/tests/chunk-optimization-static.test.mjs`
- 删除：课时、分析、编辑器专用静态测试

- [ ] **Step 1：删除教师端课时状态与交互**

移除 `LessonEditor`、课时表单、资料插入课时正文、课时保存/删除/排序及相关弹窗。删除危险操作确认仅限课时部分，资料删除确认必须保留。

- [ ] **Step 2：删除学习分析状态与界面**

移除 `CourseAnalytics`、分页、加载逻辑、指标卡、学生课时完成表格、热门课时和低完成课时。课程详情只渲染课程信息、阶段与资料管理，不保留单个“资料”Tab 外壳。

- [ ] **Step 3：卸载 wangEditor 依赖并清理构建配置**

工作目录：`frontend`

```powershell
npm uninstall @wangeditor/editor @wangeditor/editor-for-vue
```

随后删除 `env.d.ts` 中专用声明、`vite.config.ts` 中 `vendor-wangeditor` 规则和编辑器分包测试。`chunk-optimization-static.test.mjs` 仅删除 LessonEditor 相关断言，其他性能断言保留。

- [ ] **Step 4：修正教师入口文案**

- `TeacherDashboard.vue`：“维护阶段、资料与课程内容”。
- `TeacherLayout.vue`：注释改为“课程列表 + 阶段/资料管理”。
- 教师课程详情标题、按钮、空状态均不得出现“课时”或“学习分析”。

- [ ] **Step 5：运行教师端和构建配置回归**

工作目录：`frontend`

```powershell
node tests/chunk-optimization-static.test.mjs
node tests/teacher-courses-search-static.test.mjs
npm run type-check
```

预期：全部通过，且 `package-lock.json` 不再包含 `node_modules/@wangeditor/`。

### Task 5：同步有效文案与静态回归

**文件：**

- 修改：`frontend/src/views/InboxView.vue`
- 修改：`frontend/src/views/AboutView.vue`
- 修改：`frontend/src/views/PrivacyView.vue`
- 修改：`frontend/src/components/home/HeroSection.vue`
- 修改：`frontend/src/components/home/CoursePreview.vue`
- 修改：`frontend/src/components/home/StatsSection.vue`
- 修改：`frontend/src/components/home/ModuleShowcase.vue`
- 修改：相关前端静态测试

- [ ] **Step 1：替换有效产品文案**

统一使用“教程”“阶段资料”“学习资料”。通知偏好描述改为“新增资料和课程公告”。首页、关于页不再承诺图文课时或课时目录。

隐私页不能直接声称历史课时数据不存在，应改为准确表述：平台继续保存功能下线前产生的历史课程学习记录，但不再新增课时阅读记录；练习答题和作业完成数据不受影响。

- [ ] **Step 2：更新静态测试中的正向与反向断言**

`public-learning-static.test.mjs`、`local-file-preview-static.test.mjs` 和 `course-detail-layout-static.test.mjs` 不得再读取已删除文件。新增反向断言，保证 `frontend/src` 中无 `lesson_id`、`lesson_count`、`完成本课`、`登录后可保存学习进度` 等退役契约。

- [ ] **Step 3：执行所有前端静态测试**

工作目录：`frontend`

```powershell
Get-ChildItem tests -Filter *.test.mjs | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { throw "静态测试失败：$($_.Name)" } }
```

预期：所有现存 `.test.mjs` 均通过；已删除测试不再出现在文件清单中。

### Task 6：全量验证与浏览器验收

- [ ] **Step 1：后端全量回归**

工作目录：`backend`

```powershell
pytest -q
```

预期：全部通过；允许保留项目既有、已记录的环境条件跳过，但不得新增失败。

- [ ] **Step 2：前端类型检查与生产构建**

工作目录：`frontend`

```powershell
npm run type-check
npm run build
```

预期：类型检查和构建成功；不得再生成 `vendor-wangeditor` chunk。

- [ ] **Step 3：做残留扫描**

```powershell
rg -n "lesson_id|lesson_count|LessonEditor|LessonReader|getLessons|getCourseProgress|reportLessonProgress|getCourseAnalytics|完成本课|课时" frontend/src backend/app/api/v1 backend/app/services backend/app/schemas/common.py
```

预期：无有效业务残留。`entities.py`、`schema_compat.py`、历史迁移和历史文档中的命中属于明确保留项，不应为了清零搜索结果而删除。

- [ ] **Step 4：浏览器验收桌面与移动端**

至少覆盖：

- 游客打开公开教程，直接看到资料目录和直读器。
- 登录学生打开已加入的私有课程，仍能读取认证资料。
- URL 携带 `lesson_id` 或 `tab=lessons` 时自动进入资料页，不白屏、不循环导航。
- 无资料课程显示中文空状态，不出现课程加载失败。
- PDF、视频、链接资料可打开；资料预览生成中的轮询和失败提示正常。
- 教师课程详情可维护阶段、上传/编辑/删除资料，无课时和学习分析入口。
- 桌面三栏、窄屏和移动端均无重叠、横向溢出或乱码。

- [ ] **Step 5：验证历史数据未被修改**

在只读数据库检查中确认 `lessons`、`lesson_progress`、`course_progress` 表仍存在，部署过程未执行删除或更新语句。本步骤只验证表和行数，不导出敏感学习数据。

### Task 7：同步稳定文档、修改记录与知识图谱

**文件：**

- 修改：`docs/superpowers/project-map.md`
- 修改：`docs/superpowers/frontend-guidelines.md`
- 修改：`AGENTS.md`
- 修改：`backend/docs/项目修改记录.md`

- [ ] **Step 1：更新稳定事实**

`project-map.md` 删除当前架构中的 `Lesson`/课时进度业务链和课时路由说明，补充“历史表保留、产品与 API 已下线”。历史修改记录保留原文，但标注已被 2026-07-16 决策取代。

`frontend-guidelines.md` 将教师课程详情规则改为“课程信息 + 阶段资料管理”，学生课程详情改为资料直读唯一主路径。

`AGENTS.md` 更新当前完成状态和长期约定，删除“删除课时时如何处理进度引用”这类已退役业务规则；不得改动与本任务无关的治理优先级。

- [ ] **Step 2：写入项目修改记录**

`backend/docs/项目修改记录.md` 必须记录：问题、最终方案、删除的接口、保留的历史表、验证结果、未验证路径、服务器部署影响。

- [ ] **Step 3：更新知识图谱**

工作目录：项目根目录。

```powershell
graphify update .
```

若本机 `graphify` 解释器仍不可用，记录失败原因；不得声称图谱已更新，也不得因此跳过代码和文档验证。

- [ ] **Step 4：最终差异检查**

```powershell
git status --short
git diff --check
git diff -- docs/superpowers/plans/2026-07-16-remove-course-lessons.md
```

确认没有提交 `.playwright-cli/`、缓存、截图、构建产物或与本任务无关的文件。

当前工作区已有其他未提交修改，本计划默认不包含暂存或提交操作。只有用户明确授权 Git 操作时，才按任务逐文件核对并暂存，禁止使用 `git add frontend`、`git add backend/app` 等宽范围命令。

## 七、验收标准

1. 教师课程详情无课时 CRUD、课时排序、富文本编辑器和学习分析。
2. 学生/游客课程详情只有阶段资料目录、资料直读区和资料导读，无课时 Tab、完成本课、上一课/下一课和进度提示。
3. `/learn` 不显示课时数或学习百分比，不请求课时/进度接口，不生成 `lesson_id` 链接。
4. 本计划接口矩阵中的全部路径从 OpenAPI 消失并返回 HTTP 404。
5. 公开课程列表和详情不返回 `lesson_count`，资料接口与 `material_count` 正常。
6. 旧 `lesson_id`/`tab=lessons` 链接平滑进入资料阅读，无白屏和错误 Toast。
7. wangEditor 源码引用、依赖、类型声明、分包配置和专用测试全部移除。
8. `lessons`、`lesson_progress`、`course_progress` 历史表、ORM、兼容逻辑和迁移文件仍保留，历史行未被修改。
9. 后端全量 Pytest、前端全部静态测试、`npm run type-check` 和 `npm run build` 通过。
10. 文案无乱码，资料空状态、错误状态、PDF/视频/链接阅读和教师资料危险操作确认正常。
11. 稳定文档、修改记录、服务器部署影响和知识图谱结果已同步或如实记录未完成原因。

## 八、风险与缓解

| 风险 | 影响 | 缓解与验收 |
|---|---|---|
| 历史课时正文不再可见 | 老用户无法从产品页面读取旧课时 | 保留表、ORM 和迁移；发布前确认业务接受，回滚代码即可恢复 |
| 旧前端或第三方仍调用课时 API | 上线后收到 HTTP 404 | 明确这是退役契约；同批发布前端并检查访问日志中的旧路径 |
| 学习进度和教师分析突然消失 | 用户可能误解为数据丢失 | 不展示虚假空分析；修改记录说明历史数据保留、产品能力下线 |
| 资料页被课时清理误伤 | PDF/视频/链接无法阅读 | 保留并强化公开资料、认证文件、Range、预览和直读回归 |
| 单页 CSS 清理不完整 | 移动端空白、重叠或残留大段死样式 | 静态布局测试 + 桌面/移动浏览器验收 + 残留扫描 |
| wangEditor 清理影响构建 | lockfile 或 Vite 分包引用失效 | 使用 `npm uninstall` 机械更新依赖，随后跑类型检查和生产构建 |
| 隐私文案与历史留存矛盾 | 声称不收集但仍保存历史记录 | 明确区分“不再新增”与“历史数据保留” |
| 工作区已有未提交修改 | 实施时可能覆盖其他任务 | 执行前重新检查 `git status`，逐文件合并，不回滚用户改动 |

## 九、回滚方案

本轮不改数据库，因此回滚只回滚同一批前后端代码和静态资源：

1. 恢复后端 Router、服务、Schema 和公开课程 `lesson_count`。
2. 恢复前端课时组件、API、教师端课时/分析界面和 wangEditor 依赖。
3. 重新构建并部署前端，重启后端。
4. 使用保留的 `lessons`、`lesson_progress`、`course_progress` 历史数据验证旧课时和进度可再次读取。

禁止只回滚前端或只回滚后端；前后端接口契约必须保持同一版本。由于没有数据库迁移，不需要执行数据库逆向脚本。

## 十、服务器部署影响

本计划文档本身的完善**不需要服务器修改**。将来执行代码计划并上线时：

- **需要拉取代码。**
- **需要在前端重新安装依赖**，建议使用锁文件执行 `npm ci`。
- **需要重新构建并部署前端静态资源。**
- **需要重启 FastAPI 后端服务**，使注销的 Router 生效。
- **不需要数据库迁移或清表。** 发布前仍建议备份数据库，历史表和数据必须保留。
- **不需要修改环境变量、Nginx、Redis 或对象存储配置。**
- 建议先完成并校验新前端构建，再在同一发布窗口部署前端并重启后端；旧页面缓存调用退役接口时返回 404 属于预期，发布后应做一次强制刷新验收。
