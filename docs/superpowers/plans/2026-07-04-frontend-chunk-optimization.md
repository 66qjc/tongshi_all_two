# 前端 Chunk 体积优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 降低前端生产构建中的大 chunk，优先让教师课程详情页、成长档案页和入口包不再承担当前页面不需要的重依赖成本。

**架构：** 本轮采用“重依赖延迟加载”而不是重写业务页面。`LessonEditor` 只在教师打开课时弹窗时加载，ECharts 被隔离到独立异步图表组件，Element Plus 图标从全量注册收窄到实际使用的白名单。Element Plus 组件全量按需注册影响面更大，留到第二阶段单独处理。

**技术栈：** Vue 3 `<script setup lang="ts">`、Vite、Element Plus、wangeditor、ECharts、静态 Node 断言测试。

---

## 范围

### 本轮做

1. 新增 `frontend/tests/chunk-optimization-static.test.mjs`，防止重依赖再次被页面静态引入。
2. 修改 `frontend/src/views/teacher/TeacherCourseDetail.vue`，把 `LessonEditor` 改为 `defineAsyncComponent` 动态加载。
3. 新增 `frontend/src/components/portfolio/PortfolioRadarChart.vue`，把 ECharts 和 `vue-echarts` 依赖隔离到独立异步组件。
4. 修改 `frontend/src/views/PortfolioView.vue`，只异步加载 `PortfolioRadarChart`。
5. 修改 `frontend/src/main.ts`，只注册当前模板实际使用的 Element Plus 图标。
6. 更新 `docs/superpowers/project-map.md`，记录服务器部署影响。

### 本轮不做

1. 不改后端接口。
2. 不改数据库。
3. 不改教师端上传、课时保存、资料预览业务逻辑。
4. 不做 Element Plus 组件级全量按需注册，因为它会影响所有 `<el-*>` 模板解析，需要单独验证。
5. 不引入新的 PDF 或视频渲染库。

## 验收标准

1. `frontend/tests/chunk-optimization-static.test.mjs` 先能在当前代码下失败，失败原因指向静态重依赖。
2. 优化后 `node ./tests/chunk-optimization-static.test.mjs` 通过。
3. 优化后 `npm run build-only` 通过。
4. 构建产物中 `TeacherCourseDetail` 主 chunk 明显下降，不再包含 wangeditor 主体。
5. 构建产物中 `PortfolioView` 主 chunk 明显下降，ECharts 进入独立异步 chunk。
6. 构建产物中入口 `index` chunk 因图标全量注册移除而下降。
7. 修改记录写明：服务器需要重新构建并部署前端静态资源，不需要后端重启和数据库迁移。

## 任务

### Task 1：静态回归测试

**Files:**
- Create: `frontend/tests/chunk-optimization-static.test.mjs`

- [ ] **Step 1：写失败测试**

新增测试读取 `TeacherCourseDetail.vue`、`PortfolioView.vue` 和 `main.ts`，断言：

```js
assert.doesNotMatch(teacherCourseDetail, /import\s+LessonEditor\s+from/, '教师课程详情页不能静态引入富文本编辑器')
assert.match(teacherCourseDetail, /defineAsyncComponent\(\s*\(\)\s*=>\s*import\(['"]@\/components\/lesson\/LessonEditor\.vue['"]\)/, '教师课程详情页应动态加载富文本编辑器')
assert.doesNotMatch(portfolioView, /from ['"]vue-echarts['"]/, '成长档案页不能静态引入 vue-echarts')
assert.doesNotMatch(portfolioView, /from ['"]echarts\//, '成长档案页不能静态引入 ECharts 模块')
assert.match(portfolioView, /defineAsyncComponent\(\s*\(\)\s*=>\s*import\(['"]@\/components\/portfolio\/PortfolioRadarChart\.vue['"]\)/, '成长档案页应动态加载图表组件')
assert.doesNotMatch(main, /import\s+\*\s+as\s+ElementPlusIconsVue/, '入口不能全量导入 Element Plus 图标')
assert.match(main, /import\s+\{\s*Loading\s*\}\s+from ['"]@element-plus\/icons-vue['"]/, '入口只注册实际使用的 Loading 图标')
```

- [ ] **Step 2：运行测试确认失败**

Run:

```bash
cd frontend
node ./tests/chunk-optimization-static.test.mjs
```

Expected: FAIL，至少提示 `TeacherCourseDetail.vue` 静态引入 `LessonEditor`。

### Task 2：教师课程详情页懒加载富文本编辑器

**Files:**
- Modify: `frontend/src/views/teacher/TeacherCourseDetail.vue`

- [ ] **Step 1：改脚本导入**

把 Vue 导入改为：

```ts
import { computed, defineAsyncComponent, onMounted, reactive, ref } from 'vue'
```

删除：

```ts
import LessonEditor from '@/components/lesson/LessonEditor.vue'
```

新增：

```ts
const LessonEditor = defineAsyncComponent(() => import('@/components/lesson/LessonEditor.vue'))

type LessonEditorExpose = {
  insertMaterialPlaceholder: (materialId: number, materialType: 'video' | 'pdf') => void
}
```

把 ref 类型改为：

```ts
const lessonEditorRef = ref<LessonEditorExpose | null>(null)
```

- [ ] **Step 2：保持模板不变**

模板继续使用：

```vue
<LessonEditor ref="lessonEditorRef" v-model="lessonForm.content" @insert-material="openMaterialSelector" />
```

Vue 会在弹窗渲染到该组件时加载异步组件。

### Task 3：成长档案图表异步隔离

**Files:**
- Create: `frontend/src/components/portfolio/PortfolioRadarChart.vue`
- Modify: `frontend/src/views/PortfolioView.vue`

- [ ] **Step 1：新增图表组件**

创建 `PortfolioRadarChart.vue`：

```vue
<script setup lang="ts">
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { RadarChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([RadarChart, TooltipComponent, LegendComponent, CanvasRenderer])

defineProps<{
  option: Record<string, unknown>
}>()
</script>

<template>
  <v-chart :option="option" class="portfolio-radar-chart" autoresize />
</template>

<style scoped>
.portfolio-radar-chart {
  width: 100%;
  height: 360px;
}
</style>
```

- [ ] **Step 2：修改 `PortfolioView.vue`**

删除 ECharts 相关静态导入和 `use(...)` 调用，改为：

```ts
import { ref, onMounted, defineAsyncComponent } from 'vue'

const PortfolioRadarChart = defineAsyncComponent(() => import('@/components/portfolio/PortfolioRadarChart.vue'))
```

模板改为：

```vue
<PortfolioRadarChart :option="radarOption" />
```

### Task 4：入口图标注册收窄

**Files:**
- Modify: `frontend/src/main.ts`

- [ ] **Step 1：删除全量图标导入**

删除：

```ts
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
```

新增：

```ts
import { Loading } from '@element-plus/icons-vue'
```

删除全量注册循环，改为：

```ts
app.component('Loading', Loading)
```

当前模板中只有 `ProfileView.vue` 直接使用 `<Loading />` 图标组件，因此先只注册该图标。

### Task 5：验证与记录

**Files:**
- Modify: `docs/superpowers/project-map.md`

- [ ] **Step 1：运行静态测试**

Run:

```bash
cd frontend
node ./tests/chunk-optimization-static.test.mjs
```

Expected: 输出 `chunk-optimization-static: 所有断言通过`。

- [ ] **Step 2：运行构建**

Run:

```bash
cd frontend
npm run build-only
```

Expected: 构建通过。允许仍存在超过 500 KB 的 chunk 警告，但需要记录本轮前后主要大 chunk 的变化。

- [ ] **Step 3：更新修改记录**

在 `docs/superpowers/project-map.md` 顶部修改记录新增：

```markdown
### 2026-07-04 前端 Chunk 体积第一阶段优化

- 问题：前端生产构建存在大 chunk，入口包、教师课程详情页和成长档案页分别承担了全量图标、富文本编辑器和图表库等当前页面不一定需要的成本。
- 优化：`TeacherCourseDetail.vue` 将 `LessonEditor` 改为异步组件；`PortfolioView.vue` 将 ECharts 隔离到 `PortfolioRadarChart.vue` 并异步加载；`main.ts` 将 Element Plus 图标从全量注册改为只注册当前使用的 `Loading`。
- 验证：新增 `frontend/tests/chunk-optimization-static.test.mjs`；执行 `node ./tests/chunk-optimization-static.test.mjs` 和 `npm run build-only`。
- 服务器部署影响：需要服务器拉取前端代码并重新构建、部署前端静态资源；不需要后端重启，不需要数据库迁移，不需要修改环境变量或 Nginx 配置。
```

## 风险

1. 富文本编辑器异步加载后，首次打开课时弹窗会多一次 chunk 请求。
   - 处理：只在真正进入课时编辑时付出该成本，符合首屏优化目标。
2. ECharts 拆成异步组件后，成长档案图表区域可能短暂空白。
   - 处理：这是可接受的延迟加载成本；如后续需要，可补充 loading skeleton。
3. 图标白名单过窄可能导致未搜索到的全局图标失效。
   - 处理：当前全库搜索只发现 `<Loading />` 直接依赖；如果后续新增图标，需要同步在 `main.ts` 注册。
