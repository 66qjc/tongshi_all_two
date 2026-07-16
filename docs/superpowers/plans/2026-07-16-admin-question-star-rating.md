# 管理员公共题库星级维护实施计划

## 目标

让管理员和题目创建教师维护共享题目的 1-5 星级，与教师端题库使用同一个 `Question.star_rating` 字段。

## 现状

- 教师端 `TeacherQuestions.vue` 已展示星级，并在新增、编辑弹窗中使用 `el-rate` 维护星级。
- `Question` 模型、通用题目 Schema 与教师端接口已具备 `star_rating`，默认值为 3，范围为 1-5。
- 管理员公共题库的 `_format_question()` 未返回星级；`AdminQuestionCreate`、`AdminQuestionUpdate` 与 `AdminQuestionPayload` 未声明星级；管理员页面列表和弹窗未显示该字段。
- 管理员已有新增、编辑共享题目的权限和接口，无需新建路由或调整数据库结构。

## 范围

1. 后端管理员公共题库接口返回 `star_rating`。
2. 管理员新增、编辑请求接受并校验 `star_rating` 为 1-5，未传时默认 3。
3. 管理员题库表格新增只读星级列；管理员可在新增、编辑弹窗中为任意活跃共享题目设置 5 星评分。
4. 教师端继续允许创建教师编辑自己题目的星级；非创建教师保持只读，不能绕过既有 `is_owner` 权限编辑。
5. 补充管理员接口与页面静态回归测试。
6. 更新项目修改记录，明确服务器需要重新构建前端和重启后端，但不需要数据库迁移。

## 不做

- 不修改教师端题库现有星级行为。
- 不改变题库共享归属、创建人、删除、批量删除、导入或贡献记录规则。
- 不新增星级筛选、排序、批量设置或数据库迁移；既有旧数据继续按模型默认值 3 星展示。
- 不实施管理员回收站前端 Task6。

## 实施步骤

1. 在 `backend/app/schemas/common.py` 为管理员题目创建/更新 Schema 增加 `star_rating`，使用 1-5 范围校验和默认值 3。
2. 在 `backend/app/api/v1/routes/admin_public_course_routes.py` 的题目格式化响应中返回星级；确认服务层创建和更新仅写入 Schema 已校验字段。
3. 在 `frontend/src/api/adminPublicCourse.ts` 的 `AdminQuestionPayload` 声明星级字段。
4. 在 `frontend/src/views/admin/AdminPublicCourses.vue` 的题库表格中加入星级列，新增/编辑表单加入 `el-rate`，并在打开、保存时正确回填与提交。
5. 核对教师端编辑接口继续受 `is_owner` 约束，确保星级与题干、答案等字段采用相同所有权边界。
6. 为管理员题库补充后端 API 断言和前端静态断言；运行受影响测试、`npm run type-check`、`npm run build`。
7. 更新 `backend/docs/项目修改记录.md` 与相关计划状态，随后执行 `graphify update .`。

## 验收

- 管理员题库列表每题显示 1-5 星，旧数据无星级值时显示 3 星。
- 管理员新增题目可设定星级，保存后列表与刷新后的接口值一致。
- 管理员编辑题目可修改星级，提交 0、6 或非整数时接口返回可理解的校验错误。
- 教师可编辑自己创建题目的星级；非创建教师不能通过界面或接口编辑其他教师题目的星级。
- 后端受影响测试、前端类型检查和构建通过；不提交环境文件、构建产物或 Task6 文件。

## 服务器部署影响

正式发布需要服务器拉取新的 `main`、重新构建并同步前端静态资源、重启 `tongshi-backend.service`。不需要数据库迁移、Nginx 或环境变量调整。
