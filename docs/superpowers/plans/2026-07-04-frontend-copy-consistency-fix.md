# 前端长文案一致性修复实施计划

## 目标

修复前端长文案审计中确认的高风险问题，让教师端、学生/公开端、管理端和通用资料组件在术语、业务后果说明和下一步动作上保持一致。

## 范围

### 本轮做

1. 教师端统一“作业 / 题目 / 资料 / 公共课程源 / 课程副本”等文案。
2. 学生和公开端统一“公开学习馆 / 学习资料 / 作业 / 自由练习”等文案。
3. 管理端修复密码重置驳回原因未传参的问题，并澄清公共课程同步删除范围。
4. 通用资料组件统一“资料预览”和“在新窗口打开”等操作文案。
5. 新增静态回归测试，防止内部迁移说明、错误口径和关键术语回归。
6. 更新项目修改记录，明确服务器部署影响。

### 本轮不做

1. 不调整数据库结构。
2. 不新增后端接口，不改变接口路径和响应结构。
3. 不重构权限逻辑、课程同步逻辑或资料预览生成流程。
4. 不重做页面视觉风格，只改与审计结果直接相关的文案和一个已存在接口的参数传递。

## 涉及文件

- `frontend/src/views/teacher/TeacherDashboard.vue`
- `frontend/src/views/teacher/TeacherAnnouncements.vue`
- `frontend/src/views/teacher/TeacherCourses.vue`
- `frontend/src/views/teacher/TeacherCourseDetail.vue`
- `frontend/src/views/teacher/TeacherMaterials.vue`
- `frontend/src/views/teacher/TeacherQuestions.vue`
- `frontend/src/views/teacher/TeacherReviews.vue`
- `frontend/src/views/teacher/TeacherStudents.vue`
- `frontend/src/views/teacher/TeacherTaskReport.vue`
- `frontend/src/views/admin/AdminPasswordReset.vue`
- `frontend/src/views/admin/AdminPublicCourses.vue`
- `frontend/src/views/admin/AdminShowcase.vue`
- `frontend/src/components/home/HeroSection.vue`
- `frontend/src/components/home/ModuleShowcase.vue`
- `frontend/src/components/home/StatsSection.vue`
- `frontend/src/components/AppFooter.vue`
- `frontend/src/views/LearnView.vue`
- `frontend/src/views/CourseDetailView.vue`
- `frontend/src/views/PracticeAssignments.vue`
- `frontend/src/views/PracticeQuizView.vue`
- `frontend/src/views/ProfileView.vue`
- `frontend/src/views/CreateView.vue`
- `frontend/src/components/common/MaterialRichCard.vue`
- `frontend/src/components/common/MaterialPreviewDialog.vue`
- `frontend/src/components/common/PdfPreviewDialog.vue`
- `frontend/src/api/http.ts`
- `frontend/tests/copy-consistency-static.test.mjs`
- `docs/superpowers/project-map.md`

## 验收标准

1. 新增的 `frontend/tests/copy-consistency-static.test.mjs` 先在当前代码下失败，失败原因指向审计出的文案或行为不一致。
2. 修复后 `node ./tests/copy-consistency-static.test.mjs` 通过。
3. 现有相关静态测试继续通过：`public-learning-static.test.mjs`、`practice-quiz-flow-static.test.mjs`。
4. `npm run build-only` 通过。
5. 修改记录写明服务器部署影响：需要重新构建并部署前端静态资源；不需要后端重启、数据库迁移、环境变量或 Nginx 配置调整。

## 风险

1. 文案替换可能触发既有静态测试中旧字符串断言失败。
   - 处理：同步更新测试断言为新的统一术语。
2. 管理端驳回原因传参会改变实际日志记录内容。
   - 处理：接口已经支持 `reason` 字段，本轮只让前端承诺与既有接口行为一致，不改变接口结构。
3. API 错误提示策略调整可能改变部分页面 Toast 数量。
   - 处理：本轮优先只收敛未知校验错误文案，避免扩大请求行为变化。
