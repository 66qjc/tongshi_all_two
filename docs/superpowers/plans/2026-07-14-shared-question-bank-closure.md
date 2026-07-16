# 2026-07-14 共享题库闭环实施计划

> **供执行代理使用：** 按任务顺序实施；每一步先写或调整受影响测试，再运行测试验证，再写最小实现。计划中的查重语义是既定边界，禁止借本任务重构。

**目标：** 让全站共享题库在教师端完整展示和维护“添加人、1-5 星级、编辑归属”，同时让手工新增、编辑、Excel 导入对现有题干哈希查重规则保持一致。

**架构：** `Question.created_by`、`star_rating` 和 `stem_hash` 已存在，不新增表、迁移或接口路径。题目列表接口补齐现有字段和创建人姓名，教师端显示并编辑星级；服务层把既有 `stem_hash` 规则补齐到更新、导入路径。全站共享和完整指纹查重逻辑继续保留。

**技术栈：** FastAPI、SQLAlchemy、Pydantic、Vue 3 `<script setup lang="ts">`、Element Plus、SQLite 测试库。

---

## 已确认边界

- 题库继续全站共享；题目仍归属创建时选择的课程。
- 保留 `find_duplicate_question()` 的“题型 + 题干 + 选项 + 答案”完整指纹查重；不修改 `test_question_duplicate_candidates.py` 中“同题干不同答案可共存”的单元语义。
- 新增题目的 `stem_hash` 继续作为更严格的同题干拦截；本计划只让更新和 Excel 导入与该既有规则一致。
- 教师只能编辑 `Question.created_by` 等于自己的题；不改变“教师不能删除题目”的长期约定。
- 不新增题库评分、收藏、审核流、题目删除入口、数据库迁移或新的状态管理方式。

## 文件范围

- 修改：`backend/app/api/v1/routes/question_routes.py`
- 修改：`backend/app/services/question_service.py`
- 修改：`backend/app/schemas/common.py`
- 修改：`backend/tests/test_public_question_contribution.py`
- 修改：`backend/tests/test_question_import_skip.py`
- 修改：`frontend/src/api/question.ts`
- 修改：`frontend/src/views/teacher/TeacherQuestions.vue`
- 新建：`frontend/tests/teacher-question-bank-static.test.mjs`
- 修改：`docs/superpowers/project-map.md`

不修改：`backend/app/models/entities.py`、`backend/app/services/question_bank_service.py`、`backend/tests/test_question_duplicate_candidates.py`、教师端其他页面、管理员端、学生答题接口。

### 任务 1：锁定题库接口契约

**目标：** 列表和创建响应能让教师端同时获得题目添加人、添加人姓名、星级和真实编辑归属。

- [x] 在 `backend/tests/test_public_question_contribution.py` 增加 API 回归：教师创建一题（`star_rating=5`）后，经另一课程的 `/api/questions` 共享列表读取该题，断言 `created_by` 为创建教师 ID、`creator_name` 为教师姓名、`star_rating` 为 5、创建教师 `is_owner=true`。
- [x] 在同一测试创建第二位教师，并断言其读取第一位教师的题目时 `is_owner=false`；不尝试编辑。
- [x] 运行 `backend/.venv/Scripts/python.exe -m pytest tests/test_public_question_contribution.py -q`，预期接口字段断言失败。
- [x] 修改 `backend/app/schemas/common.py` 的 `QuestionOut`，增加 `creator_name: Optional[str] = None` 和 `is_owner: bool = False`，保留现有 `created_by`、`star_rating`。
- [x] 修改 `backend/app/api/v1/routes/question_routes.py` 的 `_format_question()`：返回 `created_by=q.created_by`、`creator_name=q.creator.name if q.creator else None`、`star_rating=q.star_rating`，并把 `is_owner` 改为 `q.created_by == current_user_id`。
- [x] 重跑同一测试，预期通过。

### 任务 2：统一新增、编辑、导入的题干哈希

**目标：** 不改变现有查重策略，但不能让修改题干或 Excel 导入绕过 `stem_hash`。

- [x] 在 `backend/tests/test_question_import_skip.py` 增加一行导入场景：数据库已有带 `stem_hash` 的题目，导入同题干但不同选项/答案的数据，断言 `skip_count=1` 且不新增记录。
- [x] 在 `backend/tests/test_public_question_contribution.py` 增加编辑场景：创建两题后，把第二题题干改为第一题题干，断言接口返回 `400`；再把一题改成新题干，断言保存后的 `stem_hash` 等于 `_compute_stem_hash(新题干)`。
- [x] 运行这两个测试文件，预期导入或编辑断言失败。
- [x] 在 `backend/app/services/question_service.py` 中复用现有 `_compute_stem_hash()`：
  - `update_question()` 在落库前计算更新后题干的 hash，查询除自身外的同 hash 题目并抛出当前中文重复提示；成功后写回 `q.stem_hash`。
  - `import_questions_from_excel()` 在完整指纹查重前计算题干 hash；若已有同 hash 题目，按当前导入跳过格式写入 `skips`；创建 `Question` 时写入 `stem_hash` 和默认 `star_rating=3`。
- [x] 重跑两个测试文件，预期通过；`test_question_duplicate_candidates.py` 不修改。

### 任务 3：教师端显示并维护添加人和星级

**目标：** 教师能在共享列表识别题目来源，新增或编辑时选择 1-5 星，且不能误点编辑其他教师的题。

- [x] 新建 `frontend/tests/teacher-question-bank-static.test.mjs`：断言 `Question` 类型含 `creator_name`、`star_rating`、`is_owner`；列表存在“添加人”“星级”列；编辑表单使用 `<el-rate>` 且最大值为 5；编辑禁用条件使用 `row.is_owner === false`。
- [x] 运行 `node .\\tests\\teacher-question-bank-static.test.mjs`，预期星级控件和列表列断言失败。
- [x] 修改 `frontend/src/api/question.ts`：`Question` 增加 `creator_name?: string | null`，并将 `is_owner` 的注释改为“题目创建人是否为当前教师”。
- [x] 修改 `frontend/src/views/teacher/TeacherQuestions.vue`：
  - 在课程列后加入“添加人”列，显示 `row.creator_name || row.created_by || '-'`。
  - 加入“星级”列，使用禁用的 `el-rate` 展示 `row.star_rating`。
  - 在新增/编辑弹窗的解析字段前加入 `el-rate v-model="form.star_rating" :max="5" show-score`，标签为“题目星级”。
  - 保留现有 `payload.star_rating`，不新增独立保存接口。
- [x] 重跑静态测试并执行 `npm run type-check`，预期通过。

### 任务 4：回归、文档与部署记录

- [x] 运行后端受影响测试：`backend/.venv/Scripts/python.exe -m pytest tests/test_public_question_contribution.py tests/test_question_import_skip.py tests/test_question_duplicate_candidates.py -q`。
- [x] 运行前端检查：`node .\\tests\\teacher-question-bank-static.test.mjs`、`npm run build`。
- [ ] 手工验收教师端：共享列表显示添加人和 1-5 星；新增题可选择星级；其他教师题目显示禁用编辑；Excel 导入同题干被跳过；同题干不同答案的旧指纹单测仍保持原行为。
- [x] 更新 `docs/superpowers/project-map.md` 的修改记录，写明共享题库展示字段、导入/编辑 hash 一致性和部署影响。

## 验收标准

1. 不同教师课程入口读取同一套题；每题显示添加人和星级。
2. 手工新增、编辑题干、Excel 导入均不能绕过现有同题干 hash 拦截。
3. 星级只能是 1-5，默认 3；新建、编辑、刷新列表后数值一致。
4. 其他教师创建的题不能在当前教师 UI 中编辑，后端仍拒绝越权更新。
5. 既有完整指纹单测不改、不删，题干查重策略不扩展为新算法。
6. 不引入数据库迁移、接口路径变化或学生端答题行为变化。

## 服务器部署影响

- 需要：拉取代码、重启后端服务、重新构建并部署前端。
- 不需要：数据库迁移、环境变量调整、Nginx 调整。
