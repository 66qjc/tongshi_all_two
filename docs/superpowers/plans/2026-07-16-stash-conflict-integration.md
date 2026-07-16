# stash 冲突整合实施计划

> **供执行代理使用：** 实施时按任务逐项处理；每完成一个任务都运行对应验证。不得在主仓 `main` 直接应用或弹出原 stash，所有处理必须在以当前 `main` 为基点的新分支与隔离工作树中完成。

**目标：** 将 `stash@{0}` 中需要保留的既有工作安全整合到当前 `main`，解决 13 个内容冲突和 1 个同名未跟踪文件冲突，同时保持已发布的统一软删除 Task1–5 业务规则不被回退。

**架构：** 以当前远端 `main` 提交 `b364535` 为唯一基线，在隔离工作树创建 `codex/resolve-stash-main-20260716` 分支后应用 stash。对冲突文件以当前 `main` 的软删除策略、清理快照与历史报表实现为主干，只移植 stash 中尚未合入的读取过滤、权限校验、前端/文档改动和测试覆盖；不使用“选择一侧全部接受”的处理方式。原 `stash@{0}` 在最终全量验证、提交并推送前不得删除。

**技术栈：** Git worktree / stash、FastAPI、SQLAlchemy、SQLite/MySQL 兼容层、pytest、Vue 3、TypeScript、Vite、Element Plus。

---

## 一、问题边界与固定规则

### 本次范围

1. 将 `stash@{0}` 中的非冲突改动和经人工合并后的冲突改动整合到新的修复分支。
2. 解决以下 13 个文本冲突：
   - `backend/app/api/v1/routes/admin_routes.py`
   - `backend/app/services/admin_public_course_service.py`
   - `backend/app/services/announcement_service.py`
   - `backend/app/services/class_service.py`
   - `backend/app/services/material_service.py`
   - `backend/app/services/project_service.py`
   - `backend/app/services/question_service.py`
   - `backend/app/services/soft_delete_service.py`
   - `backend/app/services/task_service.py`
   - `backend/docs/项目修改记录.md`
   - `backend/tests/test_integration_bugfixes.py`
   - `backend/tests/test_public_course_delete.py`
   - `backend/tests/test_public_question_contribution.py`
3. 解决同名未跟踪文件：`backend/tests/test_quiz_submit_scope.py`；以当前 `main` 已合入版本为基线，只人工迁入 stash 独有且仍符合现行接口语义的断言。
4. 对 stash 中已经自动应用的后端、前端、测试和文档改动逐个检查，保留与其对应计划一致的行为；任何与当前主线规则冲突的旧断言、旧文案或旧物理删除逻辑不得恢复。

### 明确不做

1. **不实施 Task6 管理员回收站前端。** 不修改 `frontend/src/api/admin.ts`、`frontend/src/views/admin/AdminRecycleBin.vue`，不创建 `frontend/tests/admin-recycle-bin-soft-delete-static.test.mjs`，也不把该计划项标记为完成。
2. 不恢复“保留期内提前彻底删除”的能力；`purge_resource()` 必须继续拒绝公开提前清理。
3. 不改服务器配置、Nginx、Redis、多 worker、上传限制、环境变量或真实 MySQL 数据。
4. 不删除 `stash@{0}`，不在验证前向 `main` 合并或推送。

### 合并后的硬性不变量

- 七类资源的正式删除入口仍走 `soft_delete()`；不得重新调用 ORM `delete()` 直接物理删除。
- `purge_resource()` 保持当前主线的 `403` 拒绝语义，物理清理由 `soft_delete_cleanup_service.py` 的到期任务负责。
- 资源恢复仍通过 `restore_resource()`；字符串或数值资源 ID 经过 `_coerce_resource_id()` 统一处理。
- 历史成绩、完成情况和审计中文展示仍依赖 `history_snapshot_service.py` 与现有快照读路径。
- 正常业务查询继续过滤自身及必要父资源的 `deleted_at.is_(None)`，资料/作品文件访问不得绕过软删除校验。
- 所有新增或保留的页面文案、注释与文档使用正常中文。

## 二、文件责任划分

| 分组 | 文件 | 处理原则 |
| --- | --- | --- |
| 删除策略与管理员入口 | `admin_routes.py`、`soft_delete_service.py` | 以 main 的回收站策略、ID 转换、提前 purge 禁止规则为准；只叠加 stash 中不改变策略的过滤或调用修正。 |
| 核心业务删除入口 | `admin_public_course_service.py`、`announcement_service.py`、`class_service.py`、`material_service.py`、`project_service.py`、`question_service.py` | 保留 main 的 `AuthUser` 与 `soft_delete()` 调用；合入 stash 中未重复的关联读取过滤、公告引用校验或权限校验。 |
| 历史统计 | `task_service.py` | 保留 main 的 `history_snapshot_service` 导入和历史聚合；仅叠加 stash 中不会覆盖快照结果的任务读取过滤。 |
| 回归测试 | `test_integration_bugfixes.py`、`test_public_course_delete.py`、`test_public_question_contribution.py`、`test_quiz_submit_scope.py` | 断言现行“可恢复、读取不可见、到期清理”语义；删除任何期待立即物理删除或提前 purge 成功的旧断言。 |
| 文档 | `backend/docs/项目修改记录.md`、`docs/superpowers/project-map.md`、stash 新增计划/设计/评估文档 | 记录真实合入内容、验证结果和服务器影响；不得把未做的 Task6、真实 MySQL 或服务器发布写成已完成。 |
| 自动应用的后续改动 | `frontend/src/api/question.ts`、`frontend/src/views/LearnView.vue`、`frontend/src/views/teacher/TeacherQuestions.vue` 与对应静态测试 | 保持 stash 原有功能意图，逐文件审查后运行其现有静态测试和受影响后端测试；无对应计划或与主线无关的内容不提交。 |

## 三、实施任务

### Task 1：建立可回退的整合分支并固定冲突基线

**文件：** 不修改业务文件；创建分支与隔离工作树。

- [ ] **Step 1：确认主线与原 stash 未变化**

运行：

```powershell
git fetch --prune origin
git status --short --branch
git rev-parse main
git rev-parse origin/main
git stash list -n 1
```

预期：本地和远端 `main` 都是 `b364535`，工作树干净，`stash@{0}` 仍为 `codex-safety-backup-before-main-merge-20260716-101821`。

- [ ] **Step 2：在隔离工作树创建分支并应用 stash**

```powershell
git -C C:\Users\ASUS\.codex\worktrees\tongshi-conflict-resolution-20260716 switch -c codex/resolve-stash-main-20260716
git -C C:\Users\ASUS\.codex\worktrees\tongshi-conflict-resolution-20260716 stash apply 'stash@{0}'
git -C C:\Users\ASUS\.codex\worktrees\tongshi-conflict-resolution-20260716 diff --name-only --diff-filter=U
```

预期：显示本计划列出的 13 个冲突文件；原 stash 仍保留。

- [ ] **Step 3：记录双侧版本，禁止整体接受任一侧**

```powershell
git -C C:\Users\ASUS\.codex\worktrees\tongshi-conflict-resolution-20260716 show ':2:backend/app/services/soft_delete_service.py' > tmp/soft-delete-main.py
git -C C:\Users\ASUS\.codex\worktrees\tongshi-conflict-resolution-20260716 show ':3:backend/app/services/soft_delete_service.py' > tmp/soft-delete-stash.py
git -C C:\Users\ASUS\.codex\worktrees\tongshi-conflict-resolution-20260716 diff --no-index -- tmp/soft-delete-main.py tmp/soft-delete-stash.py
```

预期：每个冲突文件都按 `:2`（当前 main）和 `:3`（stash）逐段比对；不执行 `git checkout --ours/--theirs` 覆盖整文件。

### Task 2：先解决删除策略与管理员入口冲突

**文件：**
- Modify: `backend/app/api/v1/routes/admin_routes.py`
- Modify: `backend/app/services/soft_delete_service.py`
- Test: `backend/tests/test_soft_delete_lifecycle.py`
- Test: `backend/tests/test_soft_delete_cleanup.py`
- Test: `backend/tests/test_soft_delete_snapshots.py`

- [ ] **Step 1：保留当前 main 的提前清理拒绝规则**

在 `soft_delete_service.py` 的 `purge_resource()` 中保留当前 main 的固定拒绝实现：

```python
def purge_resource(db, resource_type, resource_id, operator):
    """公开清理入口在保留期内固定拒绝。"""
    raise BusinessException(403, "资源仍在保留期，不能提前彻底删除")
```

不得恢复 stash 中查询资源、直接删除实体、提前清理关联记录或返回成功的实现。

- [ ] **Step 2：保留统一 ID 转换与恢复调用**

在 `restore_resource()` 和管理员恢复路由中保留 `_coerce_resource_id()` 的统一转换；路径参数继续允许字符串 ID，恢复成功响应保持现有统一格式。

- [ ] **Step 3：逐段合并管理员列表/删除入口的非策略变更**

在 `admin_routes.py` 中保留 main 的回收站列表、恢复与 purge 路由契约；仅迁入 stash 中不改变“软删除、不可提前 purge”含义的中文说明、过滤条件或参数兼容代码。若 stash 片段调用 `soft_delete(..., cascade=False)`，仅在其与当前级联规则一致时保留；否则采用 main 的调用参数。

- [ ] **Step 4：运行删除策略回归**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_soft_delete_lifecycle.py backend/tests/test_soft_delete_cleanup.py backend/tests/test_soft_delete_snapshots.py -q --basetemp=tmp/pytest-conflict-policy
```

预期：全部通过；删除后资源可恢复，提前 purge 被拒绝，到期清理与快照回归通过。

### Task 3：解决核心资源删除入口与读取过滤冲突

**文件：**
- Modify: `backend/app/services/admin_public_course_service.py`
- Modify: `backend/app/services/announcement_service.py`
- Modify: `backend/app/services/class_service.py`
- Modify: `backend/app/services/material_service.py`
- Modify: `backend/app/services/project_service.py`
- Modify: `backend/app/services/question_service.py`
- Test: `backend/tests/test_public_course_delete.py`
- Test: `backend/tests/test_public_question_contribution.py`
- Test: `backend/tests/test_soft_delete_read_filters.py`
- Test: `backend/tests/test_soft_deleted_file_access.py`

- [ ] **Step 1：统一删除入口的调用方式**

每个正式删除函数保留当前 main 的调用模式：

```python
from app.schemas.common import AuthUser
from app.services.soft_delete_service import soft_delete

operator = AuthUser(id=operator_id, name="", role=operator_role)
soft_delete(db, resource, operator, action="course.delete")
```

其中 `operator_id`、`operator_role` 和 action 名称沿用当前函数已有权限语义；不得因为解决冲突而恢复 `db.delete(resource)`。

- [ ] **Step 2：逐项迁入 stash 的读取过滤和关联保护**

- 公共课程、公告、班级、资料、作品和题目查询必须保留自身 `deleted_at.is_(None)`。
- 需要父资源有效性的读取继续联查课程、班级或用户的 `deleted_at.is_(None)`。
- `question_service.py` 中若 stash 增加了“公告正在引用题目”的校验，只在其返回现有业务异常且不改变共享题库软删除规则时迁入。
- `project_service.py` 的作品删除仍保留图片与点赞等关联历史，不得在删除入口物理移除。

- [ ] **Step 3：运行资源删除、贡献与读取过滤回归**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_public_course_delete.py backend/tests/test_public_question_contribution.py backend/tests/test_soft_delete_read_filters.py backend/tests/test_soft_deleted_file_access.py -q --basetemp=tmp/pytest-conflict-resource
```

预期：全部通过；已软删除资源不在正常读取结果中，公共课程/题目贡献关系不被破坏，旧文件访问链接失效。

### Task 4：解决任务统计和综合回归测试冲突

**文件：**
- Modify: `backend/app/services/task_service.py`
- Modify: `backend/tests/test_integration_bugfixes.py`
- Modify: `backend/tests/test_quiz_submit_scope.py`
- Modify: `backend/tests/test_assignment_practice_flow.py`
- Test: `backend/tests/test_030405_management_systems.py`
- Test: `backend/tests/test_assignment_practice_flow.py`
- Test: `backend/tests/test_quiz_submit_scope.py`
- Test: `backend/tests/test_integration_bugfixes.py`

- [ ] **Step 1：以 main 的快照历史聚合为任务统计基线**

`task_service.py` 必须保留：

```python
from app.services.history_snapshot_service import (
    history_attempt_totals,
    history_completion_rows,
)
```

以及当前 main 中在活跃数据查询后补充历史快照统计的逻辑。stash 中不含该依赖的旧片段不得覆盖它。

- [ ] **Step 2：合并仍有效的答题范围与任务读取断言**

`test_quiz_submit_scope.py` 使用当前 main 的已跟踪文件作为基线。通过比较 stash 第三父提交中的同名文件，只新增对“活跃选课或公共共享题库”边界仍有效的测试；不复制重复用例，不降低当前断言强度。

- [ ] **Step 3：更新综合回归的删除预期**

`test_integration_bugfixes.py`、`test_assignment_practice_flow.py` 和相关测试必须断言：正式删除后 `deleted_at` 被设置、正常列表不可见、必要时可恢复；不得断言关联行被删除或提前物理清理成功。

- [ ] **Step 4：运行任务与综合回归**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_030405_management_systems.py backend/tests/test_assignment_practice_flow.py backend/tests/test_quiz_submit_scope.py backend/tests/test_integration_bugfixes.py -q --basetemp=tmp/pytest-conflict-task
```

预期：全部通过；历史快照统计不被回退，自由练习提交不泄露越权题目答案。

### Task 5：审查并保留自动应用的 stash 改动

**文件：**
- Modify: `backend/app/api/v1/routes/announcement_routes.py`
- Modify: `backend/app/api/v1/routes/material_routes.py`
- Modify: `backend/app/api/v1/routes/public_learning_routes.py`
- Modify: `backend/app/api/v1/routes/question_routes.py`
- Modify: `backend/app/db/schema_compat.py`
- Modify: `backend/app/models/entities.py`
- Modify: `backend/app/schemas/common.py`
- Modify: `backend/app/services/access_control_service.py`
- Modify: `backend/app/services/public_learning_service.py`
- Modify: `backend/app/services/question_bank_service.py`
- Modify: `backend/app/services/quiz_service.py`
- Modify: `frontend/src/api/question.ts`
- Modify: `frontend/src/components/AppFooter.vue`
- Modify: `frontend/src/components/home/HeroSection.vue`
- Modify: `frontend/src/components/home/StatsSection.vue`
- Modify: `frontend/src/components/learn/MaterialInlineReader.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/views/AboutView.vue`
- Modify: `frontend/src/views/ActDetailView.vue`
- Modify: `frontend/src/views/ActView.vue`
- Modify: `frontend/src/views/CourseDetailView.vue`
- Modify: `frontend/src/views/LearnView.vue`
- Modify: `frontend/src/views/PracticeQuizView.vue`
- Modify: `frontend/src/views/PrivacyView.vue`
- Modify: `frontend/src/views/teacher/TeacherQuestions.vue`
- Modify: `frontend/tests/act-guest-access-static.test.mjs`
- Create: `frontend/tests/act-showcase-image-fallback-static.test.mjs`
- Modify: `frontend/tests/home-first-stage-static.test.mjs`
- Modify: `frontend/tests/nginx-local-file-preview-static.test.mjs`
- Modify: `frontend/tests/public-learning-static.test.mjs`
- Create: `frontend/tests/teacher-question-bank-static.test.mjs`
- Create/Modify: stash 中已经列明的后端测试、计划、规格与评估文档；仅在与本计划范围一致时纳入提交。

- [ ] **Step 1：逐文件确认来源与计划一致性**

对每个自动应用文件运行：

```powershell
git diff -- backend/app/api/v1/routes/announcement_routes.py backend/app/api/v1/routes/material_routes.py backend/app/api/v1/routes/public_learning_routes.py backend/app/api/v1/routes/question_routes.py backend/app/services/access_control_service.py backend/app/services/public_learning_service.py backend/app/services/question_bank_service.py backend/app/services/quiz_service.py frontend/src/api/question.ts frontend/src/views/LearnView.vue frontend/src/views/teacher/TeacherQuestions.vue
```

仅保留能对应以下已存在计划或当前路线图的变更：答题范围收紧、软删除读路径过滤、学习页教程站改造、共享题库添加人/星级、资料阅读/公共文件链修复、单机运维计划与总体治理文档。无法对应计划、与 Task6 有关或改变服务器配置的文件从整合分支撤出。

- [ ] **Step 2：处理新测试文件与同名文件冲突**

- `backend/tests/test_soft_delete_relationships.py` 和 `backend/tests/test_soft_deleted_file_access.py` 仅在断言现行软删除规则时加入。
- `backend/tests/test_quiz_submit_scope.py` 不从 stash 直接检出；按 Task 4 的基线差异手工合并。
- 前端新增静态测试必须与对应页面改动同时保留，且测试文案使用中文。

- [ ] **Step 3：运行受影响的静态测试和前端构建**

```powershell
npm.cmd run type-check --prefix frontend
npm.cmd run build --prefix frontend
npm.cmd run test:admin-question-batch-delete --prefix frontend
npm.cmd run test:message-refresh --prefix frontend
npm.cmd run test:no-counter-store --prefix frontend
```

预期：全部通过。Task6 专用 `admin-recycle-bin-soft-delete-static.test.mjs` 不在本次命令中，因为该任务不在范围内。

### Task 6：统一文档、执行全量验证并提交

**文件：**
- Modify: `backend/docs/项目修改记录.md`
- Modify: `docs/superpowers/project-map.md`
- Create/Modify: `docs/superpowers/2026-07-15-project-consistency-assessment.md`
- Create/Modify: `docs/superpowers/plans/2026-07-13-quiz-scope-soft-delete-read-filters.md`
- Create/Modify: `docs/superpowers/plans/2026-07-14-learn-tutorial-site-ui.md`
- Create/Modify: `docs/superpowers/plans/2026-07-14-material-reader-auto-load.md`
- Create/Modify: `docs/superpowers/plans/2026-07-14-public-file-chain-fix.md`
- Create/Modify: `docs/superpowers/plans/2026-07-14-shared-question-bank-closure.md`
- Create/Modify: `docs/superpowers/plans/2026-07-14-single-server-ops-hardening.md`
- Create/Modify: `docs/superpowers/plans/2026-07-15-overall-governance-roadmap.md`
- Create/Modify: `docs/superpowers/specs/2026-07-15-overall-governance-roadmap-design.md`
- Create: `docs/superpowers/plans/2026-07-16-stash-conflict-integration.md`

- [ ] **Step 1：合并修改记录而非拼接冲突两侧**

`backend/docs/项目修改记录.md` 只保留一条本次整合记录，内容必须包含：解决 stash 冲突的范围、保留的软删除安全规则、实际执行的测试命令与结果、Task6 未合入、真实 MySQL 未验证，以及服务器部署影响。删除两侧重复或互相矛盾的阶段状态。

- [ ] **Step 2：更新稳定事实文档**

`project-map.md` 与总体治理路线图必须准确标注：Task1–5 已合入 main 并完成 SQLite 回归；Task6 仍未合入；stash 原始备份在推送前保留；真实 MySQL 和服务器发布不因本地测试而视为完成。

- [ ] **Step 3：执行全量验证**

```powershell
New-Item -ItemType Directory -Force tmp | Out-Null
backend\.venv\Scripts\python.exe -m pytest backend/tests -q --basetemp=tmp/pytest-stash-conflict-final
npm.cmd run build --prefix frontend
git diff --check
git status --short
```

预期：后端全量测试通过；前端构建通过；`git diff --check` 无输出；工作树只包含本计划列出的业务、测试和文档文件。

- [ ] **Step 4：更新知识图并进行最终核对**

```powershell
graphify update .
git diff --stat main...HEAD
git diff --name-only main...HEAD
git stash list -n 1
```

预期：知识图已更新；差异不包含 Task6 前端文件；`stash@{0}` 仍存在。

- [ ] **Step 5：创建独立提交并等待复核后合并**

```powershell
git add backend frontend docs graphify-out  # 仅暂存 git diff --name-only main...HEAD 列出的文件
git commit -m "fix: 整合主线后的遗留改动并保留软删除规则"
```

预期：提交创建在 `codex/resolve-stash-main-20260716`，不直接提交到 `main`。经复核后再合并、推送并决定是否删除原 stash。

## 四、验收标准

1. 冲突索引为空：`git diff --name-only --diff-filter=U` 无输出。
2. 七类删除入口仍为软删除；提前 purge 固定返回 403；到期清理与快照保留。
3. 已软删除课程、班级、资料、作业、作品、公告、题目和用户不出现在正常业务读取中，文件读取不能绕过过滤。
4. 共享题库、公告题目引用、任务统计和历史成绩的现有主线规则不回退。
5. 后端全量 pytest、前端类型检查/构建及现有静态测试通过。
6. 文档未把 Task6、真实 MySQL 或服务器发布写成已完成。
7. 原 `stash@{0}` 在分支验证、提交和人工复核前仍保留，可用于追溯。

## 五、风险与部署影响

- **主要风险：** stash 基于 `b0f9ce7`，而 `main` 已引入 12 个软删除提交；若整体接受 stash 一侧，会重新开放提前物理删除、丢失快照统计或覆盖正常读路径过滤。
- **缓解：** 所有冲突逐段合并，以当前 main 的策略服务、清理服务和快照服务为权威；每类业务入口都由回归测试覆盖。
- **服务器部署影响：** 本计划实施与验证阶段不修改服务器。最终合并后，服务器需先拉取代码、重启后端服务；若服务器本地构建前端则重新构建前端。真实 MySQL 需在备份后执行兼容初始化与专门验证；不调整环境变量、Redis、Nginx 或上传配置。
