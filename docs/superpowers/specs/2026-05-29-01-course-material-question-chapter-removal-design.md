# 课程 / 资料 / 题库 与章节去除设计（01 · B 组域）

- 日期：2026-05-29
- 上级文档：[`00-教师端重构总览`](2026-05-29-00-teacher-refactor-overview-design.md)
- 归属：B 组（课程/资料/题库），跨改学生端学习链路
- 拍板：D 组

---

## 1. 目标

1. 课程成为归属根：`Course.created_by`，教师端只见自己创建的课程。
2. **彻底删除章节**：资料、题目、学习进度直接挂课程。
3. 资料按课程上传/筛选；课程管理列表加"查看资料"跳转。
4. 题库按课程组织（去章节维度）。
5. 重构学生端学习/练习链路为"按课程"。

## 2. 现状（梳理结论）

- 课程 CRUD 寄生在 `question_routes.py`：`/questions/courses`(+`/{id}`)，`Course(id,name unique,created_at)`，无归属。
- 章节是核心锚点：`Material.chapter_id`、`Question.chapter_id`、`StudentProgress.chapter_id` 均 NOT NULL；`Course → chapters` 一对多。
- 章节带排课字段 `day_of_week/class_periods/schedule_note`（即"课程时间管理"）。
- 资料：`/materials`、`/chapters/{id}/contents`，上传按章节选。
- 题库：三级联动 课程→章节→题型；Excel 导入按章节编号/标题匹配。
- 课程管理页列表显示"章节数""题目数"，无"查看资料"。
- 学生端：`LearnView/CourseDetailView/ChapterView/PracticeView/PracticeQuizView` 全依赖章节。
- `portfolio_service` 硬编码"6 章节"计算进度。

## 3. 数据模型改动

```text
Course:   + created_by(FK users, NOT NULL); 唯一约束 name → (name, created_by)
Chapter:  整体删除（模型、表、关系、排课字段）
Material:  chapter_id → course_id(FK courses, NOT NULL, index)
Question:  chapter_id → course_id(FK courses, NOT NULL, index)
StudentProgress: chapter_id → course_id(FK courses, NOT NULL, index)
QuizAttempt: 不变（question → course）
```

`schema_compat.py`：删除 chapters 排课字段补齐；新增对 `courses.created_by`、`materials/questions/student_progress.course_id` 的补齐（旧库存在时 ALTER）。

`database_setup.py`：种子课程带 `created_by`（指向种子教师）；种子资料/题目/进度直接挂 `course_id`；不再建任何章节。

## 4. 后端改造

### 4.1 课程（Course）

- 课程路由从 `question_routes.py` **抽出**为独立 `course_routes.py` + `course_service.py`（课程已升为归属根，不再附属题库）。路径建议 `/courses`（旧 `/questions/courses` 保留 30 天兼容转发或由 D 组定）。
- 所有课程查询按 `created_by == current_user.id` 过滤。
- 创建：`CourseCreate{name}` + 自动注入 `created_by`；同教师下 `name` 唯一。
- 列表项字段：`id,name,created_at,material_count,question_count,class_count`（**去掉 chapter_count**）。
- 删除：前置校验——该课程下存在资料 / 题目 / 学生学习记录 / 班级时拒删（`BusinessException(400, ...)`），提示具体阻塞项。

### 4.2 资料（Material）

- 上传/列表/筛选全部改为按 `course_id`：
  - `GET /materials?course_id=` 按课程过滤（仅当前教师课程）。
  - `GET /courses/{course_id}/contents` 替代旧 `/chapters/{id}/contents`（供"查看资料"和学生端使用）。
  - `POST /materials`：`MaterialCreate{course_id,type,title,url,size,file_id}`，去 `chapter_id`。
  - 创建前校验课程存在且属当前教师。
- 一个课程可含多个视频和 PDF（`type ∈ {video,pdf}`）。
- 文件存储链路（StoredFile/file_id/魔数校验）不变（C 组现状沿用）。

### 4.3 题库（Question）

- 全部按 `course_id`：
  - `GET /questions?course_id=&type=`（去 `chapter_id`）。
  - `GET /questions/course/{course_id}` 替代 `/questions/chapter/{id}`。
  - `POST/PUT`：`QuestionCreate{type,course_id,stem,options,answer,explanation}`。
  - Excel 导入：表头 `chapter` 改为 `course`，按课程名匹配当前教师的课程；匹配不到则报错行号。
- 删除题目不级联（与现状一致）。

### 4.4 测验 / 进度 / 档案

- `quiz_service.submit_answer`：StudentProgress 改为按 `course_id`（经 question.course_id 定位），完成数/正确率按课程聚合。
- `GET /quiz/stats/{course_id}` 替代 `/quiz/stats/{chapter_id}`。
- `portfolio_service`：去掉硬编码 6 章节，进度按"学生选课范围内的课程"动态计算（分母 = 学生可见课程数或有进度记录的课程数，具体口径见开放问题）。
- `teacher_service.get_teacher_stats`：删 `published_chapters`，新增 `my_courses`（当前教师课程数）；`list_students` 的进度聚合改按课程。

## 5. 前端改造

### 5.1 教师端

**课程管理 `TeacherCourses.vue`**
- 列表列：序号 / 课程名称 / 资料数 / 题目数 / 创建时间 / 操作。**去掉"章节数""课程时间"**。
- 操作列：编辑、删除、**查看资料**（新增）。点"查看资料"跳 `/teacher/materials?course_id={id}`，资料页据此预筛选该课程资料。
- 删除：命中前置校验时弹出后端返回的阻塞原因。

**资料管理 `TeacherMaterials.vue`**
- 删除"课程时间安排/排课/章节编辑"整块。
- 上传表单：所属课程（必选，下拉=当前教师课程）+ 类型 + 标题 + 文件。
- 筛选：按课程下拉（支持从 URL `course_id` 预选）。
- 列表列：资料名 / 所属课程 / 类型 / 大小 / 上传时间 / 删除。

**题库管理 `TeacherQuestions.vue`**
- 联动由 课程→章节→题型 改为 课程→题型。
- 新增/编辑表单去"所属章节"，保留"所属课程"。
- 列表"所属章节"列删除。

**概述 `TeacherDashboard.vue`**
- 统计卡"已发布章节 x/6"替换为"我的课程数"。

### 5.2 API 模块

- 删除 `api/chapter.ts`。
- `api/course.ts`：路径迁到 `/courses`；类型去 `chapter_count`，加 `material_count`。
- `api/material.ts`：`getCourseContents(courseId)`；`createMaterial` 参数 `course_id`。
- `api/question.ts`：参数 `course_id`，去 `chapter_id`/`getChapterQuestions`/`getCourses`（课程查询统一走 `course.ts`）。

### 5.3 学生端（章节删除连带）

- 删除 `views/ChapterView.vue` 及路由 `/learn/:chapterId`。
- `LearnView.vue`：去章节列表，改为课程卡 → 进入课程详情。
- `CourseDetailView.vue`：直接展示该课程的资料（视频/PDF）列表 + 学习进度，替代原"章节列表"。课程内容入口为 `/courses/{id}/contents`。
- `PracticeView.vue`：练习卡按课程（替代按章节），显示该课程题型/进度。
- `PracticeQuizView.vue`：路由 `:chapterId` → `:courseId`，加载 `GET /questions/course/{courseId}`。
- `CoursePreview.vue` / `AboutView.vue`：清理章节文案。

## 6. 验收

- 教师端课程/资料/题库下拉与列表只含当前教师课程。
- 代码全局无 `chapter` 残留（`grep -ri chapter` 仅余历史文档）。
- 资料按课程上传/筛选；"查看资料"跳转并预筛选正确。
- 题库 Excel 导入按课程名匹配。
- 学生端按课程学习/练习/进度/档案完整可用。
- 课程删除在有下属数据时被正确拒绝并提示。
- 相关测试通过，并新增：课程归属隔离、资料/题目按课程、删课程拒删。

## 7. 开放问题

1. 课程内容是否需要排序字段（替代原章节 `sort_order`）？建议 `Material.sort_order` 保留/新增以控制学生端展示顺序可以增加排序字段。
2. `portfolio` 学习进度分母口径：按"有进度记录的课程数"还是"学生所属班级关联的课程数"？建议后者（更贴合一班一课程）。
3. `/questions/courses` 旧路径是否需要兼容期，由 D 组定。
