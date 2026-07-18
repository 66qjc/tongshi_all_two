# 2026-07-17 验收整改与回归记录

> **状态：** P1/P2 整改已实施并完成最终自动化回归：后端 `488 passed, 1 deselected, 1 warning`（292.23s），前端静态测试 `44/44`、`npm run type-check`、`npm run build` 均通过。当前环境未配置 `MYSQL_VERIFY_URL` / `MYSQL_VERIFY_ADMIN_URL`，真实 MySQL 验证脚本未运行。
>
> **日期：** 2026-07-17
>
> **关联：** `docs/superpowers/plans/2026-07-17-shared-question-bank-followups.md`、`docs/superpowers/plans/2026-07-17-shared-question-bank-ui-alignment.md`、`docs/superpowers/specs/2026-07-17-course-purge-reference-detachment-design.md`

## 一、目标

收口共享题库、课程阶段资料删除和课程 cleanup 的本轮验收整改，补齐导入规则、贡献记录、前端组件注册和 MySQL 验证脚本安全门，避免将静态或单元测试结果误写为真实 MySQL 或浏览器验收。

## 二、范围与已实施内容

### 1. 共享题库导入与贡献记录

- 教师和管理员的 Excel 导入将“标签”列设为必填；缺少表头时在请求级拒绝，单行标签为空时只记录该行失败，不回滚同批有效行。
- 导入每行的“答案”也必须为有效非空值，不能把空单元格写入题库；该校验已在教师和管理员导入服务中补齐回归保护。
- 同一答案非空校验已覆盖旧公共课程兼容导入服务，避免保留路由绕过规则。
- 导入“课程名称”保持可选：列可缺省或为空，空值写入独立共享题库；填写不存在课程时明确报错，不静默降级为独立题。
- 管理员经 `/api/questions/import` 按非空课程名称导入时，若匹配到多个同名课程会明确拒绝，避免任意选择不同教师的课程。
- 教师下载模板的表头与说明明确“题型、标签、题干、答案”四项必填，课程名称为可选项。
- 管理员独立题库 Excel 导入支持约定的五种课程列别名。非空行内课程名称优先于默认 `mount_course_id`，只有唯一活跃公共课程可挂载；未知、私有或同名歧义课程均作为该行错误，不降级为独立题；空课程值才回退默认挂载。贡献日志按每门公共课和独立题库分别聚合，管理员模板新增空白课程名称列并同步导入说明。
- 教师、管理员与旧公共课程兼容导入服务三条路径均以行级嵌套事务隔离数据库 `flush` 失败；新增教师/管理员真实重复主键失败回归，保证失败行不会回滚同文件内已成功的题目。
- 独立题与公共课程挂载题均写入贡献日志；批量导入按公共课程和独立题库分别聚合数量，独立题使用 `public_course_id = NULL` 与“独立题库”快照。

### 2. 阶段与资料删除

- 课程详情和公共课程读路径过滤已软删资料，避免删除后仍显示幽灵资料。
- 删除阶段可在确认后级联软删该阶段下活跃资料；教师端与管理员端采用一致的确认和接口语义。

### 3. 前端与运行时配置边界

- 共享题库的星级组件已补齐按需注册，教师端和管理员端可正常使用星标展示与编辑。
- `Settings` 连续创建实例时的环境隔离已补回归：`DATABASE_URL` 与 `SECRET_KEY` 各有一条覆盖，均已通过，避免前一实例的环境值污染后一实例。
- 本轮不向应用运行时 `Settings` 或项目 `.env` 增加 MySQL 验证连接配置。验证脚本仅在 CI 或人工验收时从进程环境读取专用变量，不参与生产服务启动。

### 4. MySQL 验证脚本

- `backend/scripts/verify_course_cleanup_mysql.py` 在连接数据库前校验 `MYSQL_VERIFY_URL`、`MYSQL_VERIFY_ADMIN_URL`、`MYSQL_VERIFY_ALLOW_RESET`、`--reset` 和 `--confirm-db`。
- 脚本只允许名称匹配 `tongshi_verify_*` 的专用验证库，禁止指向正式 `tongshi` 库；新增 `app/db/base.py` 解耦 session 与 entities，并通过子进程隔离回归确认脚本导入不会间接读取项目 `.env`。
- 管理 DSN 必须与验证 DSN 指向同一 MySQL `host/port`，避免跨实例执行重置；DSN query 覆盖已禁用，控制台和报告对查询参数中的 `password`、`token`、`api_key` 等敏感值统一脱敏。
- 外键矩阵报告默认写入系统临时目录，可通过 `--output-dir` 指定输出位置。仓库内 `backend/tmp_mysql_course_fk_matrix.txt` 仅是历史临时产物，不再由当前脚本生成，也不是当前验收依赖。

## 三、验证结果

| 验证项 | 结果 |
|---|---|
| 后端完整回归 | `488 passed, 1 deselected, 1 warning`（292.23s）；排除 `test_deploy_files_static.py::test_redeploy_script_normalizes_crlf_before_remote_bash`，原因是本机 WSL 无 Linux 发行版 |
| 前端完整回归 | 静态测试 `44/44`；`npm run type-check`、`npm run build` 均通过 |
| MySQL 验证脚本单元测试 | `12 passed`（含同实例校验、查询参数脱敏与子进程 `.env` 隔离） |
| MySQL 脚本拒绝路径 | 五条拒绝路径均以非零退出码正确拒绝 |
| 验证脚本与重复题限定组 | `14 passed`，独立复审确认无阻断项 |
| `Settings` 环境隔离回归 | `DATABASE_URL`、`SECRET_KEY` 两条通过 |
| 题库定向后端回归 | `41 passed, 1 warning` |
| 本地页面验收 | 教师 `/teacher/questions`、管理员 `/admin/question-bank`、管理员 `/admin/public-courses` 均可打开且无中文乱码；教师确认课程名称可选、标签必填和新增无课程字段，管理员确认独立题与标签必填 |
| 真实 MySQL 验证脚本 | 未运行：当前未配置 `MYSQL_VERIFY_URL` / `MYSQL_VERIFY_ADMIN_URL` |

历史文档中记录的临时库 cleanup/FK 验证属于此前环境的事实，不替代本轮在当前环境中对安全门脚本的真实 MySQL 执行结果。

## 四、未闭合事项

- 本轮未点击资料或阶段删除的确认操作。单份资料“保留教师副本”、阶段“自建资料移至未分类”仅经源码确认，仍需在可控数据上补做实际危险操作验收。
- 只有在提供专用验证库连接且确认数据库名符合 `tongshi_verify_*` 时，才能执行真实 MySQL 脚本；不得使用正式库连接，也不得将验证变量写入生产运行时配置。

## 五、服务器部署影响

- **需要**服务器拉取代码。
- **需要**重启后端服务。
- **需要**重新构建并部署前端静态资源。
- **不需要**新增数据库迁移、Nginx 调整或生产运行时环境变量调整。
- `MYSQL_VERIFY_URL`、`MYSQL_VERIFY_ADMIN_URL` 与 `MYSQL_VERIFY_ALLOW_RESET` 仅供 CI 或人工验证流程临时注入，且必须指向专用验证库，绝不能指向正式数据库。
