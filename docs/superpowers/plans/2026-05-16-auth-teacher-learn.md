# 认证系统 + 教师端 + 学习模块增强 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 AI 通识课平台添加登录注册、教师端 4 个管理页面、学习模块视频/PDF 内容展示

**Architecture:** Pinia 管理认证状态，路由守卫控制访问权限，教师端使用嵌套路由布局，学习模块新增内容页

**Tech Stack:** Vue 3 + TypeScript + Element Plus + Pinia + vue-pdf-embed

---

## 文件变更总览

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 新增 | `src/stores/auth.ts` | 认证状态管理 |
| 新增 | `src/views/LoginView.vue` | 登录页 |
| 新增 | `src/views/RegisterView.vue` | 注册页 |
| 新增 | `src/views/teacher/TeacherLayout.vue` | 教师端布局 |
| 新增 | `src/views/teacher/TeacherDashboard.vue` | 教师概览 |
| 新增 | `src/views/teacher/TeacherMaterials.vue` | 资料管理 |
| 新增 | `src/views/teacher/TeacherQuestions.vue` | 题库管理 |
| 新增 | `src/views/teacher/TeacherStudents.vue` | 学生数据 |
| 新增 | `src/views/teacher/TeacherReviews.vue` | 作品审核 |
| 新增 | `src/views/ChapterView.vue` | 章节内容页 |
| 新增 | `src/views/content/VideoPlayer.vue` | 视频播放器 |
| 新增 | `src/views/content/PdfViewer.vue` | PDF 阅读器 |
| 修改 | `src/router/index.ts` | 新路由 + 守卫 |
| 修改 | `src/components/AppHeader.vue` | 登录/用户状态 |
| 修改 | `src/views/LearnView.vue` | 按钮跳转 + 内容统计 |

---

### Task 1: Pinia Auth Store

**Files:** Create `src/stores/auth.ts`

- [ ] 创建 auth store，使用 Pinia setup 语法（同 counter.ts 模式）
- [ ] 定义 User 接口、mock 账号数据、login/register/logout actions
- [ ] localStorage 持久化

### Task 2: LoginView

**Files:** Create `src/views/LoginView.vue`

- [ ] 左侧品牌 + 右侧表单布局
- [ ] el-form 表单：学号/工号 + 密码 + 登录按钮
- [ ] 调用 authStore.login，成功后按角色跳转

### Task 3: RegisterView

**Files:** Create `src/views/RegisterView.vue`

- [ ] 同布局风格
- [ ] 表单：学号/工号、姓名、密码、确认密码、角色选择、专业（学生必填）
- [ ] 调用 authStore.register，成功后自动登录跳转

### Task 4: Router + Auth Guards

**Files:** Modify `src/router/index.ts`

- [ ] 添加 login、register、teacher 子路由、learn/:chapterId 路由
- [ ] beforeEach 守卫：白名单 + 登录检查 + 教师角色检查

### Task 5: AppHeader Auth Integration

**Files:** Modify `src/components/AppHeader.vue`

- [ ] 未登录：显示"登录"按钮
- [ ] 学生登录：显示姓名 + 教师入口（如是教师）+ 退出按钮
- [ ] 教师登录：显示"教师工作台"入口

### Task 6-11: Teacher Pages

- [ ] TeacherLayout（sidebar + router-view）
- [ ] TeacherDashboard（4 统计卡片 + 快捷入口）
- [ ] TeacherMaterials（章节资料列表 + 上传弹窗）
- [ ] TeacherQuestions（题目列表 + 筛选 + 新增弹窗）
- [ ] TeacherStudents（学生表格 + 搜索）
- [ ] TeacherReviews（作品列表 + drawer 详情 + 审核操作）

### Task 12-15: Learn Module Enhancement

- [ ] VideoPlayer 组件（原生 video + 自定义控件）
- [ ] PdfViewer 组件（vue-pdf-embed）
- [ ] ChapterView（左侧目录 + 右侧内容区）
- [ ] LearnView 修改（按钮跳转 + 内容统计标签）

### Task 16: Build Verification

- [ ] `npm install vue-pdf-embed`
- [ ] `npm run build` 通过
