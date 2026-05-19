# 登录系统 + 教师端 + 学习模块增强 设计文档

## Context

AI 通识课平台前端已完成两轮深化（页面创建 + Bug 修复/交互补完），现有 13 个视图页面全部就绪。但平台缺少：
1. 用户认证系统（登录/注册/角色区分）
2. 教师端页面（上传资料、管理题库、审核作品、查看学生数据）
3. 学习模块的内容展示能力（目前只有章节卡片，无实际视频/PDF 内容页）

本次实现范围：**仅前端，mock 数据，无后端 API**。目标是搭建完整的页面框架和交互流程，为后续后端接入做准备。

---

## 一、认证系统

### 1.1 Pinia Auth Store

**文件：** `frontend/src/stores/auth.ts`

```typescript
interface User {
  id: string           // 学号或工号
  name: string
  role: 'student' | 'teacher'
  major?: string
}

// 状态
user: User | null
token: string | null

// Actions
login(id: string, password: string) → boolean
register(id: string, name: string, password: string, role: 'student' | 'teacher', major?: string) → boolean
logout()
```

**Mock 账号：**

| 学号/工号 | 密码 | 姓名 | 角色 |
|-----------|------|------|------|
| 2025001 | 123456 | 张同学 | student |
| T001 | 123456 | 王老师 | teacher |

**持久化：** `localStorage` 存储 user 和 token，页面刷新后自动恢复登录状态。

### 1.2 登录页

**文件：** `frontend/src/views/LoginView.vue`
**路由：** `/login`

- 布局：左侧品牌区域（logo + 标语 + 4 模块图标）+ 右侧登录表单
- 表单字段：学号/工号（el-input）、密码（el-input password）、登录按钮
- Element Plus 表单验证：非空 + 长度校验
- 登录成功 → 根据 role 跳转首页或教师端
- 底部链接：没有账号？去注册

### 1.3 注册页

**文件：** `frontend/src/views/RegisterView.vue`
**路由：** `/register`

- 同布局风格
- 表单字段：学号/工号、姓名、密码、确认密码、角色选择（el-radio-group: 学生/教师）、学生需填专业
- 注册成功 → 自动登录 → 跳转首页
- 底部链接：已有账号？去登录

### 1.4 路由守卫

**修改文件：** `frontend/src/router/index.ts`

```typescript
router.beforeEach((to) => {
  // 设置 title（已有逻辑）
  document.title = ...

  const authStore = useAuthStore()

  // 白名单页面
  const publicPaths = ['/', '/login', '/register', '/about', '/privacy', '/contact']

  if (!publicPaths.includes(to.path) && !authStore.isLoggedIn) {
    return '/login'
  }

  // 教师端路由守卫
  if (to.path.startsWith('/teacher') && authStore.user?.role !== 'teacher') {
    return '/'
  }
})
```

---

## 二、教师端

### 2.1 路由结构

```
/teacher            → TeacherDashboard
/teacher/materials  → TeacherMaterials
/teacher/questions  → TeacherQuestions
/teacher/students   → TeacherStudents
/teacher/reviews    → TeacherReviews
```

所有路由使用 `TeacherLayout` 作为父级包裹（嵌套路由 `<RouterView />`）。

### 2.2 TeacherLayout

**文件：** `frontend/src/views/teacher/TeacherLayout.vue`

- 顶部 header：平台 logo + "教师工作台" 标题 + 教师姓名 + "返回学生端" 按钮
- 左侧 sidebar：4 个导航项（概览、资料管理、题库管理、学生数据、作品审核），当前路由高亮
- 右侧内容区：`<router-view />`
- 配色使用 `--color-primary` 为主色，与学生端四模块区分开

### 2.3 概览页 Dashboard

**文件：** `frontend/src/views/teacher/TeacherDashboard.vue`
**路由：** `/teacher`

- 4 个统计卡片：总学生数、已发布章节、待审作品、本周练习量
- 快捷入口按钮：上传资料、管理题库

### 2.4 资料管理 Materials

**文件：** `frontend/src/views/teacher/TeacherMaterials.vue`
**路由：** `/teacher/materials`

- 按章节分组展示资料列表（表格：文件名、类型、大小、上传时间、操作）
- 上传按钮 → el-dialog 弹窗（选择章节、文件类型、文件上传区、标题输入）
- 支持删除操作
- Mock 数据：每个章节 2-3 个资料（视频/PDF 混合）

### 2.5 题库管理 Questions

**文件：** `frontend/src/views/teacher/TeacherQuestions.vue`
**路由：** `/teacher/questions`

- 顶部筛选栏：章节下拉、题型下拉（选择题/填空题）
- 题目列表表格：题号、题干预览、题型、章节、操作（编辑/删除）
- 新增题目按钮 → el-dialog 弹窗（章节选择、题型选择、题干输入、选项输入【选择题】、答案、解析）
- Mock 数据复用 PracticeQuizView 中的题目结构

### 2.6 学生数据 Students

**文件：** `frontend/src/views/teacher/TeacherStudents.vue`
**路由：** `/teacher/students`

- 学生列表表格：学号、姓名、专业、学习进度、练习题数、正确率
- 顶部搜索框（按学号/姓名过滤）
- Mock 数据：10 个学生

### 2.7 作品审核 Reviews

**文件：** `frontend/src/views/teacher/TeacherReviews.vue`
**路由：** `/teacher/reviews`

- 作品列表（卡片或表格）：作品名、作者、提交时间、状态（待审/通过/驳回）
- 点击作品 → el-drawer 侧边栏展示详情（描述、标签、视频链接）
- 底部操作按钮：通过 / 驳回（需填写理由）
- Mock 数据：6 个作品，部分待审

---

## 三、学习模块增强

### 3.1 新增路由

```
/learn/:chapterId → ChapterView（章节内容页）
```

### 3.2 ChapterView

**文件：** `frontend/src/views/ChapterView.vue`
**路由：** `/learn/:chapterId`

**布局：**
- 顶部：返回按钮 + 章节编号 + 章节标题
- 主体分两栏：
  - 左侧（280px 固定宽度）：内容目录列表
  - 右侧（flex）：视频播放器或 PDF 阅读器

**内容目录列表：**
- 每个条目显示：类型图标（视频▶ / 文档📄）、标题
- 当前选中项高亮（左侧色条 + 背景色）
- 底部显示"已完成 x/y"进度

**Mock 章节内容数据结构：**
```typescript
interface ChapterContent {
  id: number
  chapterId: number
  type: 'video' | 'pdf'
  title: string
  url: string          // mock URL
  duration?: string    // 视频时长，如 "12:30"
  pages?: number       // PDF 页数
}
```

### 3.3 VideoPlayer 组件

**文件：** `frontend/src/views/content/VideoPlayer.vue`

- 使用原生 `<video>` 元素
- 自定义控制栏覆盖在视频底部（半透明渐变背景）：
  - 播放/暂停按钮
  - 进度条（可拖拽）
  - 时间显示（当前 / 总时长）
  - 倍速选择（0.5x / 0.75x / 1x / 1.25x / 1.5x / 2x）
  - 音量滑块
  - 全屏按钮
- 无视频源时显示占位提示："教师暂未上传视频"

### 3.4 PdfViewer 组件

**文件：** `frontend/src/views/content/PdfViewer.vue`

- 使用 `vue-pdf-embed` 库（`npm install vue-pdf-embed`）
- 控制栏：上一页 / 页码输入 / 下一页 / 缩放（- / + / 适配宽度）
- 无 PDF 源时显示占位提示："教师暂未上传文档"
- 备选方案：如 vue-pdf-embed 兼容性不佳，回退到 `<iframe>` + 浏览器内置 PDF 查看器

### 3.5 LearnView 改造

**修改文件：** `frontend/src/views/LearnView.vue`

- "开始学习"按钮跳转 `/learn/:chapterId`（之前改为跳转练习页，需改回）
- 章节卡片增加内容统计标签："3 个视频 · 2 份文档"
- 章节数据增加 `contentCount` 字段

---

## 四、文件变更总览

| 操作 | 文件路径 |
|------|----------|
| 新增 | `src/stores/auth.ts` |
| 新增 | `src/views/LoginView.vue` |
| 新增 | `src/views/RegisterView.vue` |
| 新增 | `src/views/teacher/TeacherLayout.vue` |
| 新增 | `src/views/teacher/TeacherDashboard.vue` |
| 新增 | `src/views/teacher/TeacherMaterials.vue` |
| 新增 | `src/views/teacher/TeacherQuestions.vue` |
| 新增 | `src/views/teacher/TeacherStudents.vue` |
| 新增 | `src/views/teacher/TeacherReviews.vue` |
| 新增 | `src/views/ChapterView.vue` |
| 新增 | `src/views/content/VideoPlayer.vue` |
| 新增 | `src/views/content/PdfViewer.vue` |
| 修改 | `src/router/index.ts` — 添加新路由 + 守卫 |
| 修改 | `src/views/LearnView.vue` — 按钮跳转 + 内容统计 |
| 修改 | `src/stores/index.ts` — 可能需调整（如存在） |
| 依赖 | `npm install vue-pdf-embed` |

---

## 五、页面流程

```
首页 (/)
  ├─ 未登录 → 点击任意模块 → /login
  │   ├─ 登录(学生) → 返回原目标页
  │   └─ 登录(教师) → /teacher
  │
  ├─ 学生已登录
  │   ├─ 探 (/learn) → 章节卡片 → /learn/:id → 内容页（视频/PDF）
  │   ├─ 练 (/practice) → 章节卡片 → /practice/quiz/:id
  │   ├─ 造 (/create) → 作品列表 → 作品详情 / 提交作品
  │   ├─ 行 (/act) → 行动页 → 成长档案
  │   └─ 头部显示姓名 + 退出按钮
  │
  └─ 教师已登录
      ├─ /teacher → 概览
      ├─ /teacher/materials → 资料管理
      ├─ /teacher/questions → 题库管理
      ├─ /teacher/students → 学生数据
      ├─ /teacher/reviews → 作品审核
      └─ 头部显示"返回学生端"（可查看学生视角）
```

---

## 六、验证步骤

```bash
cd d:/Users/ASUS/Desktop/tongshi/frontend
npm install vue-pdf-embed
npm run build
```

手动验证清单：
1. 未登录状态访问 `/learn` → 跳转到 `/login`
2. 用学生账号登录 → 跳转首页，可访问所有学生页面
3. 用教师账号登录 → 跳转 `/teacher`，可访问所有教师页面
4. 教师访问 `/create` → 正常访问（教师可切换到学生视角）
5. 学生访问 `/teacher` → 重定向到首页
6. `/learn/1` → 显示章节内容列表，点击可切换视频/PDF
7. 退出登录 → 清除状态，回到首页
