# 发布题目设计（03 · D 组域）

- 日期：2026-05-29
- 上级文档：[`00-教师端重构总览`](2026-05-29-00-teacher-refactor-overview-design.md)
- 归属：D 组（任务/公告）
- 拍板：D 组

---

## 1. 目标

1. "任务发布"改为"发布题目"，**去除公告**，只保留给班级发题。
2. 相关命名一并更改（菜单、路由、组件、API、字段语义）。
3. 发布题目可选**多个班级**（一次发题可同时指向同课程下的多个班级）。
4. "完成情况"改为"查看情况"，且**点击直接跳转到"学生成绩"页**展示该任务的完成情况（不在发布页弹框）。

## 2. 现状（梳理结论）

- `Announcement(id,class_id,teacher_id,type,title,content,question_ids,start_time,end_time,created_at)`，`type ∈ {announcement, quiz}`，`class_id` 为**单个**班级。
- 已有教师归属：`teacher_id`，删除需本人。
- 接口：`GET/POST/DELETE /announcements`、`/{id}`、`/unread-count`、`/{id}/read`、`/{id}/complete`、`/{id}/completion-report`。
- `question_ids` 仅存列表，后端不校验；`TaskCompletion`（唯一键 `announcement_id+user_id`）记录完成；`completion-report` 返回单班级完成/未完成名单 + 是否过期。
- 前端 `TeacherAnnouncements.vue` 已支持选**单个**班级、两种 type、选题对话框（课程→章节→题型）、"完成情况"在本页弹框。
- 学生成绩页 `TeacherStudents.vue` 已有"任务完成"Tab（下拉选任务 → 展示完成报告）。

## 3. 设计取舍

### 3.1 保留 announcements 表，语义收敛为发题

不新建任务主表，沿用 `announcements`，语义收敛为"发布题目（quiz）"：

- 不再创建 `type='announcement'` 记录；`type` 恒为 `quiz`。
- 去除公告正文创建入口（`content` 字段保留可空）。

### 3.2 多班级 → 新增关联表（多对多）

`Announcement.class_id` 单班级无法满足"多个班级"，改为多对多：

```text
新增表 announcement_classes:
  id(PK), announcement_id(FK announcements, ON DELETE CASCADE),
  class_id(FK classes, ON DELETE CASCADE),
  UNIQUE(announcement_id, class_id), index(class_id)

announcements.class_id: 保留为可空（兼容历史，新发题不再写）或在重置库后删除。
推荐：随库重置后直接删除 announcements.class_id，统一走关联表。
```

- `TaskCompletion` 维持按 `announcement_id+user_id`（与具体班级无关，天然支持多班级）。
- 约束：一次发题的所有目标班级**必须同属一门课程**，且与 `question_ids` 所属课程一致（呼应一班一课程、题目同课程）。

> 备选：为每个班级各建一条 announcement。会导致同一份题目散成多条记录、完成报告需跨记录聚合，**不推荐**。

## 4. 后端改造

### 4.1 发题（创建/列表/删除）

- `POST /announcements`：`AnnouncementCreate{ course_id, class_ids: List[int], title, question_ids: List[int], start_time?, end_time? }`
  - 去 `content`；`type` 固定 `quiz`。
  - 校验：`course_id` 属当前教师；`class_ids` 非空且均属该课程；`question_ids` 非空且均属该课程。
  - 写入 announcement 主记录 + 多条 `announcement_classes`。
- `GET /announcements`（教师）：只返回本人发布的发题任务，每项带 `class_ids/class_names`（聚合自关联表）。
- `DELETE /announcements/{id}`：本人可删，级联删 `announcement_classes` + `TaskCompletion`。

### 4.2 完成情况（供学生成绩页"查看情况"）

- `GET /announcements/{id}/completion-report` 调整为**跨多班级聚合**：
  - `total_students` = 该任务所有目标班级去重学生数（同一学生可能在多班？按一班一课程通常不会，仍做去重）。
  - `completed_students` / `incomplete_students` 名单带所属班级名。
  - 按班级分组的小计（可选）：`per_class: [{class_id,class_name,total,completed}]`，便于学生成绩页分班展示。
  - `is_expired` 沿用 `end_time`。

### 4.3 学生端

- `unread-count/read/complete` 保留。
- 学生可见性：学生看到任务的条件由"`class_id==我的班级`"改为"我的班级 ∈ 该任务关联班级集合"（经 `announcement_classes` 过滤）。

## 5. 前端改造

### 5.1 发布题目页（`TeacherAnnouncements.vue` → `TeacherPublish.vue`）

- 菜单"任务发布"→"发布题目"；路由 `/teacher/announcements`→`/teacher/publish`（以 00 文档为准）。
- 表单（去公告类型与正文，固定发题）：
  - 所属课程（必选，下拉=当前教师课程）。
  - **目标班级（多选）**：多选下拉/复选，候选=该课程下的班级。
  - 标题（必选）。
  - 选题（必选，对话框筛选 课程→题型，去章节）。
  - 开始/截止时间（可选）。
- 列表：每行操作按钮 **"查看情况"**，点击 **跳转** `/teacher/grades?tab=tasks&task_id={id}`（学生成绩页 → 任务完成 Tab → 预选该任务并展示报告）。**移除本页的完成情况弹框**。
- 删除入口保留（本人）。

### 5.2 学生成绩页承接"查看情况"

详见文档 02 §5.3 补充：学生成绩页读取 URL `tab=tasks&task_id`，自动切到"任务完成"Tab 并预选该任务、拉取 `completion-report` 展示（支持分班小计）。

### 5.3 关联改名核对

- `api/announcement.ts`（可更名 `publish.ts`）：`createAnnouncement`→`publishQuestions`，入参 `{course_id,class_ids,title,question_ids,...}`。
- 学生端发题任务展示处的"公告"字样统一改为"题目/任务"。

## 6. 验收

- 发布题目页无公告类型/正文；可一次选**多个**同课程班级 + 至少一道题。
- 发布后，所有目标班级的学生都能看到该任务。
- 列表"查看情况"跳转到学生成绩页并展示该任务完成情况（含分班小计）。
- 完成报告跨多班级正确聚合（总数/已完成/未完成/过期）。
- 教师只见自己发布的发题任务；只能选自己课程下的班级与题目。
- 全端"任务发布/公告"字样已改为"发布题目"。

## 7. 开放问题

1. 目标班级是否**强制同属一门课程**？本设计按"是"（与一班一课程、题目同课程一致）。若允许跨课程多班级群发，则去掉该约束，但题目-课程归集语义会变弱。
2. 路由前缀 `/announcements` 是否迁到 `/assignments` 或 `/publish`，由 D 组拍板（影响学生端调用）。
3. `announcements.class_id` 重置库后直接删除还是保留可空兼容，由 D 组定（本设计推荐删除）。
