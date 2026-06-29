# 人工智能通识全站共享题库与重复题限制设计

> 日期：2026-06-28  
> 阶段：设计稿  
> 相关现状：题库已支持公共课程同步与题库贡献记录，但当前共享边界仍围绕“公共课程副本”；本次需求把共享边界提升为“全站统一题库”。

## 背景

当前网站只做“人工智能通识”这一门课，A/B/C 只是不同形式。题库不能再按课程私有化理解，任何老师在任一课程里新增或导入题目，其他课程都应立即可见。

同时需要新增一个硬限制：如果别的老师提交了相同题目，要自动拦截，避免共享题库被重复题堆满。

现有的 `QuestionContributionLog` 继续保留，用于管理员追踪“谁在什么时间、什么课程下、新增或导入了多少题”。

## 目标

1. 形成全站唯一共享题库。
2. 老师在任意课程新增/导入题目时，自动写入共享题库。
3. 重复题自动拦截。
4. 管理员继续查看题库贡献日志，日志快照不受后续课程改名影响。
5. 不改教师端主要入口，不改资料、阶段、作品、作业等其他课程内容的边界。

## 非目标

1. 不做题目审核流。
2. 不做题目适用 A/B/C 的标签分流。
3. 不调整资料、阶段、作品、作业的共享规则。
4. 不重做题库搜索和分页 UI。

## 设计

### 1. 共享根课程

新增课程级共享题库指针 `question_bank_root_course_id`，用于指向当前课程所属的共享题库根课程。

- 共享根课程本身该字段为空。
- 其他课程都指向同一个根课程。
- 业务上通过 `resolve_question_bank_course(db, course)` 统一解析：
  - 如果课程有根指针，返回根课程。
  - 如果没有根指针，返回课程自身。

题目读写、列表查询、课程题目数统计，都只认这个解析结果，不再按原始 `course_id` 分散存储。

### 2. 写入路径

`create_question`、`import_questions_from_excel`、管理员端公共题库新增/导入，统一走同一条逻辑：

1. 先校验当前操作者对课程的访问权限。
2. 解析到共享根课程。
3. 生成题目标识 `fingerprint`。
4. 在共享根课程维度查重。
5. 未重复才插入，且 `Question.course_id` 固定写共享根课程 id。
6. 成功后写入贡献日志。

管理员公共题库的 `mirror_public_course_content` 不再复制题目到每个教师副本，只保留资料和阶段的同步逻辑。题库共享改为“单根写入 + 统一解析读取”。

### 3. 读取路径

`list_questions`、`get_course_questions`、课程详情里的题目数、管理员公共课程题库页、题库贡献页，都改成先解析到共享根课程，再按根课程 id 查询。

这样 A/B/C 三种课程在题库视角下看到的是同一套题。

前端当前用于显示“公共/私有”的字段可以继续保留，但后端在共享题库中的题目上统一返回“共享/公共”语义，避免页面改动过大。

### 4. 重复题判定

重复判定口径固定为：

- `type`
- 规范化后的 `stem`
- 规范化后的 `options`
- 规范化后的 `answer`

规范化规则：

- `stem` 去首尾空格，并把连续空白压成一个空格。
- `options` 逐项去首尾空格，保留原顺序。
- `answer`
  - 单选/填空：去首尾空格并压缩连续空白。
  - 多选：按大写字母集合规范化，再排序后比较。

`tags`、`explanation` 不参与判重。

判重结果：

- 单条新增：直接返回 400，提示“题库中已存在相同题目”。
- 批量导入：该行跳过，记录到 `skips`，不算失败行。

### 5. 贡献记录

`QuestionContributionLog` 保持现有结构不变，仍然记录：

- `public_course_id`
- `public_course_name`
- `operator_id`
- `operator_name`
- `operator_role`
- `action`
- `question_count`
- `created_at`

这里的 `public_course_*` 实际上记录的是共享根课程的快照。课程后续改名，不影响历史记录展示。

`question_count` 只统计成功写入的题目数，不统计跳过或失败行。

### 6. 兼容与迁移

`schema_compat` 需要给 `courses` 表补 `question_bank_root_course_id` 和索引，旧库可自动兼容建表。

迁移时采用“单根归并”策略：

1. 选定现有共享根课程，优先使用现有公共课程。
2. 其他课程统一指向该根课程。
3. 现有题目统一迁入共享根课程。
4. 如历史库里存在重复题，按同一 fingerprint 只保留最早的一条，其余跳过。

`source_course_id` 继续只服务于资料/阶段同步，不再承担题库共享语义。

## 涉及模块

- `backend/app/models/entities.py`
- `backend/app/db/schema_compat.py`
- `backend/app/services/question_service.py`
- `backend/app/services/admin_public_course_service.py`
- `backend/app/services/public_course_sync_service.py`
- `backend/app/services/question_contribution_service.py`
- `backend/app/api/v1/routes/question_routes.py`
- `backend/app/api/v1/routes/admin_public_course_routes.py`
- `frontend/src/views/teacher/TeacherQuestions.vue`
- `frontend/src/views/admin/AdminPublicCourses.vue`
- `frontend/src/api/adminPublicCourse.ts`
- `backend/tests/test_public_question_contribution.py`
- `backend/tests/test_schema_compat.py`

## 测试

1. 任一课程新增同一题目，第二次提交会被拦截。
2. 任一课程批量导入相同题目，重复行会跳过并给出原因。
3. A/B/C 任一课程下新增的题目，在其他课程里都能看到。
4. 管理员查看题库贡献记录时，能看到正确的课程快照、操作者和题数。
5. 旧库能自动补齐 `question_bank_root_course_id`，且不影响现有数据读取。
6. 前端执行 `cd frontend && npm run build`。

## 风险与约束

- 共享题库后，任何一个课程上的题目修改都会影响所有课程，这是预期行为。
- 共享根课程不能随意删除，否则所有课程题库都会失效；实现时应默认阻止删除根课程，或要求先迁移根。
- 如果历史库里已经有多套题目，迁移时必须先去重再归并，避免把旧重复直接搬进根课程。

## 服务器部署影响

- 设计阶段不需要服务器修改。
- 正式实施后需要数据库兼容迁移、后端重启、前端重新构建。
- 如果当前线上库已经存在旧的课程和题目数据，建议先完成迁移/补齐字段，再切换到新版本。
