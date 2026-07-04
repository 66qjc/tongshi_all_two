# User 主键迁移设计

## 目标

降低跨表 JOIN 成本，同时保留学生学号、教师工号、管理员账号作为登录账号。

## 当前状况

- `User.id`：`String(32)`，同时作为登录账号和主键。
- 被 `courses.created_by`、`classes.created_by`、`projects.author_id`、`materials.created_by`（间接）、`quiz_attempts.user_id`、`student_class_enrollment.user_id`、`announcements.created_by` 等十余张表引用为外键。
- 字符串主键 JOIN 在 MySQL InnoDB 中成本高于整型主键（字符串比较 vs 整型比较），在数据量大时影响查询性能。

## 推荐方案

新增整型 `User.numeric_id`（`Integer, autoincrement, unique, index`）作为内部主键，保留当前 `User.id` 为唯一业务账号字段。后续逐表增加 `user_pk` 外键并双写，验证完成后再切换 JOIN。

步骤：

1. `entities.py` 新增 `numeric_id = Column(Integer, autoincrement=True, unique=True, index=True)`。
2. `schema_compat.py` 为旧库补建 `users.numeric_id` 列和唯一索引。
3. 回填：为所有已有用户分配 `numeric_id`。
4. 新建用户时自动生成 `numeric_id`。
5. 引用用户的表逐批新增可空 `user_pk` 列，写入时双写。
6. 验证后，服务层 JOIN 改为优先使用整型列。
7. 全量验证后再收紧 NOT NULL 和外键。

## 不推荐方案

直接把 `users.id` 从字符串改为自增整型。该方案会同时破坏：

- 登录账号匹配（`WHERE users.id = :username` 失效）
- JWT `sub` 字段（从字符串变整型）
- 所有外键（十余张表需要同时 ALTER TABLE）
- 测试夹具（所有 seed data 中的字符串 ID 需要重写）
- 前端 `authStore.user.id` 类型

## 迁移阶段

| 阶段 | 内容 | 风险 |
|------|------|------|
| 1 | 新增 `users.numeric_id` 列 + 回填 | 低 |
| 2 | 高频外键表（`projects`, `courses`, `classes`）新增 `user_pk` 列 + 双写 | 中 |
| 3 | 服务层 JOIN 切换为 `user_pk`，保留字符串列兼容 | 中 |
| 4 | 低频外键表迁移 | 低 |
| 5 | 全量验证后收紧 NOT NULL | 高（需停机） |

## 验收

- 登录账号仍是原 `id` 字符串。
- JWT `sub` 在迁移期仍可识别旧账号。
- 所有现有测试夹具不需要一次性重写。
- 高频 JOIN（作品列表、课程列表）使用整型外键后查询计划改善。

## 引用清单

以下表和字段引用了 `users.id`，迁移时需要逐一处理：

- `courses.created_by` → `ForeignKey("users.id")`
- `classes.created_by` → `ForeignKey("users.id")`
- `projects.author_id` → `ForeignKey("users.id")`
- `quiz_attempts.user_id` → `ForeignKey("users.id")`
- `student_class_enrollment.user_id` → `ForeignKey("users.id")`
- `announcements.created_by` → `ForeignKey("users.id")`
- `password_reset_requests.user_id` → `ForeignKey("users.id")`
- `password_reset_requests.resolved_by` → `ForeignKey("users.id")`
- `security_questions.user_id` → `ForeignKey("users.id")`
- `task_completions.user_id` → `ForeignKey("users.id")`
- `activity_events.created_by` → `ForeignKey("users.id")`（如仍存在）

## 服务器部署影响

- 阶段 1-2：`schema_compat` 自动补列，重启后端即可。
- 阶段 3：需要重启后端，可能需要短暂停写以完成数据一致性校验。
- 阶段 5：需要计划停机窗口。
