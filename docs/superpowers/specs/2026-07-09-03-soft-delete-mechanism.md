# 软删除机制设计

> **已废止（部分）：** 文中“删除课程前先转挂共享题到其他未删除课程 / 题库根”的现行规则已废止。
> **现行规则：** 删课不转挂、不软删、不隐藏共享题；活跃共享题只看 `Question.deleted_at`；课程仅是挂载上下文，物理清理时允许 `course_id` 等引用脱钩。
> **依据：** `docs/superpowers/specs/2026-07-15-unified-soft-delete-business-rules-design.md`、`docs/superpowers/plans/2026-07-17-shared-question-bank-followups.md`。

## 一、背景与目标

### 当前问题
- 物理删除导致数据不可恢复
- 误删课程后班级、资料全部丢失
- 学生删除账号后答题记录全部丢失
- 无法追溯删除操作历史

### 目标
1. 核心表实现软删除
2. 支持数据恢复
3. 管理员可查看已删除数据
4. 保留删除操作审计记录

## 二、数据库设计

### 2.1 需要软删除的表（7张）
- users, courses, classes, announcements
- projects, materials, questions

### 2.2 新增字段
统一添加：deleted_at, deleted_by

### 2.3 级联删除策略调整
- Course删除 -> 软删除所有Class、Material、Announcement
- Question 属于全站共享题库；删除课程前先转挂到其他未删除课程，不随课程软删除或恢复
- User删除 -> 保留QuizAttempt、Project

## 三、Service层改造

### 3.1 统一过滤Mixin
SoftDeleteMixin提供：
- filter_active() 过滤已删除数据
- soft_delete() 软删除实例
- restore() 恢复已删除实例

### 3.2 应用到所有Service
所有查询自动过滤deleted_at IS NULL

## 四、API 接口设计

### 4.1 查看已删除数据
GET /api/admin/deleted/{resource_type}

### 4.2 恢复数据
POST /api/admin/restore/{resource_type}/{id}

### 4.3 彻底删除
DELETE /api/admin/purge/{resource_type}/{id}

## 五、前端改动

### 5.1 管理员回收站页面
路由: /admin/recycle-bin
功能: 查看/恢复/彻底删除

## 六、数据迁移
为7张表添加deleted_at和deleted_by字段及索引

## 七、测试计划
- 软删除后查询不到
- 包含已删除参数可查到
- 恢复后重新可见
- 级联软删除

## 八、实施风险

### 高风险
1. 查询遗漏：100+处查询需要改造
2. 级联删除逻辑需要重新设计

### 中风险
1. 性能影响：每个查询多一个条件
2. 唯一约束冲突

## 九、服务器部署
1. 备份数据库
2. 执行迁移
3. 验证查询逻辑
4. 回滚预案

## 十、后续优化
1. 自动清理超过180天的已删除数据
2. 批量恢复
3. 删除原因记录

## 十一、实施记录（2026-07-09）

### 已落地内容
- 在 `User`、`Class`、`Course`、`Material`、`Question`、`Project`、`Announcement` 七类核心资源上增加 `deleted_at`、`deleted_by` 字段，并在 `schema_compat.py` 中补齐兼容建表/补字段逻辑。
- 新增 `soft_delete_service.py`，提供回收站列表、软删除、恢复、彻底删除和 `filter_active` 工具函数。
- 课程删除改为软删除，并级联软删除课程下班级、资料和公告；删除行为会写入审计日志。
- 恢复课程时会按相同删除时间和删除人精确恢复本次级联删除的班级、资料和公告，不会误恢复更早单独删除的子资源。
- 管理员端新增回收站接口：`GET /api/admin/deleted/{resource_type}`、`POST /api/admin/restore/{resource_type}/{resource_id}`、`DELETE /api/admin/purge/{resource_type}/{resource_id}`。
- 前端新增管理员“数据回收站”页面，可按资源类型查看、恢复或彻底删除数据；彻底删除前有确认弹窗。
- 已验证软删除用户不能登录，软删除课程不会继续出现在课程列表中。

### 当前边界
- 第一版优先覆盖核心课程删除链路、登录安全边界和管理员回收站；全项目历史查询仍需在后续长期治理中继续排查遗漏过滤。
- 彻底删除属于危险操作，只在管理员回收站暴露入口；生产执行前应先备份数据库。

### 验证记录
- `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_030405_management_systems.py -q`：5 passed。
- `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_lessons_progress.py backend/tests/test_030405_management_systems.py -q`：22 passed, 1 warning。
- `frontend` 下 `npm run build`：通过。
- 真实浏览器验收：管理员访问 `/admin/recycle-bin` 时 `GET /api/admin/deleted/courses` 返回 200，软删除课程的名称、删除人、删除时间及“操作历史/恢复/彻底删除”入口均正常显示；本轮浏览器验收未实际执行恢复或彻底删除，恢复语义继续由后端集成测试覆盖。

### 服务器部署影响
- 需要服务器拉取代码并重启后端，使兼容层补齐软删除字段和回收站接口。
- 需要重新构建并部署前端静态资源，管理员端才会出现“数据回收站”入口。
- 建议部署前备份数据库；如服务器采用正式迁移流程，应补 Alembic 迁移后执行。
- 不需要修改环境变量或 Nginx 配置。

## 十二、共享题库删除修正（2026-07-10）

### 修正内容

- 教师课程软删除和管理员公共课程删除统一调用 `rehome_questions_before_course_delete()`，先转挂有效题目，再删除课程。
- 承接目标优先选择未删除公共课程；没有公共课程时选择其他未删除课程作为外键锚点。
- 有题目但没有任何承接课程时返回 400，课程和题目均保持原状。
- 题目不进入课程软删除和恢复批次；恢复课程不会复制题目或把题目转回原课程。
- 教师题目编辑权依据 `Question.created_by`，承接课程所有者不会因 `course_id` 变化获得编辑权。
- 教师、管理员新增或导入题目时统一写入 `created_by`。

### 验证记录

- 课程、题库、公共课程删除和贡献日志回归：74 passed, 1 warning。
- 后端全量测试：241 passed, 1 warning。

### 服务器部署影响

- 需要服务器拉取代码并重启后端；部署前建议备份数据库。
- 本次修正不新增表或字段，不需要数据库迁移、环境变量或 Nginx 修改。
- 阶段 A 还包含前端改密 Token 保存修复，整体上线需要重新构建并部署前端静态资源。
