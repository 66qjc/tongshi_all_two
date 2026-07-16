# PDF 资料阅读体验改进实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 在课程资料 PDF 阅读器中用接近底部自动加载后续页面，删除正文下方重复的“打开原资料”区域，同时保留右侧资料操作入口。

**架构：** 继续使用现有 `vue-pdf-embed` 和 `visiblePdfPageCount` 分批渲染机制；新增底部哨兵元素与 `IntersectionObserver`，哨兵进入视口时把页数增加 2。观察器只在 PDF、仍有后续页面且没有正在加载时工作，资料切换或组件卸载时释放，避免重复监听和跨资料触发。

**技术栈：** Vue 3 `<script setup lang="ts">`、`vue-pdf-embed`、IntersectionObserver、Node 静态测试、Vite。

---

### Task 1：自动加载 PDF 后续页面

**文件：**
- 修改：`frontend/src/components/learn/MaterialInlineReader.vue`
- 修改：`frontend/tests/public-learning-static.test.mjs`

- [x] **Step 1：增加失败静态断言**

断言组件包含 `IntersectionObserver`、底部观察哨兵、按 2 页增加可见页数的逻辑，并继续保留全部页面停止加载的条件。

- [x] **Step 2：运行测试确认当前实现失败**

运行：`node frontend/tests/public-learning-static.test.mjs`

预期：新增自动加载断言失败，因为当前组件只有“加载更多页面”按钮。

- [x] **Step 3：实现最小自动加载逻辑**

新增 `pdfLoadSentinel` ref、`pdfObserver` 变量和 `setupPdfObserver/stopPdfObserver`；观察器触发时调用现有页数递增逻辑，每次增加 2 页。观察器回调必须检查 PDF 类型、`pdfStatus !== 'error'`、`!fileLoading`、`!pdfRenderingMore` 和 `hasMorePdfPages`，避免重复触发。

- [x] **Step 4：替换按钮为状态与哨兵**

保留“正在加载后续页面”文本状态，在 PDF 内容末尾渲染带 `ref="pdfLoadSentinel"` 的空哨兵；移除“加载更多页面”按钮。资料切换时重置页数并重新挂载观察器，组件卸载时断开观察器。

- [x] **Step 5：运行静态测试确认通过**

运行：`node frontend/tests/public-learning-static.test.mjs`

预期：所有断言通过。

### Task 2：移除重复底部打开入口

**文件：**
- 修改：`frontend/src/components/learn/MaterialInlineReader.vue`
- 修改：`frontend/tests/public-learning-static.test.mjs`

- [x] **Step 1：增加底部入口移除断言**

断言组件不再包含 `.pdf-open-row`，但 PDF 失败降级区域和链接资料自身的“打开原资料”入口仍保留。

- [x] **Step 2：删除底部重复区域并清理样式**

删除 PDF section 下方的 `.pdf-open-row` 模板和对应 CSS；不修改右侧 `CourseDetailView.vue` 的“打开原资料”链接。

- [x] **Step 3：运行前端验证**

运行：`node frontend/tests/public-learning-static.test.mjs`、`npm run type-check --prefix frontend`、`npm run build --prefix frontend`。

预期：静态测试、类型检查和构建全部通过；仅允许出现既有大 chunk 警告。

### 验收与部署边界

- 本轮只修改本地前端组件和静态回归测试，不同步服务器、不重启后端、不修改数据库或 Nginx。
- 浏览器验收：打开课程资料，滚动接近 PDF 底部自动追加 2 页；全部页面后不再追加；底部重复入口消失；右侧入口仍可用。

### 实施结果（2026-07-14）

- `MaterialInlineReader.vue` 使用 `IntersectionObserver` 在距离底部 400px 时自动追加 2 页，并在资料切换/组件卸载时断开观察器。
- 已移除正文下方重复的 `.pdf-open-row`，右侧“打开原资料”入口保持不变。
- 静态测试、类型检查和生产构建通过；本轮没有服务器部署影响。
