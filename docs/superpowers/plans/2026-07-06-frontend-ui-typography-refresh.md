# 全站前端 UI 与文字排版优化实施计划

## 目标

在不调整后端接口、数据库、权限边界和服务器配置的前提下，保留本轮非教师端的前端排版优化：

- 首页、公开页、登录注册页和学生端页面使用统一的中文标题、正文行高、行宽和数字排版规则。
- 修复 Vue Transition 和 Element Plus 相关本地 warning。
- 教师端页面按用户反馈回退，不再纳入本轮 UI 大改成果。

## 范围

### 本轮保留

- `frontend/src/assets/main.css` 的排版 token、`text-wrap` 和等宽数字工具。
- 首页公共外壳和首页模块的文字排版优化。
- 公开活动、关于、联系、隐私、登录、注册、修改密码、404 页面的标题和说明排版优化。
- 学生端学习、答题、练习、作品、个人、消息页面的文字排版优化。
- `App.vue` 页面切换单根节点修复。
- `main.ts` Element Plus 单选组件别名注册。
- `AdminPublicCourses.vue` 的空值 option 和 tag type warning 收口。

### 本轮回退

- `frontend/src/views/teacher/` 下教师端页面恢复到教师端 UI 大改前状态。
- 删除教师端重设计专用计划和静态测试，不再要求 `teacher-ui-redesign-static.test.mjs`。

### 本轮不做

- 不修改后端接口、数据库结构、认证、权限、课程/作业/资料/作品业务逻辑。
- 不部署服务器，不重启服务器服务，不写入服务器数据。
- 不新增 UI 框架、状态管理方案或图标体系。
- 不继续改教师端视觉方案；后续如果要再做教师端，需要另起小范围设计和验收。

## 验证

在 `frontend` 目录执行：

```bash
node ./tests/frontend-typography-static.test.mjs
node ./tests/vue-console-warning-static.test.mjs
node ./tests/home-first-stage-static.test.mjs
node ./tests/home-course-preview-removal-static.test.mjs
node ./tests/public-learning-static.test.mjs
node ./tests/practice-assignments-color-static.test.mjs
node ./tests/practice-quiz-flow-static.test.mjs
node ./tests/teacher-workbench-only-static.test.mjs
node ./tests/teacher-courses-search-static.test.mjs
npm run build
```

浏览器本地生产预览至少检查：

- `/`
- `/learn`
- `/practice`
- `/create`
- `/portfolio`
- `/teacher`

## 服务器部署影响

本次按用户要求不写入服务器，只做本地生产环境测试。真正上线时若保留本分支其他前端改动，需要服务器拉取前端代码并重新构建、部署前端静态资源；不需要后端重启，不需要数据库迁移，不需要修改环境变量或 Nginx 配置。
