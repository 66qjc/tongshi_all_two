# P1 书架卡片动效实施计划

> P0 公开学习馆已完成并部署。本计划聚焦 P1 第一阶段：LearnView 课程卡片的"书本展开"视觉升级。

## 一、目标

把 `/learn` 页面的课程卡片从平面信息卡改为有"书本感"的交互卡片：
- 卡片外观像一本竖立的书，有封面质感
- hover 时封面轻微翻开，露出内侧课程摘要
- 点击后进入课程详情（行为不变，仅视觉增强）
- 移动端降级为平面卡片 + 轻微阴影提升

## 二、范围

### 做

1. LearnView.vue 课程卡片改为"书本"样式（封面 + hover 翻开）
2. 资料条卡片加入轻微书架感（书脊色带 + 阴影）
3. 保留现有所有数据流、搜索、进度条、游客/学生双模式逻辑不变
4. 响应式适配（桌面 2 列书架 → 平板 1 列 → 移动端平面降级）
5. 不改动后端任何代码
6. 不改动 CourseDetailView.vue 阅读页
7. 不改动首页 HeroSection.vue（校徽和图标保持不变）

### 不做

1. 不做三栏书站式阅读页（那是 P1 第二阶段）
2. 不改数据库结构
3. 不改路由或权限
4. 不引入新的 CSS 框架或动画库
5. 不重做资料条布局（只加视觉增强）

## 三、设计方案

### 3.1 书本卡片结构

每张课程卡片由两层 DOM 组成：

```
.course-card (perspective 容器)
  .book-wrapper (3D 翻转容器)
    .book-cover (封面层 — 始终可见)
      .cover-spine (左侧书脊色带)
      .cover-title (课程名)
      .cover-meta (课时数 · 资料数)
      .cover-badge (公开学习标签)
    .book-inner (内页层 — hover 时露出)
      .inner-summary (课程简介/描述)
      .inner-progress (进度条，仅登录学生)
      .inner-action (开始学习/继续学习按钮)
```

### 3.2 动效参数

| 属性 | 值 | 说明 |
|------|-----|------|
| 翻转方式 | Y 轴旋转，`transform-origin: left center` | 模拟从左向右翻开 |
| hover 翻转角度 | `rotateY(-18deg)` | 轻微翻开，不翻到底 |
| 过渡时间 | `400ms cubic-bezier(0.4, 0, 0.2, 1)` | 柔和缓出 |
| 封面阴影 | hover 时增加 `box-shadow: 8px 4px 20px rgba(0,0,0,0.15)` | 翻开后投射阴影 |
| 书脊宽度 | `6px`，使用课程主题色 | 视觉锚点，增强书籍感 |
| perspective | `800px` 设在 `.course-card` 上 | 3D 空间深度 |

### 3.3 封面内容布局

```
┌──────────────────────────────┐
│▎ 公开学习                     │  ← 书脊 + badge
│▎                              │
│▎  AI 基础与思维               │  ← 课程名（衬线字体）
│▎                              │
│▎  12 课时 · 8 份资料         │  ← 元信息
│▎                              │
│▎  ████████░░  67%            │  ← 进度条（仅登录学生）
│▎                              │
│▎  [开始学习]                  │  ← 按钮
└──────────────────────────────┘
```

hover 时封面左侧翘起，露出右侧内页的课程简介：

```
┌────────┬─────────────────────┐
│▎       │ AI 基础与思维        │
│▎(封面) │                     │
│▎ 翘起  │ 本课程介绍 AI 发展史、│
│▎      │ 大模型原理和日常应用..│
│▎      │                     │
│▎      │ [继续学习 →]         │
└────────┴─────────────────────┘
```

### 3.4 资料条书架感

资料小卡片左侧添加 `4px` 书脊色带（PDF 用紫色，视频用蓝色），增加 `box-shadow` 深度，hover 时 `translateX(2px)` 轻微位移。

### 3.5 响应式降级

| 断点 | 行为 |
|------|------|
| `> 900px` | 2 列书架，完整 3D 翻转 |
| `768-900px` | 1 列书架，保留 3D 翻转 |
| `< 768px` | 1 列平面卡片，取消 3D（改为 `translateY(-2px)` + 阴影提升） |

### 3.6 无障碍

- 卡片的 `role="button"` + `tabindex="0"` + `@keydown.enter` 保持键盘可访问
- `prefers-reduced-motion` 媒体查询下禁用 3D 翻转，降级为平面阴影
- 封面和内页文本颜色保持 WCAG AA 对比度

## 四、实施任务

### Task 1：课程卡片 DOM 重构 + 书本 CSS

**修改文件：** `frontend/src/views/LearnView.vue`

**改动内容：**
- 重构 `.course-card` 模板：从单层 `<div>` 改为 `.book-wrapper > .book-cover + .book-inner` 双层结构
- 封面层放置：书脊色带、课程名、课时/资料计数、公开学习标签、进度条（条件渲染）、行动按钮
- 内页层放置：课程描述（截断 3 行）、行动按钮（重复，hover 时可见）
- 新增 CSS：`perspective`、`transform-style: preserve-3d`、`backface-visibility`、书脊渐变、hover 翻转
- 调整 `.course-grid` 的 `gap` 和 `.course-card` 的 `min-height` 适配新结构

**不改：** script 部分的数据流、搜索、进度加载、路由跳转逻辑全部保持原样。

### Task 2：资料条书架感增强

**修改文件：** `frontend/src/views/LearnView.vue`

**改动内容：**
- `.material-mini-card` 左侧添加 `::before` 伪元素作为书脊色带（4px 宽，根据 type 取色）
- 增加 `box-shadow: 2px 2px 8px rgba(0,0,0,0.06)` 基础阴影
- hover 时 `transform: translateX(2px)` + 阴影加深

### Task 3：响应式和无障碍适配

**修改文件：** `frontend/src/views/LearnView.vue`

**改动内容：**
- `@media (max-width: 768px)` 中：取消 3D 翻转（`transform: none !important`），改为平面 `translateY(-2px)` + 阴影
- `@media (prefers-reduced-motion: reduce)` 中：禁用所有 transition 和 3D 变换
- 确保卡片可键盘聚焦和回车触发

### Task 4：构建验证

- `npm run build` 通过
- 浏览器手动检查：桌面端 hover 翻开效果、移动端降级效果、游客/学生双模式

## 五、涉及文件清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `frontend/src/views/LearnView.vue` | 修改 | 卡片 DOM 重构 + 书本 CSS + 资料条增强 + 响应式 |

只改一个文件，不动后端、不动路由、不动其他页面。

## 六、验收标准

1. 桌面端 `/learn` 课程卡片呈现书本封面外观，有左侧书脊色带
2. hover 时封面沿左侧向左翻开约 18°，露出内页课程简介，过渡动画流畅
3. 点击卡片正常跳转到课程详情页（行为与 P0 一致）
4. 公开学习标签、进度条（登录学生）、搜索功能均正常
5. 资料条小卡片有书脊色带和轻微阴影
6. 移动端（< 768px）卡片为平面样式，无 3D 翻转
7. `prefers-reduced-motion` 下无动画
8. `npm run build` 通过
9. 首页 `/` 校徽和图标保持不变
10. 游客模式和登录学生模式均可正常使用

## 七、服务器部署影响

- 不需要后端改动
- 需要重新构建并部署前端（仅 LearnView.vue 改动）
- 不需要数据库迁移
- 不需要修改环境变量或 Nginx 配置
