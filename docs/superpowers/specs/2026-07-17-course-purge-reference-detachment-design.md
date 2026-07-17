# 课程物理清理引用脱钩设计

> 状态：已按 2026-07-17 工作区实现；真实 MySQL 临时库验证已通过
> 日期：2026-07-17
> 关联计划：`docs/superpowers/plans/2026-07-17-shared-question-bank-followups.md`（J1）

## 一、目标

课程到期物理清理时：

1. 不误删全站共享题、作品、教师副本等应长期保留的数据。
2. 允许的挂载引用置空（`ON DELETE SET NULL` / 服务层显式脱钩），并固化题目挂载名称快照。
3. 同批软删子资源（班级/资料/作业）先快照再显式删除；非同批活跃或未到期阻断引用仍阻断清理。
4. 不恢复 rehome，不建系统锚点课。

## 二、真实 MySQL 入站外键矩阵

验证环境：本机 MySQL 8.0.44 临时库 `tongshi_cleanup_verify`（**未**改写正式库 `tongshi`）。
导出方式：`information_schema.KEY_COLUMN_USAGE` + `REFERENTIAL_CONSTRAINTS` + `COLUMNS`，条件 `REFERENCED_TABLE_NAME = 'courses'`。
导出脚本：`backend/scripts/verify_course_cleanup_mysql.py`。
原始快照：`backend/tmp_mysql_course_fk_matrix.txt`（验证产物，非正式业务配置）。

| 表.列 | 约束名（验证库） | DELETE_RULE | 可空 | 处理策略 |
|---|---|---|---|---|
| `questions.course_id` | `fk_questions_course_id_set_null` | **SET NULL** | YES | 服务层 cleanup 前脱钩并写 `mount_course_name_snapshot`；活跃性只看 `Question.deleted_at` |
| `materials.course_id` | `fk_materials_course_id_set_null` | **SET NULL** | YES | 同批资料快照后删除；非同批已软删资料脱钩保留；活跃资料阻断清理 |
| `projects.course_id` | `fk_projects_course_id_set_null` | **SET NULL** | YES | 作品保留并脱钩 |
| `courses.source_course_id` | `fk_courses_source_course_id_set_null` | **SET NULL** | YES | 教师副本保留，停止后续同步 |
| `courses.question_bank_root_course_id` | `fk_courses_question_bank_root_set_null` | **SET NULL** | YES | 历史 root 业务语义已退役，迁移清空；列保留 |
| `classes.course_id` | `classes_ibfk_1` | NO ACTION | NO | 同批软删班级先清理；非同批/活跃阻断 |
| `announcements.course_id` | `announcements_ibfk_2` | CASCADE | NO | 服务层按同批显式快照删除，不依赖库级级联误删；非同批阻断 |
| `course_stages.course_id` | `course_stages_ibfk_1` | NO ACTION | NO | 随课清理：先置空阶段下资料 `stage_id`，再删阶段 |
| `lessons.course_id` | `lessons_ibfk_1` | NO ACTION | NO | 历史课时表随课清理 |
| `course_progress.course_id` | `course_progress_ibfk_2` | CASCADE | NO | 历史进度随课清理 |
| `lesson_progress.course_id` | `lesson_progress_ibfk_2` | CASCADE | NO | 历史进度随课清理 |

与计划第四节 J1.1 矩阵逐项对应：可脱钩引用均为 SET NULL；阻断/随清子资源仍由服务层预检与显式清理编排，不依赖“裸 DELETE courses”自动处理共享题。

## 三、cleanup 编排

实现：`backend/app/services/soft_delete_cleanup_service.py`

1. `_course_cleanup_blockers`：活跃资料、非同批班级/作业等阻断。
2. 同批班级/资料/作业：各自 cleaner 写历史快照后删除。
3. `_detach_course_references`：题/软删资料/作品/source/root 置空，题目标题快照。
4. `_cleanup_course_history_structures`：阶段/课时/进度。
5. Core `DELETE courses`（避免 ORM cascade 误伤）。

## 四、审计与 MySQL 实测修复

MySQL 实测发现：清理审计写 `user_id="system"` 时，若 `users` 表无该行，会触发 `audit_logs.user_id` 外键失败；失败审计再把超长堆栈写入 `error_message`（512）导致二次失败。

修复（2026-07-17）：

- 系统清理审计 `user_id=None`，`user_role="system"`。
- `create_audit_log` 对 `error_message` 截断至 512；失败详情完整原因截断写入 `details.失败原因`。

## 五、验证记录

### 5.1 真实 MySQL（临时库）

```text
backend/.venv/Scripts/python.exe backend/scripts/verify_course_cleanup_mysql.py
```

结果：`ALL_MYSQL_VERIFY_OK`

断言：

- 期望 SET NULL 五类引用均存在且 `DELETE_RULE=SET NULL`
- 课程物理删除成功
- 共享题保留、`course_id IS NULL`、名称快照固化
- 作品/非同批软删资料/教师副本 source 与 root 置空
- 同批子资源存在历史快照
- `cleaned_count >= 1` 且 `failed_count = 0`

### 5.2 SQLite 外键开启

```text
pytest backend/tests/test_soft_delete_cleanup.py::test_course_cleanup_with_sqlite_foreign_keys_enabled
```

结果：passed。`PRAGMA foreign_keys=ON` 下同样完成脱钩与删课；系统审计 `user_id is None`。

## 六、部署注意

- 正式库发布前备份。
- 启动 `ensure_schema_compatibility` 会幂等调整可空列、快照回填、root 清空与 SET NULL FK 重建。
- 验证脚本只操作 `tongshi_cleanup_verify`，发布流程不要指向生产库跑 DROP DATABASE。
