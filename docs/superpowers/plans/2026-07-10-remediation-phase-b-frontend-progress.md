# 前端流程与课时进度修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复随机点名、通知中心、作品入口、课时进度和课程分析的前后端契约。

**Architecture:** 进度写入使用数据库原子更新，前端显式区分“进入课时”和“心跳”。页面修复沿用现有 API、Pinia 和消息刷新工具，不新增状态管理体系。

**Tech Stack:** Vue 3、TypeScript、Vite、Element Plus、FastAPI、SQLAlchemy、pytest、Node 静态测试。

**Design:** `docs/superpowers/specs/2026-07-10-code-review-remediation-design.md`

---

### Task 1: 修复随机点名学生加载与动画竞态

**Files:**
- Modify: `frontend/src/views/teacher/TeacherRandomPicker.vue`
- Modify: `frontend/src/api/class.ts`
- Create: `frontend/tests/teacher-random-picker-static.test.mjs`

- [x] **Step 1: 写接口契约和竞态失败测试**

断言页面导入并调用 `getClassStudents(selectedClassId)`，不读取 `classData.students`；切换班级时重新调用加载函数；动画计时器有可清理句柄，切班和卸载都会停止旧动画；快速切班时旧请求结果不能覆盖新班级。

- [x] **Step 2: 运行并确认失败**

Run: `node frontend/tests/teacher-random-picker-static.test.mjs`

Expected: FAIL，当前实现读取班级摘要的可选字段。

- [x] **Step 3: 使用真实学生列表接口**

```typescript
async function loadStudents() {
  if (!selectedClassId.value) return
  const currentRequestId = ++studentRequestId
  const result = await getClassStudents(selectedClassId.value)
  if (currentRequestId !== studentRequestId) return
  students.value = result.map(student => ({
    id: student.id,
    name: student.name,
    major: student.major || '',
  }))
  availableStudents.value = [...students.value]
  calledStudents.value = []
  currentStudent.value = null
  showResult.value = false
}
```

保存抽取动画的 interval ID；`handleClassChange()` 先停止动画并清空当前结果，再加载新班学生；`onBeforeUnmount()` 同时使 `studentRequestId` 失效并清理 interval。空班级必须显式清空 `students`、`availableStudents`、`calledStudents` 和 `currentStudent`。`getClasses()` 返回类型保持 `ClassInfo[]`，删除误导性的 `students?` 交叉类型。

- [x] **Step 4: 运行静态测试和构建**

Run: `node frontend/tests/teacher-random-picker-static.test.mjs`

Run: `npm run build --prefix frontend`

Expected: PASS。

### Task 2: 修复作品入口、通知中心和现有静态回归

**Files:**
- Modify: `frontend/src/router/index.ts:70-82`
- Modify: `frontend/src/views/InboxView.vue`
- Modify: `frontend/src/components/AppHeader.vue`
- Modify: `frontend/src/views/CourseDetailView.vue`
- Modify: `frontend/src/components/home/HeroSection.vue`
- Modify: `backend/app/services/notification_service.py:368-389`
- Modify: `frontend/tests/message-refresh-static.test.mjs`
- Modify: `frontend/tests/copy-consistency-static.test.mjs`
- Modify: `frontend/tests/course-detail-layout-static.test.mjs`
- Modify: `frontend/tests/home-branding-static.test.mjs`

- [x] **Step 1: 运行现有失败测试记录基线**

Run: `node frontend/tests/message-refresh-static.test.mjs`

Run: `node frontend/tests/copy-consistency-static.test.mjs`

Run: `node frontend/tests/course-detail-layout-static.test.mjs`

Run: `node frontend/tests/home-branding-static.test.mjs`

Expected: FAIL，缺少 `loadMessages`、刷新订阅、稳定文案，且两份旧布局/品牌断言与当前页面结构不一致。

- [x] **Step 2: 恢复作品入口登录边界和正确通知路由**

移除 `/create` 的 `meta.public`。后端作品通知改为：

```python
action_url=f"/create/project/{project.id}"
```

- [x] **Step 3: 集中消息加载并恢复刷新机制**

`InboxView.vue` 增加：

```typescript
async function loadMessages(showInitialLoading = false) {
  if (showInitialLoading) loading.value = true
  try {
    await Promise.all([loadAnnouncements(), loadNotifications()])
  } finally {
    if (showInitialLoading) loading.value = false
  }
}
```

首屏先 `Promise.all([loadMessages(true), loadPreferences()])`；偏好不进入 15 秒轮询，避免覆盖尚未保存的开关。挂载时设置 15 秒消息定时器、仅在页面重新可见时刷新消息，并注册 `onMessageRefresh(loadMessages)`；卸载时清理 interval、DOM 监听和事件订阅。后台刷新不切换首屏 `loading`，避免列表每 15 秒闪烁。成功已读、全部已读和作业完成后调用 `emitMessageRefresh()`。

- [x] **Step 4: 页头点击先已读后跳转**

把 `router-link` 改为命令按钮或点击处理函数：调用 `markNotificationRead(item.id)` 成功后关闭下拉并 `router.push(item.action_url || '/student/notifications')`。失败时不修改本地未读数、不跳转，并显示“通知标记已读失败，请稍后重试”。

- [x] **Step 5: 修正稳定文案与过期静态断言**

课程详情资料页签使用“学习资料库”；Hero 徽标统一为“中国计量大学 · AI 通识教育课程平台”。`course-detail-layout-static.test.mjs` 改为校验当前 `booksite-layout`、`reader-sidebar`、`reader-main` 的桌面网格和移动抽屉，不再要求已经删除的 `.course-shell/.sidebar`；`home-branding-static.test.mjs` 校验当前学校徽标图片和中文 `alt`，不再要求已废弃的 `logo-emblem-book` 类。测试只能更新到当前明确设计契约，不能删除顶栏避让、移动抽屉或品牌归属断言。

- [x] **Step 6: 运行消息、文案、布局与品牌测试**

Run: `node frontend/tests/message-refresh-static.test.mjs`

Run: `node frontend/tests/notification-center-static.test.mjs`

Run: `node frontend/tests/copy-consistency-static.test.mjs`

Run: `node frontend/tests/course-detail-layout-static.test.mjs`

Run: `node frontend/tests/home-branding-static.test.mjs`

Expected: PASS。

### Task 3: 原子化课时进度和真实访问次数

**Files:**
- Modify: `backend/app/schemas/common.py:646-652`
- Modify: `backend/app/services/progress_service.py:196-251`
- Modify: `backend/tests/test_lessons_progress.py`
- Create: `backend/tests/test_progress_concurrency.py`
- Modify: `frontend/src/api/progress.ts:59-95`
- Modify: `frontend/src/App.vue:15-25`
- Modify: `frontend/src/views/CourseDetailView.vue:169-262,477-527`
- Create: `frontend/tests/lesson-progress-reporting-static.test.mjs`

- [x] **Step 1: 写并发与访问次数失败测试**

新增测试：两次普通心跳只累加时长、不增加 `view_count`；两次 `visit_started=true` 增加两次访问；完成状态和最高百分比不回退；并发首次上报最终只有一条 `LessonProgress` 和一条 `CourseProgress`，时长总和不丢失。`test_progress_concurrency.py` 使用临时文件 SQLite、两个独立 Engine Session 和线程屏障，禁止在线程间共享公共 `db_session` fixture；同一用例在设置 `TEST_MYSQL_URL` 时对 MySQL 测试库重复执行。

- [x] **Step 2: 运行并确认现有读改写行为失败**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_lessons_progress.py -q`

Expected: FAIL，当前每次心跳都增加浏览次数，并发场景可能丢失数据。

- [x] **Step 3: 扩展输入并使用数据库表达式更新**

Schema 增加：

```python
visit_started: bool = False
```

既有行使用 SQL 表达式更新：

```python
updates = {
    LessonProgress.duration_seconds: LessonProgress.duration_seconds + data.duration_seconds,
    LessonProgress.view_count: LessonProgress.view_count + (1 if data.visit_started else 0),
    LessonProgress.last_position: data.last_position,
    LessonProgress.last_viewed_at: now,
}
```

`LessonProgress` 和兼容用 `CourseProgress` 都使用按方言选择的数据库 upsert：SQLite 使用 `on_conflict_do_update`，MySQL 使用 `on_duplicate_key_update`。冲突更新表达式直接执行 `duration_seconds = duration_seconds + 本次时长`、`view_count = view_count + visit_started`，使用 `case`/数据库最大值保留最高完成百分比和已完成状态；不得先读取旧 ORM 值再在 Python 累加。

- [x] **Step 4: 前端区分首次访问和心跳**

`LessonProgressPayload` 增加 `visit_started?: boolean`，普通与 keepalive 请求都必须序列化该字段。`App.vue` 的路由组件 key 从 `viewRoute.fullPath` 改为 `viewRoute.path`，保证只改 `lesson_id` 查询参数不会重建课程页。每次 `currentLessonId` 真正切换后只发送一次 `visit_started: true`；30 秒心跳和最终补报均为 `false`。

新增 `takeUnreportedDuration()`，读取并立即清零本次尚未上报时长；`visibilitychange` 隐藏、`pagehide` 和卸载共同调用带 `finalReportSent` 门闩的 `reportFinalProgressOnce()`，同一隐藏/离开周期只能发送一个 keepalive 请求。页面重新可见后重置门闩和计时起点。

- [x] **Step 5: 运行进度测试**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_lessons_progress.py -q`

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_progress_concurrency.py -q`

Run: `node frontend/tests/lesson-progress-reporting-static.test.mjs`

Expected: PASS。

### Task 4: 非视频课时显式完成

**Files:**
- Modify: `frontend/src/components/lesson/LessonReader.vue`
- Modify: `frontend/src/views/CourseDetailView.vue`
- Modify: `frontend/tests/public-learning-static.test.mjs`
- Create: `frontend/tests/lesson-completion-static.test.mjs`

- [x] **Step 1: 写失败测试**

断言 `LessonReader` 向父组件暴露是否含视频；已登录学生阅读无视频课时时出现“完成本课”按钮，点击后上报 `progress_percent: 100`。

- [x] **Step 2: 运行并确认失败**

Run: `node frontend/tests/lesson-completion-static.test.mjs`

Expected: FAIL，当前非视频课时始终上报 10%。

- [x] **Step 3: 实现完成动作**

`LessonReader` 计算 `hasVideoMaterial` 并 emit `content-kind`。`CourseDetailView` 仅对 `canSaveProgress && !hasVideoMaterial && status !== 'completed'` 显示按钮；点击调用现有 `reportLessonProgress`，上报 100、最近位置和本次未上报时长。

- [x] **Step 4: 运行前端全量静态测试和构建**

Run: `$failed = $false; Get-ChildItem frontend/tests/*.test.mjs | ForEach-Object { & node $_.FullName; if ($LASTEXITCODE -ne 0) { $failed = $true } }; if ($failed) { exit 1 }`

Run: `npm run build --prefix frontend`

Expected: 全部 PASS，构建仅允许既有大 chunk 警告。

### Task 5: 课程分析改为数据库聚合和学生分页

**Files:**
- Modify: `backend/app/api/v1/routes/progress.py:67-82`
- Modify: `backend/app/services/progress_service.py:303-407`
- Modify: `backend/tests/test_lessons_progress.py`
- Create: `backend/tests/test_progress_analytics_scale.py`
- Modify: `frontend/src/api/progress.ts:39-77`
- Modify: `frontend/src/views/teacher/TeacherCourseDetail.vue`
- Modify: `frontend/tests/teacher-course-analytics-static.test.mjs`

- [x] **Step 1: 写分页契约和规模失败测试**

在现有分析测试中断言 `student_progress` 为 `{items,total,page,page_size}`；第 2 页不与第 1 页重复。规模测试创建 100 名学生、20 个已发布课时和对应进度，通过 SQLAlchemy `before_cursor_execute` 计数，断言接口查询数不随 `学生数 × 课时数` 增长，且服务不执行 `db.query(LessonProgress).all()` 全量加载。

- [x] **Step 2: 运行并确认当前接口返回全量数组**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_lessons_progress.py backend/tests/test_progress_analytics_scale.py -q`

Expected: FAIL，当前 `student_progress` 是完整数组，且服务加载所有进度 ORM。

- [x] **Step 3: 在数据库层完成聚合**

`GET /courses/{course_id}/analytics` 增加 `page: int = 1`、`page_size: int = 20`，服务将页码限制为至少 1、页大小限制为 1-100。使用以下三组聚合而非 ORM 笛卡尔展开：

- 课程学生子查询：未删除班级中的去重、未删除学生。
- 按学生聚合：`count(completed)`、`sum(duration_seconds)`、疑似快速完成 `case`，再 `offset/limit`；无进度学生通过外连接保留为 0。
- 按课时聚合：`sum(view_count)`、`count(distinct user_id)`、平均进度、完成数、平均时长和疑似快速完成数。

总体平均完成率和平均时长直接由聚合子查询计算；返回：

```python
"student_progress": {
    "items": student_items,
    "total": student_total,
    "page": safe_page,
    "page_size": safe_page_size,
}
```

- [x] **Step 4: 前端接入分页**

`CourseAnalytics.student_progress` 改为分页对象，`getCourseAnalytics(courseId, page, pageSize)` 传递查询参数。教师课程详情表格读取 `analytics.student_progress.items`，增加 Element Plus 分页；页码或页大小变化只重新请求分析接口，不在前端切片完整数组。

- [x] **Step 5: 运行分析测试、静态测试和类型检查**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_lessons_progress.py backend/tests/test_progress_analytics_scale.py -q`

Run: `node frontend/tests/teacher-course-analytics-static.test.mjs`

Run: `npm run type-check --prefix frontend`

Expected: PASS；100×20 数据下查询数保持固定，学生明细可分页。

### Task 6: 阶段 B 文档与验收

**Files:**
- Modify: `docs/superpowers/project-map.md`
- Modify: `backend/docs/项目修改记录.md`
- Modify: `docs/superpowers/specs/2026-07-09-02-lesson-progress-tracking.md`
- Modify: `docs/superpowers/specs/2026-07-09-04-notification-system-extension.md`

- [x] **Step 1: 记录最终语义和验证结果**

明确 `visit_started`、非视频完成按钮、作品入口登录边界、通知刷新和课程分析分页。服务器部署影响：需要拉代码、重启后端、重新构建前端；不需要数据库迁移、环境变量或 Nginx 修改。

- [x] **Step 2: 阶段回归、图谱和改动边界检查**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_lessons_progress.py backend/tests/test_progress_concurrency.py backend/tests/test_progress_analytics_scale.py -q --basetemp=tmp/pytest-phase-b`

Run: `$failed = $false; Get-ChildItem frontend/tests/*.test.mjs | ForEach-Object { & node $_.FullName; if ($LASTEXITCODE -ne 0) { $failed = $true } }; if ($failed) { exit 1 }`

Run: `npm run build --prefix frontend`

Run: `graphify update .`

Run: `git diff --check`

Expected: 阶段测试、全量静态测试和构建通过，图谱更新成功；本计划不自动暂存或提交。
