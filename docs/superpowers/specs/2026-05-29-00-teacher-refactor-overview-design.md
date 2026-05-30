# 教师端重构总览设计（00 · 总纲）

- 日期：2026-05-29
- 范围：教师端整体重构，跨 A/B/C/D 四组
- 拍板/收口：D 组（邱）
- 文档作者视角：C 组（俞），受用户委托产出整体方案
- 关联子文档：
  - [`01-课程资料题库与章节去除`](2026-05-29-01-course-material-question-chapter-removal-design.md)
  - [`02-班级与学生管理`](2026-05-29-02-class-and-student-management-design.md)
  - [`03-发布题目`](2026-05-29-03-publish-questions-design.md)
  - [`04-作品审核现状确认`](2026-05-29-04-project-review-status-design.md)

> ⚠️ 边界提示：本轮改动远超 CLAUDE.md 中 C 组（作品/文件存储）范围，覆盖 A 组（班级）、B 组（课程/资料/题库/章节）、D 组（任务/公告）。所有跨组共享文件（`teacher_routes.py`、`entities.py`、`common.py`、`schema_compat.py`、`router/index.ts`、`TeacherLayout.vue`）的改动需经 D 组拍板后实施。

---

## 1. 目标

把教师端从"以章节为核心、班级按专业、内容全局共享"的旧结构，重构为：

- **以课程为核心**：教师端一切分类一律按"教师创建的课程"组织。
- **彻底删除章节**：资料、题目、学习进度、练习全部直接挂在课程下。
- **班级按课程划分**：一个班级归属一门课程。
- **教师严格隔离**：每位教师只能看到/操作自己创建的课程及其下属资源。
- **任务收敛为发布题目**：去掉公告，只保留给班级发题。
- **左侧导航重排为 9 项**，并拆出独立的"学生管理"页。

## 2. 已确认的关键决策

| 决策点 | 结论 |
|--------|------|
| 班级 × 课程 | **一班级 → 一课程**（`Class` 去 `major`、加 `course_id`）|
| 教师归属 | **课程为归属根 + 严格隔离**，不设公共/未归属认领区 |
| 章节去除 | **全系统彻底删除**（前端、后端、数据库、学生端学习链路）|
| 历史数据 | **随库重置**：`database_setup.py` 重建种子数据时直接带 `created_by`，不做在线迁移认领 |
| 学生成绩 | 仅由"学生数据"**改名**，不派生任务得分 |

## 3. 左侧导航重排（9 项）

| 序 | 目标菜单 | path | 旧菜单 | 关键改动 | 子文档 |
|----|----------|------|--------|----------|--------|
| 1 | 概述 | `/teacher` | 概览 | 改名；统计卡去"已发布章节数"，换"我的课程数" | 00 |
| 2 | 课程管理 | `/teacher/courses` | 课程管理 | 列表去章节数/课程时间；加"查看资料"按钮 | 01 |
| 3 | 班级管理 | `/teacher/classes` | 班级管理 | 按课程划分 + 搜索栏；查看学生直接展示；删除受限 | 02 |
| 4 | 发布题目 | `/teacher/publish` | 任务发布 `/announcements` | 改名；删公告；选班级；完成情况→查看情况 | 03 |
| 5 | 学生成绩 | `/teacher/grades` | 学生数据 `/students` | 改名 | 02 |
| 6 | 作品审核 | `/teacher/reviews` | 作品审核 | 无功能改动 | 04 |
| 7 | 资料管理 | `/teacher/materials` | 资料管理 | 上传/筛选按课程；去章节与排课 | 01 |
| 8 | 学生管理 | `/teacher/student-admin` | —（新增）| 班级内学生增/删独立页 | 02 |
| 9 | 题库管理 | `/teacher/questions` | 题库管理 | 按课程组织（去章节维度）| 01 |

> 路由路径为建议值，最终以 D 组联调命名为准。改名涉及 `frontend/src/router/index.ts`、`TeacherLayout.vue` 导航数组、各页面 `meta.title`。

## 4. 跨域数据模型总改动

集中改 `backend/app/models/entities.py`、`backend/app/schemas/common.py`、`backend/app/db/schema_compat.py`。

### 4.1 表/字段

| 表 | 改动 |
|----|------|
| `courses` | 加 `created_by`(FK users, NOT NULL)；唯一约束由 `name` 改为 `(name, created_by)` |
| `classes` | 删 `major`；加 `course_id`(FK courses, NOT NULL, index) |
| `chapters` | **整表删除**（含 `course_id`/排课字段/`Chapter` 模型/关系）|
| `materials` | `chapter_id` → `course_id`(FK courses, NOT NULL) |
| `questions` | `chapter_id` → `course_id`(FK courses, NOT NULL) |
| `student_progress` | `chapter_id` → `course_id`(FK courses, NOT NULL) |
| `quiz_attempts` | 不变（经 `question` 间接归课程）|
| `announcements` | 见文档 03：保留表、语义收敛为发题；**新增 `announcement_classes` 关联表**支持一次发题指向多个班级（`class_id` 单班级废弃）|

### 4.2 关系链（重构后）

```
User(teacher) ──created_by──▶ Course ──┬─▶ Material（视频/PDF，多个）
                                       ├─▶ Question ──▶ QuizAttempt
                                       ├─▶ StudentProgress
                                       └─▶ Class ──▶ StudentClassEnrollment ──▶ User(student)
```

### 4.3 章节删除的级联调整

旧 `DELETE chapter` 会连带删 Material/Question/StudentProgress/QuizAttempt。删表后，这些级联改由 `DELETE course` 承担（课程删除前置校验沿用现有"有资料/题目/学习记录则拒删"的思路，见文档 01）。

## 5. 章节删除的全链路爆炸半径清单

> 这是本轮风险最高的部分，单列清单供逐项核对。

### 后端（删除/改写）

- 删除：`api/v1/routes/chapter_routes.py`、`services/chapter_service.py`、`__init__.py` 中章节路由注册、`Chapter` 模型
- 改写：`material_service.py`（按课程存取）、`question_service.py`（按课程，含 Excel 导入的章节匹配逻辑）、`quiz_service.py`（StudentProgress 按课程）、`teacher_service.py`（`published_chapters` 统计去除/替换、`list_students` 进度算法）、`portfolio_service.py`（硬编码"6 章节"算法重写）
- `schema_compat.py`：删除 chapters 排课字段补齐逻辑；新增 `courses.created_by`、`classes.course_id`、`materials/questions/student_progress.course_id` 的补齐

### 前端（删除/改写）

- 删除：`views/ChapterView.vue`、`api/chapter.ts`、路由 `/learn/:chapterId`
- 改写（学生端）：`LearnView.vue`、`CourseDetailView.vue`、`PracticeView.vue`、`PracticeQuizView.vue`、`components/home/CoursePreview.vue`、`AboutView.vue` 中章节文案
- 练习路由：`/practice/quiz/:chapterId` → `/practice/quiz/:courseId`
- 改写（教师端）：见各子文档

## 6. 迁移与上线顺序（建议）

由于历史数据随库重置，开发期采用"改模型 + 重写种子 + 重置库"，不写在线数据迁移脚本；但需保留一份 Alembic 迁移用于已有正式库（如有）。

建议实施批次（每批独立可测）：

1. **批次一（模型与库底座）**：改 `entities.py` + `schema_compat.py` + `database_setup.py` 种子（含 `created_by`、`course_id`、去章节）。跑后端测试基线。
2. **批次二（B 组 / 文档 01）**：课程归属、删章节后端、资料/题库按课程、学生端学习链路。
3. **批次三（A 组 / 文档 02）**：班级按课程 + 搜索、查看学生、学生管理页、学生成绩改名、删除受限。
4. **批次四（D 组 / 文档 03）**：发布题目改造。
5. **批次五（收口）**：导航重排统一落地、文档 04 核对、全量测试与联调。

> 批次一是所有后续工作的前置，必须先合入。导航重排（`TeacherLayout.vue`/`router`）建议最后统一改，避免中途死链。

## 7. 统一约定（不变）

- 接口统一返回 `{"code":0,"data":...,"message":"ok"}`，HTTP 恒 200。
- 新 Schema 入 `common.py`；新模型入 `entities.py`；新路由注册到 `__init__.py`。
- 错误用 `BusinessException(code, message)`。
- 前端 `<script setup>` + TS；新增 API 模块放 `frontend/src/api/`。

## 8. 主要风险

| 风险 | 说明 | 缓解 |
|------|------|------|
| 学生端学习链路回归 | 章节删除波及学生学习/练习/进度/档案 | 文档 01 单列学生端改造；批次二集中测试 |
| 教师隔离遗漏 | 任一查询忘记按 `created_by`/`course_id` 过滤会越权 | 统一在 service 层过滤；补隔离测试 |
| 课程删除级联 | 删课程牵连资料/题目/进度 | 沿用前置校验拒删；UI 明确提示 |
| 跨组共享文件冲突 | 多组同改 `entities.py`/`common.py`/`teacher_routes.py` | 批次一先行；改动经 D 组拍板 |
| 唯一约束变更 | `courses.name` 全局唯一 → 按教师唯一 | 迁移与种子同步调整 |

## 9. 验收基线（总）

- 教师端所有列表/下拉只出现当前教师创建的课程及其下属资源。
- 全库无任何 `chapter` 残留（代码、表、路由、前端引用、测试）。
- 学生端学习/练习/进度/档案在"无章节、按课程"下完整可用。
- 新班级按课程创建，班级管理可按课程/班名搜索。
- 发布题目可一次选**多个**（该课程下的）班级，"查看情况"跳转学生成绩页正常展示。
- 作品审核与批量下载不受影响（文档 04）。
- `python -m pytest tests/ -v` 全绿（含新增隔离/课程锚定测试）。
