# AI 通识教育课程平台前端

本目录是 Vue 3 + TypeScript + Vite + Element Plus 前端工程，包含学生端、教师端和管理员端页面。

## 主要页面

| 路径 | 页面 | 说明 |
|------|------|------|
| `/learn` | `src/views/LearnView.vue` | 学生端课程列表 |
| `/learn/course/:courseId` | `src/views/CourseDetailView.vue` | 学生端课程详情页 |
| `/practice` | `src/views/PracticeView.vue` | 学生端在线练习入口 |
| `/practice/assignments` | `src/views/PracticeAssignments.vue` | 学生端作业练习列表 |
| `/practice/quiz/:courseId` | `src/views/PracticeQuizView.vue` | 学生端答题页 |
| `/inbox` | `src/views/InboxView.vue` | 学生端消息通知（任务/公告） |
| `/student/notifications` | `src/views/InboxView.vue` | 学生端通知中心（与 `/inbox` 共用页面） |
| `/create` | `src/views/CreateView.vue` | 学生端作品广场 |
| `/create/upload` | `src/views/ProjectUploadView.vue` | 学生端提交/编辑作品 |
| `/create/project/:id` | `src/views/ProjectDetailView.vue` | 作品详情页 |
| `/act` | `src/views/ActView.vue` | 课程活动时间线 |
| `/portfolio` | `src/views/PortfolioView.vue` | 成长档案（雷达图） |
| `/profile` | `src/views/ProfileView.vue` | 个人中心（错题本 + 收藏作品 + 密保设置） |
| `/change-password` | `src/views/ChangePasswordView.vue` | 修改密码（首次登录强制） |
| `/teacher` | `src/views/teacher/TeacherDashboard.vue` | 教师端工作台概览 |
| `/teacher/materials` | `src/views/teacher/TeacherMaterials.vue` | 教师端资料管理 |
| `/teacher/courses` | `src/views/teacher/TeacherCourses.vue` | 教师端课程管理 |
| `/teacher/questions` | `src/views/teacher/TeacherQuestions.vue` | 教师端题库管理 |
| `/teacher/students` | `src/views/teacher/TeacherStudents.vue` | 教师端学生成绩 |
| `/teacher/classes` | `src/views/teacher/TeacherClasses.vue` | 教师端班级管理 |
| `/teacher/publish` | `src/views/teacher/TeacherAnnouncements.vue` | 教师端发布题目 |
| `/teacher/task-report` | `src/views/teacher/TeacherTaskReport.vue` | 教师端任务完成报告 |
| `/teacher/reviews` | `src/views/teacher/TeacherReviews.vue` | 教师端作品审核 |
| `/teacher/student-admin` | `src/views/teacher/TeacherStudentAdmin.vue` | 教师端学生管理（导入/密保审批） |
| `/admin/teachers` | `src/views/admin/AdminTeachers.vue` | 管理员端教师账号管理 |
| `/admin/public-courses` | `src/views/admin/AdminPublicCourses.vue` | 管理员端公共课程管理 |
| `/admin/password-reset` | `src/views/admin/AdminPasswordReset.vue` | 管理员端密码重置审批 |
| `/admin/showcase` | `src/views/admin/AdminShowcase.vue` | 管理员端悟页面内容管理 |

## API 封装

| 文件 | 说明 |
|------|------|
| `src/api/auth.ts` | 登录、注册、获取当前用户、修改密码、忘记密码、密保问题 |
| `src/api/course.ts` | 课程列表、课程详情、课程增删改 |
| `src/api/material.ts` | 学习资料列表、上传后登记、删除（含 file_id） |
| `src/api/question.ts` | 题库 CRUD + Excel 导入 |
| `src/api/quiz.ts` | 答题提交、历史、统计 |
| `src/api/project.ts` | 作品广场、提交、点赞、我的作品（含 file_id 字段） |
| `src/api/upload.ts` | 通用文件上传（返回 file_id + content_type + storage_provider） |
| `src/api/teacher.ts` | 教师工作台、学生数据、作品审核、批量下载 |
| `src/api/class.ts` | 班级管理 + Excel 批量导入学生 |
| `src/api/announcement.ts` | 公告/任务 CRUD + 已读/完成追踪 |
| `src/api/portfolio.ts` | 成长档案数据 |
| `src/api/admin.ts` | 管理员：教师账号 CRUD + 批量导入 + 密码重置 |
| `src/api/adminPublicCourse.ts` | 管理员：公共课程管理 + 内容管理 |
| `src/api/profile.ts` | 个人中心：错题本 + 收藏作品 + 密保设置 |
| `src/api/notification.ts` | 学生通知列表、未读计数、标记已读 |
| `src/api/progress.ts` | 课时进度、课程进度汇总、教师课程分析分页 |
| `src/api/showcase.ts` | 悟页面图文内容：管理员增删改查 + 公开只读 |

课程体系的前端关系：

- 教师端在”课程管理”页维护课程，在”资料管理”页上传资料。
- 学生端先进入课程列表，再进入课程详情查看资料。
- 资料、题目、学习进度全部直接挂在课程下，不使用独立章节。
- 课时进度只有真实进入课时时增加访问次数；普通心跳和离页补报只累计时长。
- 无视频课时由学生点击“完成本课”确认完成；教师端课程分析学生明细由后端分页。

## Recommended IDE Setup

[VS Code](https://code.visualstudio.com/) + [Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur).

## Recommended Browser Setup

- Chromium-based browsers (Chrome, Edge, Brave, etc.):
  - [Vue.js devtools](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd)
  - [Turn on Custom Object Formatter in Chrome DevTools](http://bit.ly/object-formatters)
- Firefox:
  - [Vue.js devtools](https://addons.mozilla.org/en-US/firefox/addon/vue-js-devtools/)
  - [Turn on Custom Object Formatter in Firefox DevTools](https://fxdx.dev/firefox-devtools-custom-object-formatters/)

## Type Support for `.vue` Imports in TS

TypeScript cannot handle type information for `.vue` imports by default, so we replace the `tsc` CLI with `vue-tsc` for type checking. In editors, we need [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) to make the TypeScript language service aware of `.vue` types.

## Customize configuration

See [Vite Configuration Reference](https://vite.dev/config/).

## Project Setup

```sh
npm install
```

### Compile and Hot-Reload for Development

```sh
npm run dev
```

### Type-Check, Compile and Minify for Production

```sh
npm run build
```

### Production Environment

同域部署并由 Nginx 反代 `/api` 时，无需配置 `VITE_API_BASE`。

前后端分域部署时，复制 `.env.production.example` 为 `.env.production`，并设置：

```env
VITE_API_BASE=https://api.example.com
```
