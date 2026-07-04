# 日期字段迁移设计

## 目标

将 `materials.date`、`projects.date` 从字符串日期迁移到可排序、可索引的日期或时间类型。

## 当前字段

- `Material.date`：当前写入 `YYYY-MM-DD` 字符串（`String(32)`）。
- `Project.date`：当前写入 `YYYY-MM-DD` 字符串（`String(32)`），作品列表按该字段倒序。
- `ActivityEvent.date`：模型已删除，无需迁移。

## 影响范围

涉及排序和展示的调用点：

- `project_service.list_approved_projects`：`order_by(Project.date.desc())`
- `project_service.get_user_projects`：`order_by(Project.date.desc())`
- `teacher_service.list_all_projects`：`order_by(Project.date.desc())`
- `material_service` 和 `course_response_service` 中 `Material.date` 用于展示

## 推荐方案

新增 `created_at`（`DateTime`，默认 `CURRENT_TIMESTAMP`）列作为内部排序和索引列，保留旧 `date` 作为 API 兼容输出字段。

步骤：

1. `entities.py` 新增 `created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)`。
2. `schema_compat.py` 为旧库补建 `materials.created_at` 和 `projects.created_at` 列。
3. 服务层写入时不再手动赋值 `date`，改为依赖 `created_at` 自动填充。
4. 列表排序改为 `order_by(Project.created_at.desc())`。
5. API 格式化继续输出 `date: YYYY-MM-DD`（从 `created_at` 派生或保留旧 `date` 字段）。
6. 旧 `date` 列保留至少一个版本周期后废弃。

## 不推荐方案

直接原地把 `date` 列类型从 `String(32)` 改为 `Date`。该方案会影响旧库中空字符串、非法字符串和前端类型定义，且 MySQL `ALTER TABLE MODIFY` 对类型变更有限制。

## 数据迁移

1. 新增 `created_at` 列。
2. 回填：对已有记录，将合法 `YYYY-MM-DD` 转为 `created_at`；非法或空值按当前时间兜底。
3. 服务层改为按 `created_at` 排序。
4. API 响应 `date` 字段优先从 `created_at` 格式化，回退到旧 `date` 字段。
5. 观察一个版本周期后，移除旧 `date` 列。

## 验收

- MySQL 可按 `created_at` 使用索引排序。
- SQLite 测试库通过。
- API 仍返回 `date` 字符串（`YYYY-MM-DD`）。
- 旧记录迁移后排序顺序与迁移前一致。

## 服务器部署影响

- 需要 `schema_compat` 自动补列（无需手动迁移）。
- 需要重启后端服务。
- 不需要前端改动（API 输出格式不变）。
