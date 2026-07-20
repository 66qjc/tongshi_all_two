# 空阶段删除失败修复设计

- 状态：已实现（2026-07-19）
- 日期：2026-07-19
- 范围：教师课程详情、管理员公共课程阶段删除
- 关联：阶段级联软删、资料软删读路径过滤、资料原位恢复快照

## 1. 背景与问题

教师端与管理员端均出现：

- 阶段下**看起来没有资料**时删除失败；
- 阶段下**仍有活跃资料**时，确认级联后反而可能删除成功。

本地对「完全空阶段」的自动化测试可通过，说明问题不是“空阶段接口写死禁止删除”，而是**页面不可见的引用**在物理删阶段时触发数据库外键/完整性失败。

## 2. 根因

删除阶段的当前主路径（`course_stage_service.delete_stage`）大致为：

1. 仅统计并处理 `deleted_at is None` 的活跃资料；
2. `cascade_materials=True` 时对活跃资料 `soft_delete`；
3. 直接 `db.delete(stage)`。

页面展示的资料数只含活跃资料。因此界面「0 份资料」不等于库中无引用。

| 隐藏引用 | 页面表现 | 当前删除路径 | 结果 |
|---|---|---|---|
| 软删资料仍挂 `stage_id` | 已过滤，显示 0 份 | 不进级联，直接删阶段 | 若 `materials.stage_id` 外键不是 `ON DELETE SET NULL`（旧库兼容脚本未保证补齐）→ 失败 |
| 其它阶段 `source_stage_id` 仍指向本阶段 | 不可见 | 教师端未脱钩 | 外键失败（本地可复现 `FOREIGN KEY constraint failed`） |
| 管理端副本阶段引用公共源阶段 | 源阶段像空 | 依赖副本清理完整性 | 清理不完整时失败或不一致 |

补充：

- 教师端删除失败文案固定为「删除失败，请稍后重试」，掩盖后端真实原因；
- ORM 中 `CourseStage.source_stage_id` 未统一声明 `ondelete="SET NULL"`；
- `schema_compat` 对 `materials.stage_id` 主要补列与索引，未保证生产 MySQL 一定存在 `ON DELETE SET NULL` 外键。

## 3. 目标行为

1. **完全空阶段**可删。
2. **仅有软删资料**的阶段可删；不把幽灵资料带回页面。
3. **有活跃资料**时：确认后级联软删活跃资料，再删阶段（现有产品语义保留）。
4. **被其它阶段 `source_stage_id` 引用**时仍可删；引用置空。
5. 教师端与管理员端规则一致；管理端「教师自建资料保留并移至未分类」语义保留。
6. 失败时前端展示后端真实中文 `message`。

## 4. 范围

### 4.1 范围内

| 层 | 内容 |
|---|---|
| 后端写路径 | `delete_stage` 物理删除前强制脱钩全部引用 |
| 管理端删公共阶段 | 与加强后的 `delete_stage` 对齐，保留副本特殊语义 |
| ORM / 兼容 | `source_stage_id` 明确 `ON DELETE SET NULL`；MySQL 尽量补齐相关 FK |
| 前端 | 教师端删除失败展示后端 message |
| 测试 / 文档 | 覆盖空阶段、仅幽灵资料、入站 source 引用、级联回归 |

### 4.2 范围外

- 不给阶段表新增 `deleted_at`（阶段仍物理删行）
- 不改资料软删/回收站/物理清理策略
- 不改共享题库
- 不改「有活跃资料默认拒绝、前端正式入口传级联」的兼容约定
- 本轮不做全库悬挂 `stage_id` 批量清理运维脚本（可选后续）

## 5. 方案

### 5.1 主路径：服务层强制脱钩（正确性主保障）

文件：`backend/app/services/course_stage_service.py`

`delete_stage` 固定顺序：

1. 查询阶段；教师侧继续按课程归属过滤。
2. 计算活跃资料列表（`deleted_at is None`）。
3. 若存在活跃资料且 `cascade_materials=False`：继续抛业务错误
   `阶段下仍有资料，请先移出或删除资料，或确认级联删除`。
4. 若存在活跃资料且 `cascade_materials=True`：对活跃资料 `soft_delete`（写 `deleted_stage_*` 快照，行为与现网一致）。
5. **新增**：将该阶段下**全部资料**（含已软删）的 `stage_id` 置 `NULL`。
6. **新增**：将所有 `course_stages.source_stage_id == stage_id` 置 `NULL`。
7. `db.delete(stage)` 并 `flush`。

设计要点：

- 活跃资料：先软删写快照，再脱钩 `stage_id`，符合「快照优先、定位可丢」的原位恢复设计。
- 已软删资料：只脱钩，不二次软删。
- **不把数据库 `ON DELETE SET NULL` 当作唯一正确性来源**；服务层脱钩后，即使旧库缺 FK 也能删。

### 5.2 管理端公共阶段删除

文件：`backend/app/api/v1/routes/admin_public_course_routes.py`

保留现有产品语义：

- 副本中同步资料（有 `source_material_id`）：级联时软删；
- 副本中教师自建资料：`stage_id = None` 移未分类；
- 删除副本阶段后，源阶段统一走加强后的 `delete_stage`。

若副本清理后源阶段仍可能被软删行或其它 `source_stage_id` 引用，由服务层第 5/6 步兜底。

### 5.3 ORM 与 schema_compat（防御层）

| 点 | 处理 |
|---|---|
| `CourseStage.source_stage_id` | ORM 写明 `ForeignKey(..., ondelete="SET NULL")` |
| `Material.stage_id` | 保持 `ON DELETE SET NULL` |
| MySQL `schema_compat` | 若缺则尽量补齐 `materials.stage_id`、`source_stage_id` 的 `ON DELETE SET NULL` FK |
| SQLite 旧库 | 不强行重建大表；依赖服务层脱钩保证行为 |

### 5.4 前端

| 文件 | 改动 |
|---|---|
| `TeacherCourseDetail.vue` | 删除失败使用 `error?.message \|\| '删除失败，请稍后重试'` |
| `AdminPublicCourses.vue` | 已有 message 展示则保持；必要时对齐 |

确认弹窗与 `cascadeMaterials: true` 请求保持不变。

## 6. 错误处理

| 场景 | 行为 |
|---|---|
| 阶段不存在 / 无权限 | 404 或既有归属过滤结果 |
| 有活跃资料且未级联 | 400，中文提示保持现状 |
| 脱钩后删除 | 成功 |
| 其它数据库异常 | 走既有异常处理；前端展示 message |

## 7. 验收标准

1. 教师端新建空阶段可删。
2. 教师端删光活跃资料（仅软删残留）后，阶段显示 0 份且可删。
3. 教师端有活跃资料时确认级联可删，资料软删且快照保留。
4. 管理端空公共阶段可删。
5. 管理端仅幽灵资料公共阶段可删。
6. 管理端教师自建副本资料保留/移未分类不回归。
7. 被 `source_stage_id` 引用的阶段可删，引用方置空。
8. 教师端失败提示可见后端真实中文原因。
9. 无业务数据迁移脚本要求。

## 8. 服务器部署影响

| 项 | 是否需要 |
|---|---|
| 拉代码 | 是 |
| 重启后端 | 是 |
| 重建前端 | 是（错误提示） |
| 业务库迁移 | 否 |
| 环境变量 / Nginx | 否 |
| schema_compat 补 FK | MySQL 缺约束时启动尝试；主修复不依赖其成功 |

## 9. 风险

| 风险 | 处理 |
|---|---|
| 脱钩后软删资料失去 `stage_id` | 依赖 `deleted_stage_*` 快照原位恢复 |
| 断开 `source_stage_id` | 源阶段已不存在，引用本应清空，与管理端删源阶段一致 |
| 生产缺 FK | 服务层脱钩为主路径 |

## 10. 预估涉及文件

- `backend/app/services/course_stage_service.py`
- `backend/app/api/v1/routes/admin_public_course_routes.py`
- `backend/app/models/entities.py`
- `backend/app/db/schema_compat.py`
- `backend/tests/test_stage_material_delete_cascade.py`（或新测试）
- `frontend/src/views/teacher/TeacherCourseDetail.vue`
- `frontend/tests/course-stage-delete-static.test.mjs`
- `backend/docs/项目修改记录.md`
- 本设计与对应实施计划
