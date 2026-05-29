# 班级与学生管理设计（02 · A 组域）

- 日期：2026-05-29
- 上级文档：[`00-教师端重构总览`](2026-05-29-00-teacher-refactor-overview-design.md)
- 归属：A 组（班级/学生）
- 拍板：D 组

---

## 1. 目标

1. 班级按课程划分（一班级 → 一课程），班级管理加搜索栏。
2. "查看学生"保持直接查看（不改），但**学生增删拆到独立"学生管理"页**。
3. 班级"删除"在该班有学生时**不可直接删除**。
4. "学生数据"改名为"学生成绩"（仅改名）。

## 2. 现状（梳理结论）

- `Class(id,name,major,created_at)`，仅 `major`，与课程无关联，无教师归属。
- 班级接口：`GET/POST /classes`、`DELETE /classes/{id}`、`GET /classes/{id}/students`、`POST /classes/{id}/enroll`、`DELETE /classes/{id}/enroll/{sid}`、`POST /classes/import`。
- `DELETE /classes/{id}` 现在**级联删除**学生注册及仅属该班学生的全部数据。
- 班级管理页：新增表单含"所属专业"；列表列含专业；"查看学生"打开弹窗，弹窗内含增删/导入；**无搜索栏**。
- 学生数据页 `TeacherStudents.vue`：含"学生列表"+"任务完成"两个 Tab，已有班级筛选、搜索、Excel 导出、分页。

## 3. 数据模型改动

```text
Class: 删 major; 加 course_id(FK courses, NOT NULL, index)
```

- 班级归属经课程间接实现：教师只见自己课程下的班级（`Class.course_id ∈ 当前教师课程`）。
- `schema_compat.py` 补 `classes.course_id`；`database_setup.py` 种子班级带 `course_id`。

## 4. 后端改造

### 4.1 班级

- `GET /classes`：仅返回当前教师课程下的班级；支持 `course_id`、`keyword`（按班名模糊）查询参数，供搜索栏使用。返回项加 `course_id,course_name`，去 `major`。
- `POST /classes`：`ClassCreate{name,course_id}`（去 `major`）；校验 `course_id` 属当前教师。
- `DELETE /classes/{id}`：**前置校验**——该班存在学生注册时拒删，返回 `BusinessException(400,"该班级仍有学生，无法删除，请先在学生管理中移除学生")`；无学生时才删（连带删该班相关公告/任务记录的逻辑保留）。

### 4.2 学生增删（供"学生管理"页）

沿用现有接口，不新增后端：
- `GET /classes/{id}/students`
- `POST /classes/{id}/enroll`（支持自动建号）
- `DELETE /classes/{id}/enroll/{sid}`
- `POST /classes/import`（Excel 批量导入）

> 即：后端学生增删能力已具备，本轮主要是前端把它从弹窗拆成独立页面，并调整班级删除约束。

## 5. 前端改造

### 5.1 班级管理 `TeacherClasses.vue`

- 新增表单：班级名称 + **所属课程**（下拉=当前教师课程），去"所属专业"。
- 列表列：班级名称 / 所属课程 / 学生人数 / 创建时间 / 操作。
- **搜索栏**：顶部加按课程下拉 + 班名关键字输入，调 `GET /classes?course_id=&keyword=`。
- 操作列按钮：
  - **查看学生**：保持现状——直接查看该班学生（只读列表展示，可继续用弹窗或行内展开；不含增删）。
  - **学生管理**（新增按钮）：跳转 `/teacher/student-admin?class_id={id}`。
  - **删除**：点击时若该班有学生，按钮禁用或点击后提示后端拒删原因。

### 5.2 学生管理（新页 `TeacherStudentAdmin.vue`，导航第 8 项）

- 入口：导航"学生管理" + 班级管理行内"学生管理"按钮（带 `class_id`）。
- 顶部：班级选择（默认取 URL `class_id`，下拉=当前教师班级）。
- 功能：**仅增与删**
  - 学生列表（学号/姓名/专业/操作[移除]）。
  - 手动添加学生（学号+姓名，调 enroll）。
  - Excel 批量导入（调 import）。
  - 移除学生（调 unenroll，二次确认）。
- 与"查看学生"区别：查看=只读；学生管理=可增删。

### 5.3 学生成绩 `TeacherStudents.vue`（导航第 5 项，改名 + 承接"查看情况"）

- 改名：菜单/路由 `meta.title`/页面标题"学生数据"→"学生成绩"。
- 列表内容、筛选、导出、"任务完成"Tab 基本不变（不派生任务得分）。
- 班级筛选下拉收敛为当前教师班级。
- **承接发布题目页的"查看情况"跳转**（见文档 03 §5.2）：
  - 读取 URL 参数 `tab=tasks&task_id={id}`，自动切到"任务完成"Tab。
  - 预选该任务并拉取 `GET /announcements/{id}/completion-report`，展示完成情况（支持按班级分组的 `per_class` 小计，因任务现可指向多个班级）。
  - 无参数时维持默认行为（停在学生列表 Tab）。

### 5.4 API 模块 `api/class.ts`

- `getClasses(params?)` 支持 `course_id`、`keyword`。
- `createClass({name,course_id})`，去 `major`。
- enroll/unenroll/import/getClassStudents 不变。

## 6. 路由改动

```text
新增: /teacher/student-admin → TeacherStudentAdmin.vue（meta.title 学生管理, role teacher）
改名: /teacher/students 的 meta.title → 学生成绩（路径可保留或改 /teacher/grades，以 00 文档为准）
```

## 7. 验收

- 新增班级按课程创建，无"所属专业"字段。
- 班级管理可按课程 + 班名搜索。
- "查看学生"只读；"学生管理"页可增删/导入学生。
- 班级有学生时删除被拒并提示清晰；无学生可正常删除。
- 教师只能看到/操作自己课程下的班级与学生。
- "学生数据"全部入口已改名为"学生成绩"。

## 8. 开放问题

1. "查看学生"沿用弹窗还是改行内展开？建议沿用弹窗（改动最小），改成弹窗仅移除其中的增删控件。
2. 学生的 `major` 字段（在 `users` 表）是否保留？建议保留（学生仍可有专业属性，仅班级不再按专业划分）。保留
