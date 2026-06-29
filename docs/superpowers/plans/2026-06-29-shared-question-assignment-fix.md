# 2026-06-29 全站共享题库作业链路修复计划

## 要解决的问题

全站共享题库已经允许任意课程入口读取同一套题，但作业发布、作业取题、答题提交和课程练习统计仍保留“题目必须属于当前课程”的旧校验，导致教师端看得到共享题却发不出作业，学生端也可能无法完成共享题作业或自由练习。

## 涉及范围

- 后端作业发布：`backend/app/services/announcement_service.py`
- 后端作业取题与完成：`backend/app/services/task_service.py`
- 后端答题提交与统计：`backend/app/services/quiz_service.py`
- 后端回归测试：`backend/tests/test_assignment_practice_flow.py`
- 项目修改记录：`backend/docs/项目修改记录.md`

## 不做内容

- 不改数据库结构。
- 不调整教师端题库选择器 UI 结构。
- 不改变课程、班级、作业本身的权限边界。
- 不把题目复制回课程副本。

## 实施步骤

1. 先新增失败测试，覆盖教师用其他课程归属的共享题发布作业、学生获取作业题、提交作业答案、自由练习提交共享题、课程练习统计统计共享题作答。
2. 修改发布作业校验：题目只需全部存在于全站题库，不再要求 `Question.course_id == announcement.course_id`。
3. 修改作业取题校验：按 `question_ids` 全站读取，并按公告保存顺序返回。
4. 修改答题提交校验：带 `announcement_id` 时只校验题目在该公告 `question_ids` 中；自由练习时允许已加入任一课程的学生提交全站共享题。
5. 修改课程练习统计：与课程卡片题目数量一致，按全站题库统计当前学生在该课程入口下的自由练习表现。
6. 运行受影响后端测试和前端构建，确认无回归。

## 验收方式

- 新增共享题库作业链路测试先失败，修复后通过。
- `python -m pytest backend/tests/test_assignment_practice_flow.py backend/tests/test_public_question_contribution.py -q` 通过。
- `npm run type-check` 和 `npm run build-only` 通过。

## 服务器部署影响

本计划落地后需要服务器拉取代码并重启后端服务；如果前端没有业务代码改动，则不需要重新构建前端。不需要数据库迁移，不需要修改环境变量或 Nginx 配置。
