# 课程资料页直读式文档站 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `/learn/course/:courseId?tab=materials` 从资料卡片流和弹窗预览，改为类似学习文档站的直读式资料页面：左侧按阶段选择资料，中间直接阅读当前 PDF/视频/链接，右侧只展示当前资料导读。

**Architecture:** 第一阶段只改前端，不改后端接口、数据库、上传流程、教师端或管理员端资料管理。核心实现集中在 `CourseDetailView.vue` 的资料 tab，保留现有课程目录 tab 和 `MaterialPreviewDialog` 作为其他页面备用能力。新增一个轻量组件承载当前资料阅读器，避免继续扩大 `CourseDetailView.vue`。

**Tech Stack:** Vue 3 `<script setup lang="ts">`、TypeScript、Vite、Element Plus、现有 `Material` 类型、现有公开资料文件 URL `getPublicMaterialFileUrl(material.id)`。

---

## 文件结构

- Modify: `frontend/tests/public-learning-static.test.mjs`
  - 增加资料页直读式结构断言。
  - 删除或替换旧的“资料页三栏卡片流”断言中与新目标冲突的部分。
- Create: `frontend/src/components/learn/MaterialInlineReader.vue`
  - 只负责当前资料的主阅读区。
  - 根据 `material.type` 渲染 PDF `<object>`、视频 `<video>`、链接落地页或空状态。
- Modify: `frontend/src/views/CourseDetailView.vue`
  - 增加 `activeMaterialId`、`activeMaterial`、`selectMaterial`、`defaultMaterial`、`activeMaterialIndex`、相邻资料计算和资料文件 URL 解析。
  - 增加资料 tab 的轻量实时刷新：页面可见且存在 `pending` / `processing` 预览状态时定时刷新课程资料数据，页面重新可见时立即刷新。
  - 将资料 tab 的中间卡片流改为 `MaterialInlineReader`。
  - 将左侧目录从“阶段跳转”改为“阶段 -> 资料选择”。
  - 将右侧统计/快速打开改为当前资料导读和上一篇/下一篇。
  - 保留 `MaterialPreviewDialog` 给课程正文 tab 的资料预览。
- Modify: `docs/superpowers/project-map.md`
  - 实施完成后追加修改记录和服务器部署影响。

不改：

- `backend/` 下任何文件。
- `frontend/src/api/publicLearning.ts`。
- `frontend/src/api/material.ts`。
- `frontend/src/components/common/MaterialPreviewDialog.vue`。
- `frontend/src/components/common/MaterialRichCard.vue`。
- 教师端、管理员端资料上传和管理页面。

## Task 1: 写直读式资料页静态回归测试

**Files:**

- Modify: `frontend/tests/public-learning-static.test.mjs`

- [ ] **Step 1: 替换旧资料页断言为直读式断言**

在现有 `CourseDetailView.vue` 断言附近，保留公开路由、公开 API、课程目录三栏、乱码检测等断言。把旧资料页只要求 `materials-booksite-layout`、`materials-sidebar`、`materials-reader`、`materials-rail`、`scrollToMaterialStage` 的断言，替换为以下断言：

```js
assert.match(detail, /activeMaterialId/, '学习资料页应维护当前选中的资料 ID')
assert.match(detail, /activeMaterial/, '学习资料页应根据当前资料 ID 计算当前阅读资料')
assert.match(detail, /defaultMaterial/, '学习资料页应有默认资料选择逻辑')
assert.match(detail, /selectMaterial/, '学习资料页左侧目录点击资料后应切换当前阅读资料')
assert.match(detail, /material-inline-reader/, '学习资料页中间区域应使用直读式资料阅读器')
assert.match(detail, /MaterialInlineReader/, 'CourseDetailView 应引入直读式资料阅读组件')
assert.match(detail, /material-doc-shell/, '学习资料页应使用文档站式资料阅读外壳')
assert.match(detail, /material-doc-sidebar/, '学习资料页应包含左侧阶段化资料目录')
assert.match(detail, /material-doc-main/, '学习资料页应包含中间当前资料阅读区')
assert.match(detail, /material-doc-guide/, '学习资料页应包含右侧当前资料导读')
assert.match(detail, /上一份资料/, '右侧导读应提供上一份资料入口')
assert.match(detail, /下一份资料/, '右侧导读应提供下一份资料入口')
assert.match(detail, /getPublicMaterialFileUrl/, '公开资料直读仍应复用公开资料文件接口')
assert.doesNotMatch(
  detail,
  /<main v-else class="materials-content">[\s\S]*<MaterialRichCard/,
  '学习资料页主流程不应继续以 MaterialRichCard 卡片流作为中间主体',
)
assert.doesNotMatch(
  detail,
  /<main v-else class="materials-content">[\s\S]*@click="previewMaterial\(material\)"/,
  '学习资料页主流程不应通过点击预览弹窗阅读资料',
)
```

继续在同一文件中读取新组件并增加断言：

```js
const inlineReader = read('src/components/learn/MaterialInlineReader.vue')

assert.match(inlineReader, /defineProps/, 'MaterialInlineReader 应声明 props')
assert.match(inlineReader, /material:\s*Material\s*\|\s*null/, 'MaterialInlineReader 应接收当前资料')
assert.match(inlineReader, /fileUrl:\s*string/, 'MaterialInlineReader 应接收当前资料文件 URL')
assert.match(inlineReader, /type === 'pdf'/, 'MaterialInlineReader 应处理 PDF 资料')
assert.match(inlineReader, /<object[\s\S]*type="application\/pdf"/, 'PDF 资料应在页面中间直接内嵌阅读')
assert.match(inlineReader, /浏览器无法直接显示 PDF/, 'PDF 内嵌失败时应有中文降级提示')
assert.match(inlineReader, /type === 'video'/, 'MaterialInlineReader 应处理视频资料')
assert.match(inlineReader, /<video[\s\S]*controls/, '视频资料应在页面中间直接播放')
assert.match(inlineReader, /type === 'link'/, 'MaterialInlineReader 应处理链接资料')
assert.match(inlineReader, /打开原资料/, '链接资料应提供打开入口')
assertNoMojibake('MaterialInlineReader.vue', inlineReader)
```

将 `inlineReader` 加入最后的乱码检查数组：

```js
['MaterialInlineReader.vue', inlineReader],
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
cd frontend
node .\tests\public-learning-static.test.mjs
```

Expected:

```text
AssertionError: 学习资料页应维护当前选中的资料 ID
```

如果失败点是找不到 `src/components/learn/MaterialInlineReader.vue`，也符合预期，因为组件还没有创建。

## Task 2: 新增 MaterialInlineReader 组件

**Files:**

- Create: `frontend/src/components/learn/MaterialInlineReader.vue`

- [ ] **Step 1: 创建组件骨架**

创建 `frontend/src/components/learn/MaterialInlineReader.vue`：

```vue
<script setup lang="ts">
import { computed } from 'vue'
import type { Material } from '@/api/material'

const props = defineProps<{
  material: Material | null
  fileUrl: string
}>()

const type = computed(() => props.material?.type)

const metaText = computed(() => {
  if (!props.material) return ''
  const parts: string[] = []
  if (props.material.type === 'pdf' && props.material.preview?.page_count) {
    parts.push(`${props.material.preview.page_count} 页`)
  }
  if (props.material.type === 'video' && props.material.preview?.duration_seconds) {
    const minutes = Math.max(1, Math.round(props.material.preview.duration_seconds / 60))
    parts.push(`${minutes} 分钟`)
  }
  if (props.material.size) parts.push(props.material.size)
  if (props.material.date) parts.push(props.material.date)
  return parts.join(' · ')
})
</script>

<template>
  <article class="material-inline-reader">
    <div v-if="!material" class="reader-empty">
      <h2>暂无可阅读资料</h2>
      <p>当前课程还没有配置 PDF、视频或链接资料。</p>
    </div>

    <template v-else>
      <header class="reader-head">
        <p class="reader-kicker">{{ material.type === 'pdf' ? 'PDF 资料' : material.type === 'video' ? '视频资料' : '外部链接' }}</p>
        <h2>{{ material.title }}</h2>
        <p v-if="metaText" class="reader-meta">{{ metaText }}</p>
      </header>

      <section v-if="type === 'pdf'" class="reader-frame pdf-frame">
        <object :data="fileUrl" type="application/pdf" class="pdf-object">
          <div class="reader-fallback">
            <h3>浏览器无法直接显示 PDF</h3>
            <p>可以使用下方按钮在新窗口打开原资料。</p>
            <a :href="fileUrl" target="_blank" rel="noopener" class="open-link">打开原资料</a>
          </div>
        </object>
      </section>

      <section v-else-if="type === 'video'" class="reader-frame video-frame">
        <video :src="fileUrl" controls preload="metadata" class="video-player" />
      </section>

      <section v-else class="reader-frame link-frame">
        <div class="link-panel">
          <h3>{{ material.title }}</h3>
          <p>{{ material.preview?.summary || '该资料为外部学习链接，请在新窗口打开阅读。' }}</p>
          <a :href="fileUrl || material.url" target="_blank" rel="noopener" class="open-link">打开原资料</a>
        </div>
      </section>
    </template>
  </article>
</template>
```

- [ ] **Step 2: 增加组件样式**

在同一个文件底部追加：

```vue
<style scoped>
.material-inline-reader {
  min-width: 0;
}

.reader-head {
  padding: 22px 26px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md) var(--radius-md) 0 0;
}

.reader-kicker {
  margin: 0 0 6px;
  color: var(--color-learn);
  font-size: 0.78rem;
  font-weight: 900;
}

.reader-head h2 {
  margin: 0;
  color: var(--color-text);
  font-size: 1.35rem;
  line-height: var(--leading-title);
  font-weight: 900;
  text-wrap: balance;
}

.reader-meta {
  margin: 8px 0 0;
  color: var(--color-text-muted);
  font-size: 0.86rem;
}

.reader-frame {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-top: 0;
  border-radius: 0 0 var(--radius-md) var(--radius-md);
}

.pdf-frame {
  min-height: 74vh;
}

.pdf-object,
.video-player {
  display: block;
  width: 100%;
  min-height: 74vh;
  border: 0;
  background: var(--color-bg-alt);
}

.video-player {
  height: auto;
  min-height: 420px;
}

.link-frame,
.reader-empty {
  padding: 42px;
}

.link-panel,
.reader-empty {
  color: var(--color-text-secondary);
  line-height: 1.8;
}

.link-panel h3,
.reader-empty h2,
.reader-fallback h3 {
  margin: 0 0 10px;
  color: var(--color-text);
  font-size: 1.1rem;
}

.reader-fallback {
  display: grid;
  place-items: center;
  min-height: 360px;
  padding: 32px;
  color: var(--color-text-secondary);
  text-align: center;
}

.open-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-top: 12px;
  padding: 9px 14px;
  color: var(--color-bg-card);
  background: var(--color-learn);
  border-radius: var(--radius-sm);
  font-weight: 800;
}

@media (max-width: 900px) {
  .reader-head {
    padding: 18px;
  }

  .reader-head h2 {
    font-size: 1.12rem;
  }

  .pdf-frame,
  .pdf-object {
    min-height: 70vh;
  }

  .link-frame,
  .reader-empty {
    padding: 24px;
  }
}
</style>
```

- [ ] **Step 3: 运行测试确认仍失败在 CourseDetailView**

Run:

```powershell
cd frontend
node .\tests\public-learning-static.test.mjs
```

Expected:

```text
AssertionError: 学习资料页应维护当前选中的资料 ID
```

新组件相关断言应不再是第一失败点。

## Task 3: 改造 CourseDetailView 资料状态和选择逻辑

**Files:**

- Modify: `frontend/src/views/CourseDetailView.vue`

- [ ] **Step 1: 引入 MaterialInlineReader**

在现有 import 附近增加：

```ts
import MaterialInlineReader from '@/components/learn/MaterialInlineReader.vue'
```

- [ ] **Step 2: 增加当前资料状态**

在 `selectedMaterial` 附近增加：

```ts
const activeMaterialId = ref<number | null>(null)
```

- [ ] **Step 3: 增加默认资料和当前资料计算**

在 `materialTypeStats` 附近增加：

```ts
const defaultMaterial = computed(() => {
  return (
    materials.value.find((material) => material.type === 'pdf') ||
    materials.value.find((material) => material.type === 'video') ||
    materials.value.find((material) => material.type === 'link') ||
    null
  )
})

const activeMaterial = computed(() => {
  if (!materials.value.length) return null
  return (
    materials.value.find((material) => material.id === activeMaterialId.value) ||
    defaultMaterial.value
  )
})

const activeMaterialIndex = computed(() => {
  if (!activeMaterial.value) return -1
  return materials.value.findIndex((material) => material.id === activeMaterial.value?.id)
})

const prevMaterial = computed(() => {
  const index = activeMaterialIndex.value
  return index > 0 ? materials.value[index - 1] : null
})

const nextMaterial = computed(() => {
  const index = activeMaterialIndex.value
  return index >= 0 && index < materials.value.length - 1 ? materials.value[index + 1] : null
})
```

- [ ] **Step 4: 增加当前资料 URL 计算**

在 `selectedMaterialPreviewUrl` 附近增加：

```ts
const activeMaterialFileUrl = computed(() => {
  if (!activeMaterial.value) return ''
  return materialFileUrl(activeMaterial.value)
})
```

把现有 `readerFileUrl(material: Material)` 改名或包装为通用函数：

```ts
function materialFileUrl(material: Material) {
  if (contentSource.value === 'public') return getPublicMaterialFileUrl(material.id)
  if (material.file_id) return `/api/files/${material.file_id}`
  return material.url
}

function readerFileUrl(material: Material) {
  return materialFileUrl(material)
}
```

- [ ] **Step 5: 增加资料选择方法**

在 `previewMaterial` 附近增加：

```ts
function selectMaterial(material: Material | null) {
  if (!material) return
  activeMaterialId.value = material.id
}
```

- [ ] **Step 6: 在数据加载后初始化默认资料**

在 `loadData()` 成功设置 `materials.value = loaded.materialList` 后，增加：

```ts
const currentActive = loaded.materialList.find((material) => material.id === activeMaterialId.value)
if (!currentActive) {
  const firstPdf = loaded.materialList.find((material) => material.type === 'pdf')
  const firstVideo = loaded.materialList.find((material) => material.type === 'video')
  const firstLink = loaded.materialList.find((material) => material.type === 'link')
  activeMaterialId.value = (firstPdf || firstVideo || firstLink)?.id ?? null
}
```

- [ ] **Step 7: 运行类型检查**

Run:

```powershell
cd frontend
npm run type-check
```

Expected:

```text
vue-tsc --build
```

Exit code should be 0.

## Task 4: 改造资料 tab 模板为文档站直读布局

**Files:**

- Modify: `frontend/src/views/CourseDetailView.vue`

- [ ] **Step 1: 替换资料 tab 根模板**

将现有：

```vue
<main v-else class="materials-content">
  <div class="materials-booksite-layout">
```

替换为：

```vue
<main v-else class="materials-content">
  <div class="material-doc-shell">
```

- [ ] **Step 2: 替换左侧目录为资料选择目录**

将 `materials-sidebar` 这一段替换为：

```vue
<aside class="material-doc-sidebar">
  <section class="doc-panel">
    <p class="doc-panel-kicker">资料目录</p>
    <h2>{{ course?.name || '学习资料' }}</h2>
    <div v-if="materialSections.length" class="doc-section-list">
      <section v-for="section in materialSections" :key="section.key" class="doc-section-group">
        <button
          type="button"
          class="doc-section-title"
          @click="section.materials[0] && selectMaterial(section.materials[0])"
        >
          <span>{{ section.label }}</span>
          <strong>{{ section.title }}</strong>
        </button>
        <button
          v-for="material in section.materials"
          :key="material.id"
          type="button"
          :class="['doc-material-link', { active: activeMaterial?.id === material.id }]"
          @click="selectMaterial(material)"
        >
          <span class="material-type">{{ materialTypeLabel(material.type) }}</span>
          <strong>{{ material.title }}</strong>
          <small>{{ materialSummary(material) }}</small>
        </button>
      </section>
    </div>
    <div v-else class="materials-empty-small">暂无资料目录</div>
  </section>
</aside>
```

- [ ] **Step 3: 替换中间内容为直读器**

将现有 `materials-reader` 中的 header、`stage-section` 循环、`MaterialRichCard` 卡片流替换为：

```vue
<section class="material-doc-main">
  <MaterialInlineReader
    :material="activeMaterial"
    :file-url="activeMaterialFileUrl"
  />
</section>
```

- [ ] **Step 4: 替换右侧为当前资料导读**

将现有 `materials-rail` 替换为：

```vue
<aside class="material-doc-guide">
  <section class="guide-panel">
    <p class="doc-panel-kicker">当前资料</p>
    <h2>{{ activeMaterial?.title || '未选择资料' }}</h2>
    <p class="guide-summary">
      {{ activeMaterial ? materialSummary(activeMaterial) : '请选择左侧目录中的资料开始阅读。' }}
    </p>
    <dl v-if="activeMaterial" class="guide-facts">
      <div>
        <dt>类型</dt>
        <dd>{{ materialTypeLabel(activeMaterial.type) }}</dd>
      </div>
      <div v-if="activeMaterial.size">
        <dt>大小</dt>
        <dd>{{ activeMaterial.size }}</dd>
      </div>
      <div v-if="activeMaterial.preview?.page_count">
        <dt>页数</dt>
        <dd>{{ activeMaterial.preview.page_count }} 页</dd>
      </div>
      <div v-if="activeMaterial.preview?.duration_seconds">
        <dt>时长</dt>
        <dd>{{ Math.max(1, Math.round(activeMaterial.preview.duration_seconds / 60)) }} 分钟</dd>
      </div>
    </dl>
    <a
      v-if="activeMaterialFileUrl"
      class="guide-open-link"
      :href="activeMaterialFileUrl"
      target="_blank"
      rel="noopener"
    >
      打开原资料
    </a>
  </section>

  <section class="guide-panel">
    <p class="doc-panel-kicker">阅读顺序</p>
    <button
      type="button"
      class="guide-nav"
      :disabled="!prevMaterial"
      @click="selectMaterial(prevMaterial)"
    >
      <span>上一份资料</span>
      <strong>{{ prevMaterial?.title || '已经是第一份' }}</strong>
    </button>
    <button
      type="button"
      class="guide-nav"
      :disabled="!nextMaterial"
      @click="selectMaterial(nextMaterial)"
    >
      <span>下一份资料</span>
      <strong>{{ nextMaterial?.title || '已经是最后一份' }}</strong>
    </button>
  </section>
</aside>
```

- [ ] **Step 5: 保留课程目录 tab 的资料弹窗**

保留模板末尾现有：

```vue
<MaterialPreviewDialog
  v-model:visible="previewVisible"
  :material="selectedMaterial"
  :preview-url="selectedMaterialPreviewUrl"
/>
```

不要删除。课程目录 tab 中的 `LessonReader` 仍可能通过 `@preview="previewMaterial"` 使用弹窗。

- [ ] **Step 6: 运行静态测试确认模板断言通过**

Run:

```powershell
cd frontend
node .\tests\public-learning-static.test.mjs
```

Expected:

```text
public-learning-static: 所有断言通过
```

如果输出因控制台编码显示乱码，只要 exit code 为 0 即通过。

## Task 5: 重写资料页样式为文档站阅读布局

**Files:**

- Modify: `frontend/src/views/CourseDetailView.vue`

- [ ] **Step 1: 删除或停止使用旧资料页样式**

在 style 中保留课程目录 tab 的 `.booksite-layout`、`.reader-sidebar`、`.reader-main`、`.resource-rail` 样式。

将资料 tab 不再使用的旧类逐步删除或保留为未引用样式：

- `.materials-booksite-layout`
- `.materials-sidebar`
- `.materials-panel`
- `.material-toc-item`
- `.materials-reader`
- `.materials-reader-header`
- `.material-flow`
- `.materials-rail`

不要删除 `.stage-section` 和 `.material-grid`，除非确认课程目录 tab 或其他模板不再引用。

- [ ] **Step 2: 新增文档站资料页桌面样式**

在 `.materials-content` 后增加：

```css
.material-doc-shell {
  max-width: 1480px;
  margin: 0 auto;
  padding: 24px 24px 80px;
  display: grid;
  grid-template-columns: 292px minmax(0, 1fr) 280px;
  gap: 24px;
  align-items: flex-start;
}

.material-doc-sidebar,
.material-doc-guide {
  position: sticky;
  top: calc(var(--app-header-height) + 16px);
  max-height: calc(100vh - var(--app-header-height) - 32px);
  overflow-y: auto;
}

.doc-panel,
.guide-panel {
  padding: 16px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.doc-panel-kicker {
  margin: 0 0 6px;
  color: var(--color-learn);
  font-size: 0.74rem;
  font-weight: 900;
}

.doc-panel h2,
.guide-panel h2 {
  margin: 0 0 14px;
  color: var(--color-text);
  font-size: 1rem;
  font-weight: 900;
  line-height: var(--leading-compact);
}

.doc-section-list {
  display: grid;
  gap: 14px;
}

.doc-section-group {
  display: grid;
  gap: 6px;
}

.doc-section-title,
.doc-material-link,
.guide-nav {
  width: 100%;
  text-align: left;
}

.doc-section-title {
  display: grid;
  gap: 3px;
  padding: 8px 4px;
  color: var(--color-text);
  background: transparent;
}

.doc-section-title span {
  color: var(--color-learn);
  font-size: 0.72rem;
  font-weight: 900;
}

.doc-section-title strong {
  font-size: 0.92rem;
}

.doc-material-link {
  display: grid;
  gap: 4px;
  padding: 10px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  transition: background 160ms var(--ease-out), border-color 160ms var(--ease-out);
}

.doc-material-link:hover,
.doc-material-link.active {
  background: var(--color-bg-alt);
  border-color: rgba(45, 106, 122, 0.22);
}

.doc-material-link.active {
  box-shadow: inset 0 0 0 1px rgba(45, 106, 122, 0.18);
}

.doc-material-link strong {
  color: var(--color-text);
  font-size: 0.88rem;
  line-height: 1.45;
}

.doc-material-link small {
  color: var(--color-text-muted);
  font-size: 0.78rem;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.material-doc-main {
  min-width: 0;
}

.material-doc-guide {
  display: grid;
  gap: 16px;
}

.guide-summary {
  margin: 0 0 12px;
  color: var(--color-text-secondary);
  line-height: 1.7;
  text-wrap: pretty;
}

.guide-facts {
  display: grid;
  gap: 8px;
  margin: 0;
}

.guide-facts div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--color-border-light);
}

.guide-facts div:last-child {
  border-bottom: 0;
}

.guide-facts dt {
  color: var(--color-text-muted);
}

.guide-facts dd {
  margin: 0;
  color: var(--color-text);
  font-weight: 800;
}

.guide-open-link {
  display: inline-flex;
  justify-content: center;
  width: 100%;
  margin-top: 12px;
  padding: 9px 12px;
  color: var(--color-bg-card);
  background: var(--color-learn);
  border-radius: var(--radius-sm);
  font-weight: 800;
}

.guide-nav {
  display: grid;
  gap: 4px;
  padding: 10px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  background: var(--color-bg-alt);
}

.guide-nav:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.guide-nav span {
  color: var(--color-text-muted);
  font-size: 0.76rem;
}

.guide-nav strong {
  color: var(--color-text);
  line-height: 1.45;
}
```

- [ ] **Step 3: 增加 1180px 响应式**

在现有 `@media (max-width: 1180px)` 中增加：

```css
.material-doc-shell {
  grid-template-columns: 260px minmax(0, 1fr);
}

.material-doc-guide {
  grid-column: 2;
  position: static;
  max-height: none;
}
```

- [ ] **Step 4: 增加 900px 移动端响应式**

在现有 `@media (max-width: 900px)` 中增加：

```css
.material-doc-shell {
  display: block;
  padding: 18px 16px 60px;
}

.material-doc-sidebar,
.material-doc-guide {
  position: static;
  max-height: none;
}

.material-doc-sidebar {
  margin-bottom: 18px;
}

.material-doc-guide {
  margin-top: 18px;
}

.doc-section-list {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.doc-section-group {
  min-width: 240px;
}
```

- [ ] **Step 5: 运行类型检查和构建**

Run:

```powershell
cd frontend
npm run type-check
npm run build
```

Expected:

```text
vue-tsc --build
✓ built
```

允许 Vite 保留现有 chunk size warning，不允许 TypeScript 或 Vite 构建错误。

## Task 6: 浏览器验收和真实文件验证

**Files:**

- No source file changes unless verification reveals a bug.

- [ ] **Step 1: 确认本地服务运行**

Run:

```powershell
try { (Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5174/ -TimeoutSec 3).StatusCode } catch { $_.Exception.Message }
try { (Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8050/api/public/learning/courses -TimeoutSec 3).StatusCode } catch { $_.Exception.Message }
```

Expected:

```text
200
200
```

如果服务未运行，先按项目现有本地启动方式启动前端和后端，不要改代码。

- [ ] **Step 2: 截图桌面端资料页**

Run:

```powershell
New-Item -ItemType Directory -Force -Path output\webtest\inline-reader | Out-Null
npx playwright screenshot --viewport-size=1440,1000 "http://127.0.0.1:5174/learn/course/1?tab=materials" output\webtest\inline-reader\course-materials-inline-desktop.png
```

Expected visual:

- 左侧是阶段化资料目录，目录项是资料标题，不只是阶段跳转。
- 中间直接显示当前 PDF 或视频，不需要点击“预览”。
- 右侧只围绕当前资料，不显示“全部资料 / PDF / 视频 / 链接”统计卡。
- 页面没有乱码。

- [ ] **Step 3: 截图移动端资料页**

Run:

```powershell
npx playwright screenshot --viewport-size=390,844 "http://127.0.0.1:5174/learn/course/1?tab=materials" output\webtest\inline-reader\course-materials-inline-mobile.png
```

Expected visual:

- 内容单列展示。
- 目录、阅读器、导读不互相遮挡。
- PDF 阅读区仍是主区域。
- 按钮文字不溢出。

- [ ] **Step 4: 用 Playwright 断言 PDF 已内嵌**

Run:

```powershell
@'
const { chromium } = require('playwright')

;(async () => {
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
  await page.goto('http://127.0.0.1:5174/learn/course/1?tab=materials', { waitUntil: 'networkidle' })
  const result = await page.evaluate(() => {
    const object = document.querySelector('.material-inline-reader object[type="application/pdf"]')
    const video = document.querySelector('.material-inline-reader video')
    const card = document.querySelector('main.materials-content .material-rich-card')
    return {
      hasPdfObject: Boolean(object),
      hasVideo: Boolean(video),
      hasCardInMain: Boolean(card),
      bodyText: document.body.innerText.slice(0, 1000),
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }
  })
  console.log(JSON.stringify(result, null, 2))
  await browser.close()
})()
'@ | node -
```

Expected:

```json
{
  "hasPdfObject": true,
  "hasCardInMain": false
}
```

如果课程 1 当前默认不是 PDF，则 `hasPdfObject` 可能为 false，但必须有 `hasVideo: true` 或链接落地页，并且 `hasCardInMain: false`。若本地测试数据里有 PDF，应保持默认优先选择 PDF。

## Task 7: 资料预览状态轻量实时刷新

**Files:**

- Modify: `frontend/tests/public-learning-static.test.mjs`
- Modify: `frontend/src/views/CourseDetailView.vue`

- [ ] **Step 1: 增加静态测试断言**

在 `CourseDetailView.vue` 相关断言中增加：

```js
assert.match(detail, /hasRefreshingMaterialPreview/, '学习资料页应识别是否存在生成中的资料预览')
assert.match(detail, /refreshMaterialsForInlineReader/, '学习资料页应提供直读器资料刷新方法')
assert.match(detail, /setInterval[\s\S]*refreshMaterialsForInlineReader/, '学习资料页应在预览生成中定时刷新资料数据')
assert.match(detail, /visibilitychange/, '学习资料页应在页面重新可见时刷新资料数据')
assert.match(detail, /clearInterval/, '学习资料页卸载时应清理资料刷新定时器')
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
cd frontend
node .\tests\public-learning-static.test.mjs
```

Expected:

```text
AssertionError: 学习资料页应识别是否存在生成中的资料预览
```

- [ ] **Step 3: 扩展 Vue lifecycle import**

将 `CourseDetailView.vue` 顶部：

```ts
import { computed, onMounted, ref } from 'vue'
```

改为：

```ts
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
```

- [ ] **Step 4: 增加预览状态计算和刷新定时器引用**

在 `activeMaterial` 相关计算后增加：

```ts
const hasRefreshingMaterialPreview = computed(() =>
  activeTab.value === 'materials' &&
  materials.value.some((material) =>
    ['pending', 'processing'].includes(material.preview?.status || ''),
  ),
)

let materialRefreshTimer: number | undefined
```

- [ ] **Step 5: 增加直读资料刷新方法**

在 `loadData` 后增加：

```ts
async function refreshMaterialsForInlineReader() {
  if (activeTab.value !== 'materials') return
  try {
    if (contentSource.value === 'authenticated') {
      const materialList = await getCourseContents(courseId.value)
      materials.value = materialList
      return
    }

    const detail = await getPublicCourseDetail(courseId.value, true)
    const refreshedStages = detail.stages ?? []
    course.value = {
      ...detail,
      stages: refreshedStages,
      uncategorized_materials: detail.uncategorized_materials ?? [],
    }
    materials.value = [
      ...refreshedStages.flatMap((stage) => stage.materials ?? []),
      ...(detail.uncategorized_materials ?? []),
    ]
  } catch {
    // 资料状态刷新失败不打断当前阅读。
  }
}
```

- [ ] **Step 6: 增加定时器控制方法**

在 `refreshMaterialsForInlineReader` 后增加：

```ts
function stopMaterialRefreshTimer() {
  if (materialRefreshTimer !== undefined) {
    window.clearInterval(materialRefreshTimer)
    materialRefreshTimer = undefined
  }
}

function syncMaterialRefreshTimer() {
  stopMaterialRefreshTimer()
  if (!hasRefreshingMaterialPreview.value || document.hidden) return
  materialRefreshTimer = window.setInterval(refreshMaterialsForInlineReader, 18000)
}

function handleVisibilityChange() {
  if (document.hidden) {
    stopMaterialRefreshTimer()
    return
  }
  if (activeTab.value === 'materials') {
    void refreshMaterialsForInlineReader()
  }
  syncMaterialRefreshTimer()
}
```

- [ ] **Step 7: 挂载 watch 和卸载清理**

把文件末尾现有：

```ts
onMounted(loadData)
```

改为：

```ts
watch(hasRefreshingMaterialPreview, syncMaterialRefreshTimer)
watch(activeTab, () => {
  if (activeTab.value === 'materials') {
    void refreshMaterialsForInlineReader()
  }
  syncMaterialRefreshTimer()
})

onMounted(() => {
  void loadData()
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onBeforeUnmount(() => {
  stopMaterialRefreshTimer()
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
```

- [ ] **Step 8: 运行验证**

Run:

```powershell
cd frontend
node .\tests\public-learning-static.test.mjs
npm run type-check
```

Expected:

```text
public-learning-static: 所有断言通过
vue-tsc --build
```

Exit code should be 0.

## Task 8: 文档记录和最终校验

**Files:**

- Modify: `docs/superpowers/project-map.md`

- [ ] **Step 1: 更新修改记录**

在 `## 修改记录` 顶部新增：

```markdown
### 2026-07-07 课程资料页直读式文档站落地

- 问题：学习资料页虽然已有三栏，但中间仍是资料卡片流，PDF/视频需要通过“预览”弹窗查看，不符合用户希望接近古月居图书资源等学习文档站的直读体验。
- 修复：`/learn/course/:courseId?tab=materials` 改为直读式资料页面，左侧按阶段选择资料，中间直接嵌入当前 PDF/视频/链接阅读框，右侧只展示当前资料导读、原资料入口和上一份/下一份；当资料预览仍在生成中时，页面可见状态下轻量轮询刷新资料状态，回到页面时立即刷新。
- 保留：不修改后端接口、数据库结构、上传流程、教师端资料管理、管理员公共课程资料管理；`MaterialPreviewDialog` 继续保留给课程正文和管理场景备用。
- 验证：执行 `node .\tests\public-learning-static.test.mjs`、`npm run type-check`、`npm run build`，并用 Playwright 截图桌面端和移动端资料页。
- 服务器部署影响：本次为前端页面改造；上线需要服务器拉取前端代码、重新构建并部署前端静态资源；不需要后端重启、不需要数据库迁移、不需要修改环境变量或 Nginx 配置。
```

- [ ] **Step 2: 运行最终验证**

Run:

```powershell
cd frontend
node .\tests\public-learning-static.test.mjs
npm run type-check
npm run build
```

Expected:

```text
public-learning-static: 所有断言通过
vue-tsc --build
✓ built
```

- [ ] **Step 3: 运行 diff 检查**

Run:

```powershell
git diff --check
```

Expected:

```text
```

允许 Windows 工作区输出 LF/CRLF warning；不允许 trailing whitespace 或 conflict marker。

- [ ] **Step 4: 汇总变更范围**

Run:

```powershell
git status --short
```

Expected:

- 能看到本次计划涉及的文件。
- 若工作区还有其他既有改动，不回滚，不覆盖，只在总结中说明。

## 自查清单

- [ ] 覆盖调研要求：接近 `book.guyuehome.com` 的左目录、中正文、右导读结构。
- [ ] 覆盖“不再跳转/弹窗才能预览 PDF”：PDF 直接内嵌到中间阅读区。
- [ ] 覆盖“分阶段展示更清晰”：阶段变成左侧目录分组，资料是可点击文档项。
- [ ] 覆盖“实时更新”：不引入 WebSocket，但实现页面可见时对 `pending` / `processing` 资料预览状态的轻量轮询刷新，并在页面重新可见时立即刷新。
- [ ] 覆盖不改后端、不改数据库、不改上传流程。
- [ ] 覆盖桌面端和移动端截图验收。
- [ ] 覆盖服务器部署影响说明。

## 执行提示

本计划还没有开始改业务代码。正式执行前，需要用户明确同意“开始写代码”或“执行计划”。推荐使用 Subagent-Driven 方式逐任务执行，并在 Task 4、Task 6 和 Task 7 后做人工截图或行为检查。
