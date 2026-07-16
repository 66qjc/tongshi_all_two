# 2026-07-14 「学」页教程站形态改造

## 目标

把「学」从书架式公开学习馆，改成**游客友好的教程站入口 + 紧凑资料目录阅读**，对齐已确认 Demo：

- 原型：`docs/superpowers/demos/2026-07-14-learn-tutorial-site-demo.html`
- 产品边界不变：仍是 AI 通识**教学平台**的公开学习前台，内容继续由管理员/教师后台运营（DB → API），**不**改成静态菜鸟站 / MkDocs / 硬编码教程内容。

## 背景与决策

### 用户确认的方向

1. **不要书架**：去掉书脊、翻开书、馆藏统计等表达。
2. **要教程站入口**：一门公开课 = 一门教程；卡片网格 + 搜索 +「开始学习」。
3. **资料目录要像教程站目录**：阶段是分组头，资料是缩进条目；行高要紧凑（参考菜鸟目录密度，不复制品牌/绿站皮肤）。
4. **右侧当前资料元信息块不需要**：去掉类型/大小/所属（及同类字段）的键值列表。
5. **入口不需要**：门数/课时数/资料数总览、底部「最新资料」条。

### 与既有规格关系

- 书站规格 `docs/superpowers/specs/2026-07-01-public-learning-booksite-design.md` 中的 **P0 游客公开、P1 三栏阅读壳** 继续有效。
- 本计划**修正 P1 中「书架」视觉路线**：入口改为教程列表；课程内仍保留左目录 / 中阅读 / 右辅助，但文案与资料目录层级按教程站调整。
- 不走规格方案 C（新建知识库/文章模型）。

## 范围

### 做

| 序号 | 内容 | 主要文件 |
|---|---|---|
| 1 | `/learn` 入口改为教程卡片网格 + 搜索 | `frontend/src/views/LearnView.vue` |
| 2 | 接通公开课 `keyword` 搜索与空结果 | `LearnView.vue` + 已有 `frontend/src/api/publicLearning.ts` |
| 3 | 资料 Tab 目录：阶段/资料紧凑分层 + 阶段折叠 | `frontend/src/views/CourseDetailView.vue` |
| 4 | 右侧「当前资料」去掉类型/大小/页数/时长等 facts | `CourseDetailView.vue` |
| 5 | 文案去书架隐喻：公开教程 / 教程目录 / 学习资料 等 | `LearnView.vue`、`CourseDetailView.vue`（仅本任务直接相关文案） |
| 6 | 文档同步：计划状态、project-map 简记、部署影响 | 本文件、`docs/superpowers/project-map.md` |

### 明确不做

- 不改后端数据模型、不新增图书/文章表
- 不改公开学习 API 权限语义（仅复用已有 `keyword`）
- 不重做教师端/管理员端；不改 10 项教师导航
- 不上在线 Try 编辑器、不引入 Next/MDX/MkDocs
- 不复制菜鸟源码/品牌/绿站整站皮肤
- 不改课时正文 `LessonReader` 的内容渲染逻辑（本轮不强制做代码块高亮/复制）
- 不做学习路径（路径卡）配置
- 不在本轮改首页其它模块（除非入口文案与「学」强绑定且已存在乱码/错误指向）

## 目标形态（以 Demo 为准）

### A. `/learn` 教程列表

```
顶区：学校名 + 深度 AI 通识 + 标题「公开教程」+ 一句说明
工具区：全部教程 + 搜索框
主体：教程卡片网格
  - 公开/已加入 徽章（若适用）
  - 课程名
  - 简介最多 2 行
  - 课时数 · 资料数（卡片内元信息保留，页级总览统计不要）
  - 主按钮：开始学习 / 继续学习
不要：门数/课时/资料总览三格、最新资料条、书脊/翻开书
```

行为：

- 游客：拉公开课列表；可搜索；点卡片进 `/learn/course/:id`（有课时进目录，无课时可进资料 Tab——沿用现有合理默认）。
- 登录学生：公开课 + 已加入课合并展示逻辑可保留；进度与「继续学习」保留。
- 搜索：调用 `getPublicCourses(keyword)`；空结果中文提示（可清空搜索）。
- 已加入私有课是否参与 keyword：优先 **公开课走 API keyword**；已加入列表可在前端按名称二次过滤，避免扩大后端范围。

### B. `/learn/course/:id` 学习资料 Tab

左侧资料目录：

```
阶段头（单行 ~32px）：▾  [阶段 N]  阶段名 …… 数量
资料行（单行 ~30px，缩进）：[PDF] 标题 …… 243 KB
选中：左侧主色条 + 浅底；阶段头浅底分组，不与资料同权大卡片
```

- 阶段默认展开；点击阶段头折叠/展开（Demo 已有，建议落地）。
- 点击阶段头**不要**等同于选中第一份资料（避免与点资料混淆）；仅折叠或无操作二选一，推荐折叠。
- 资料点击 = 切换中间 `MaterialInlineReader`。
- 组间距紧凑；不要多行堆叠类型/标题/日期把行高撑到 80px+。
- 日期可放 `title` 悬停，行内优先标题 + 大小（或类型 + 标题）。

右侧引导栏：

- 保留：当前资料标题、摘要/说明、上一份/下一份、游客学习提示（若已有）。
- **删除**：`guide-facts` 中类型/大小/页数/时长等键值列表（与 Demo 一致）。
- 「打开原资料」若现网已有且有用可保留；不在本轮新增强依赖。

Tab 文案建议：

- `课程目录` → `教程目录`（或保留「课程目录」若担心影响已登录学生习惯；**优先与 Demo 一致用「教程目录」**）
- `学习资料库` → `学习资料`
- Hero kicker：可用「公开教程阅读」替代过重「书/馆」表述

课时 Tab：

- 继续使用现有 `CourseToc` + `LessonReader` + `PrevNextNav` 三栏壳。
- 本轮不做课时目录大改；仅必要时同步文案。

## 分步任务

### Task 1：`LearnView` 去掉书架，改为教程网格

1. 阅读并理解现有 `loadCourses` / `mergeCourses` / 进度逻辑，**保留数据流**，替换 template 与样式。
2. 删除或停用：书脊轨、翻开书面板、页级统计 facts（若存在）、任何「选一本书」类文案。
3. 新 UI：
   - hero 文案对齐 Demo（公开教程、游客可读、登录可存进度）
   - 搜索框（本地 state + 触发加载）
   - 卡片网格；主按钮 `开始学习` / `继续学习`（沿用 `courseActionText` 思路）
4. 空态：无课、搜索无结果、加载中，全中文。
5. 响应式：桌面 3 列，窄屏 1 列；不引入新 UI 库。

### Task 2：搜索接通

1. `getPublicCourses(keyword?: string)` 已支持；`LearnView` 传入 keyword。
2. 本轮使用“回车或搜索按钮”触发搜索，不增加防抖计时器；清空按钮恢复全部教程，避免请求时序和加载状态变复杂。
3. 登录学生合并已加入课时：keyword 下对 enrolled 列表前端过滤课程名。
4. 不改后端，除非联调发现公开列表 keyword 与软删过滤不一致（应已在既有服务中处理）。

### Task 3：`CourseDetailView` 资料目录紧凑分层

1. 调整 `materialSections` 对应 template：
   - 阶段：`stage-head` 结构（徽章 + 标题 + 数量 + chevron）
   - 资料：`material-link` 单行
2. 使用 `ref<Set<string>>` 保存折叠状态，键使用 `materialSections` 的 `section.key`；未分类组同样处理。
3. 重写相关 CSS：行高、缩进、左色条、active；删除「阶段与资料同为全宽多行块」的旧观感。
4. 阶段头点击只切换折叠，不 `selectMaterial(section.materials[0])`。

### Task 4：右侧引导栏精简

1. 移除 `guide-facts`（类型/大小/页数/时长）整块。
2. 保留标题与 summary、上下份导航、必要提示。
3. 检查中间阅读区标题/meta 是否已足够（可保留中栏类型 pill + 简单 meta，与 Demo 中栏一致；不以右侧 facts 重复）。

### Task 5：文案与回归

1. 本任务触及的中文文案无乱码、无英文占位。
2. 游客 / 登录学生两条路径点验：
   - `/learn` 列表与搜索
   - 进入公开课资料 Tab：目录层级、折叠、选中、预览仍可用
   - 课时 Tab 未回归破坏
3. 静态回归必须运行：`node .\\tests\\public-learning-static.test.mjs`、`node .\\tests\\copy-consistency-static.test.mjs`、`node .\\tests\\course-detail-layout-static.test.mjs`。
4. 前端构建必须运行：`npm run build`（在 `frontend` 下）。

### Task 6：文档

1. 实施完成后更新本计划「实施结果」小节。
2. `docs/superpowers/project-map.md` 增加本轮变更摘要与部署影响。
3. 如 `AGENTS.md` 当前优先级需反映「学页教程站 UI」完成态，再补一条（避免写入临时调试过程）。

## 验收标准

1. **入口**：打开 `/learn`，3 秒内可理解为「教程列表」；无书脊/翻开书；无页级「X 门教程 / X 课时 / X 资料」总览；无最新资料条。
2. **搜索**：输入关键字后列表过滤；无结果有中文提示。
3. **卡片**：展示名称、简介、课时/资料数、开始或继续学习；点击进入课程页。
4. **资料目录**：不看文字也能区分阶段头与资料行；阶段行与资料行视觉高度接近单行目录（远小于现状 ~80px 大块）。
5. **选中态**：当前资料左侧有明确主色指示；预览区随选择切换。
6. **右侧**：无类型/大小/所属（页数/时长）facts 列表。
7. **权限**：游客仍可读公开内容；登录学生进度能力不回退。
8. **构建**：`frontend` 下 `npm run build` 通过。
9. **无无关重构**：不改教师/管理端业务页，不改删除/权限后端。

## 风险与注意

| 风险 | 处理 |
|---|---|
| 书架相关大量 scoped CSS 残留 | 删除无用样式，避免死代码；勿全局污染 |
| 搜索只滤公开课、已加入课仍全量 | 前端对 enrolled 同步滤名称；文案不承诺「全站统一搜索后端」 |
| 阶段折叠状态刷新丢失 | 可接受（本轮不要求 localStorage）；状态仅保存在当前页面会话 |
| 移动端三栏 | 沿用现有 `CourseDetailView` 响应式；目录过长可滚动 |
| 与书站规格文档表述冲突 | 实施后在规格或 project-map 注明「入口由书架改为教程网格」 |
| 软删资料目录过滤 | 这是既有读路径一致性问题，不在本纯前端 UI 计划内；单独纳入阶段 D 软删除收口，不能借本任务修改权限语义 |

## 服务器部署影响（实施后预期）

- **需要**：拉代码、**重新构建并部署前端**
- **不需要**：数据库迁移、改后端环境变量、改 Nginx（若仅前端 UI）
- **说明**：若未改后端，可不重启后端；若联调中顺带改了 API，再补重启说明

## 参考

- Demo：`docs/superpowers/demos/2026-07-14-learn-tutorial-site-demo.html`
- 书站规格：`docs/superpowers/specs/2026-07-01-public-learning-booksite-design.md`
- 公开 API：`backend/app/api/v1/routes/public_learning_routes.py`（`keyword` 已有）
- 前端 API：`frontend/src/api/publicLearning.ts`
- 页面：`frontend/src/views/LearnView.vue`、`frontend/src/views/CourseDetailView.vue`

## 实施结果

- 状态：**已实施**（2026-07-14）
- 主要改动：
  - `frontend/src/views/LearnView.vue`：教程卡片网格 + 搜索
  - `frontend/src/views/CourseDetailView.vue`：资料目录紧凑分层/折叠、去掉 `guide-facts`、相关文案
  - `frontend/src/router/index.ts`：`/learn` 标题改为「学 · 公开教程」
  - 静态测试：`public-learning-static.test.mjs`、`copy-consistency-static.test.mjs`
- 验证：
  - `frontend` 下 `npm run build` 通过
  - `node ./tests/public-learning-static.test.mjs` 通过
  - `node ./tests/copy-consistency-static.test.mjs` 通过
  - `node ./tests/course-detail-layout-static.test.mjs` 通过
- 服务器部署影响：需要拉代码并**重新构建、部署前端**；不需要后端重启、数据库迁移、改 Nginx 或环境变量
