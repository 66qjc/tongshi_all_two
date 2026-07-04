# 课程资料页书站式展示实施计划

> **2026-07-03 更新：** 用户已确认第一版“资料工作台/卡片流”仍然过重，后续正式实现应以 `docs/superpowers/specs/2026-07-03-course-materials-pdf-reader-design.md` 的“PDF 直读式展示”为准。本计划保留为历史记录，不建议继续按中间资料卡片流方案实施。

> **给后续编码代理：** 实施本计划时必须逐项勾选任务。正式改业务代码前，继续遵守项目 `AGENTS.md`：先确认范围、再写代码；实现阶段建议使用 `subagent-driven-development` 或 `executing-plans` 按任务推进。

**目标：** 将 `/learn/course/:courseId?tab=materials` 的“学习资料”页签从普通两列资料卡片，改为接近 `https://book.guyuehome.com/` 的书站式文件展示体验。

**架构：** 本次只改前端展示层，继续复用现有公开学习接口、课程详情数据、`MaterialRichCard` 和资料预览弹窗。材料页签改为三栏布局：左侧阶段资料目录，中间连续资料阅读流，右侧本页资料索引与课程信息；课程目录页签现有左目录、中正文、右资源栏不改变。

**技术栈：** Vue 3 `<script setup lang="ts">`、Vue Router、Element Plus、现有 `MaterialRichCard.vue`、现有公开学习 API。

---

## 一、现状与根因

当前用户指定页面是：

```text
http://127.0.0.1:5173/learn/course/2?tab=materials
```

实测运行态显示为“阶段标题 + 两列资料卡片”：

- 顶部课程信息正常。
- “学习资料”页签已进入资料视图。
- 资料按阶段展示，卡片内有类型、标题、摘要、元信息和“预览”按钮。
- 但该页签没有左侧固定目录、没有右侧本页索引，也没有形成类似书站的连续阅读结构。

根因是：`CourseDetailView.vue` 的书站式三栏布局只覆盖 `activeTab === 'lessons'` 的课程目录/课时阅读视图；`activeTab === 'materials'` 仍使用 `.materials-content > .stage-section > .material-grid` 的普通网格布局。课程 2 当前公开课时数为 0、资料数为 10，因此入口会优先进入 `tab=materials`，用户自然看不到已经做在课时阅读页签里的书站结构。

---

## 二、范围

### 本次做

1. 改造 `CourseDetailView.vue` 的“学习资料”页签为书站式三栏文件展示。
2. 左栏显示阶段目录和每阶段资料数量，点击后滚动到对应阶段。
3. 中栏显示连续资料流，每个阶段像文档章节一样展示标题、说明和资料卡片。
4. 右栏显示资料类型统计、当前课程信息、全部资料索引和游客学习提示。
5. 保留现有资料预览弹窗，点击“预览”仍走 `previewMaterial(material)`。
6. 保留公开资料预览 URL 逻辑，游客预览仍走 `/api/public/learning/materials/{material_id}/file`。
7. 增加静态回归测试，防止材料页签退回普通两列网格。
8. 更新项目修改记录，写明服务器部署影响。

### 本次不做

1. 不改后端接口。
2. 不改数据库结构。
3. 不新增资料模型、章节模型或静态站构建链路。
4. 不把项目迁移到 MkDocs。
5. 不改教师端、管理员端上传流程。
6. 不处理自动从 PDF 抽章节、自动摘要或自动转正文。
7. 不改变课程目录/课时阅读页签现有行为。

---

## 三、涉及文件

| 文件 | 类型 | 责任 |
| --- | --- | --- |
| `frontend/src/views/CourseDetailView.vue` | 修改 | 材料页签三栏布局、材料目录、右侧索引、响应式样式 |
| `frontend/tests/public-learning-static.test.mjs` | 修改 | 增加材料页签书站式结构和中文文案静态断言 |
| `docs/superpowers/project-map.md` | 修改 | 记录本次页面改造和服务器部署影响 |

不计划修改：

- `backend/app/api/v1/routes/public_learning_routes.py`
- `backend/app/services/public_learning_service.py`
- `frontend/src/api/publicLearning.ts`
- `frontend/src/components/common/MaterialRichCard.vue`

`MaterialRichCard.vue` 现有图文资料卡已经能展示封面、摘要、类型、大小、页数/时长和预览状态，先复用，不拆新组件。

---

## 四、任务拆解

### Task 1：补静态回归测试

**文件：**

- 修改：`frontend/tests/public-learning-static.test.mjs`

**目标：** 先让测试表达用户真正要的页面形态：材料页签不能只是 `.material-grid` 两列卡片，而要有材料目录、正文流和右侧索引。

- [ ] **Step 1：新增材料页签结构断言**

在读取 `CourseDetailView.vue` 的现有断言之后，补充以下断言：

```js
assert.match(detail, /materials-booksite-layout/, '学习资料页签应使用书站式三栏布局容器')
assert.match(detail, /materials-sidebar/, '学习资料页签应包含左侧资料目录')
assert.match(detail, /materials-reader/, '学习资料页签应包含中间资料阅读流')
assert.match(detail, /materials-rail/, '学习资料页签应包含右侧资料索引栏')
assert.match(detail, /资料目录/, '学习资料页签左侧目录标题应为正常中文')
assert.match(detail, /本页资料/, '学习资料页签右侧索引标题应为正常中文')
assert.match(detail, /scrollToMaterialStage/, '学习资料页签目录应能跳转到对应阶段')
```

- [ ] **Step 2：新增防退化断言**

继续在同一测试文件中增加断言，确保材料页签不再只依赖旧两列网格：

```js
assert.ok(
  detail.indexOf('materials-booksite-layout') < detail.indexOf('stage-section'),
  '学习资料页签应先建立书站式布局，再渲染阶段资料内容',
)
assert.match(
  detail,
  /materials-booksite-layout[\s\S]*materials-sidebar[\s\S]*materials-reader[\s\S]*materials-rail/,
  '学习资料页签三栏结构应同时出现在材料页签模板内',
)
```

- [ ] **Step 3：运行静态测试确认失败**

运行：

```bash
cd frontend
node ./tests/public-learning-static.test.mjs
```

预期：失败，提示缺少 `materials-booksite-layout` 或相关结构。这一步证明测试能捕捉当前问题。

---

### Task 2：增加材料页签所需计算数据和滚动方法

**文件：**

- 修改：`frontend/src/views/CourseDetailView.vue`

**目标：** 在不改接口数据的前提下，从现有 `course.stages`、`course.uncategorized_materials` 和 `materials` 推导左目录、正文流和右栏索引需要的数据。

- [ ] **Step 1：在 `railMaterials` 附近新增材料分组计算属性**

新增代码：

```ts
const materialSections = computed(() => {
  const sections = (course.value?.stages ?? []).map((stage, index) => ({
    key: `stage-${stage.id}`,
    id: stage.id,
    title: stage.name,
    label: `阶段 ${index + 1}`,
    materials: stage.materials ?? [],
  }))

  const uncategorized = course.value?.uncategorized_materials ?? []
  if (uncategorized.length) {
    sections.push({
      key: 'uncategorized',
      id: null,
      title: '未分类资料',
      label: '其他',
      materials: uncategorized,
    })
  }

  return sections
})
```

- [ ] **Step 2：新增右侧类型统计**

新增代码：

```ts
const materialTypeStats = computed(() => {
  const initial = { pdf: 0, video: 0, link: 0 }
  return materials.value.reduce((stats, material) => {
    stats[material.type] += 1
    return stats
  }, initial)
})
```

- [ ] **Step 3：新增材料目录跳转方法**

新增代码：

```ts
function scrollToMaterialStage(key: string) {
  const target = document.getElementById(`material-section-${key}`)
  if (!target) return
  target.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
```

- [ ] **Step 4：运行类型检查**

运行：

```bash
cd frontend
npm run type-check
```

预期：通过。若 TypeScript 报 `material.type` 索引不兼容，改为显式判断：

```ts
if (material.type === 'pdf') stats.pdf += 1
if (material.type === 'video') stats.video += 1
if (material.type === 'link') stats.link += 1
```

---

### Task 3：改造学习资料页签模板

**文件：**

- 修改：`frontend/src/views/CourseDetailView.vue`

**目标：** 将 `v-else class="materials-content"` 内部从单列容器 + 两列网格改成三栏书站式资料展示。

- [ ] **Step 1：替换材料页签根模板**

把现有：

```vue
<main v-else class="materials-content">
  <div class="container">
    ...
  </div>
</main>
```

替换为：

```vue
<main v-else class="materials-content">
  <div class="materials-booksite-layout">
    <aside class="materials-sidebar">
      <section class="materials-panel">
        <h2>资料目录</h2>
        <button
          v-for="section in materialSections"
          :key="section.key"
          type="button"
          class="material-toc-item"
          @click="scrollToMaterialStage(section.key)"
        >
          <span>{{ section.label }}</span>
          <strong>{{ section.title }}</strong>
          <small>{{ section.materials.length }} 份资料</small>
        </button>
        <div v-if="!materialSections.length" class="materials-empty-small">暂无资料目录</div>
      </section>
    </aside>

    <section class="materials-reader">
      <header class="materials-reader-header">
        <p class="course-kicker">课程资料库</p>
        <h2>{{ course?.name || '学习资料' }}</h2>
        <p>按阶段整理课程 PDF、视频与外部链接。先浏览目录，再打开资料预览。</p>
      </header>

      <section
        v-for="section in materialSections"
        :id="`material-section-${section.key}`"
        :key="section.key"
        class="stage-section"
      >
        <h2>
          <span class="stage-badge">{{ section.label }}</span>
          {{ section.title }}
        </h2>
        <div v-if="section.materials.length > 0" class="material-flow">
          <MaterialRichCard
            v-for="material in section.materials"
            :key="material.id"
            :material="material"
            @preview="previewMaterial"
          />
        </div>
        <div v-else class="stage-empty">该阶段暂无资料</div>
      </section>

      <div v-if="!materialSections.length" class="empty-state">
        该课程暂无学习资料。
      </div>
    </section>

    <aside class="materials-rail">
      <section class="rail-section">
        <h2>本页资料</h2>
        <dl class="course-facts">
          <div>
            <dt>全部资料</dt>
            <dd>{{ materials.length }}</dd>
          </div>
          <div>
            <dt>PDF</dt>
            <dd>{{ materialTypeStats.pdf }}</dd>
          </div>
          <div>
            <dt>视频</dt>
            <dd>{{ materialTypeStats.video }}</dd>
          </div>
          <div>
            <dt>链接</dt>
            <dd>{{ materialTypeStats.link }}</dd>
          </div>
        </dl>
      </section>

      <section class="rail-section">
        <h2>快速打开</h2>
        <div v-if="materials.length" class="rail-material-list">
          <button
            v-for="material in materials.slice(0, 8)"
            :key="material.id"
            type="button"
            class="rail-material"
            @click="previewMaterial(material)"
          >
            <span class="material-type">{{ materialTypeLabel(material.type) }}</span>
            <strong>{{ material.title }}</strong>
            <small>{{ materialSummary(material) }}</small>
          </button>
        </div>
        <div v-else class="rail-empty">暂无可打开的资料。</div>
      </section>

      <section v-if="contentSource === 'public' && !canSaveProgress" class="rail-section">
        <h2>学习提示</h2>
        <p class="rail-note">游客可以浏览公开资料；登录后可保存学习进度。</p>
      </section>
    </aside>
  </div>
</main>
```

- [ ] **Step 2：确认课程目录页签模板未改变**

人工检查 `activeTab === 'lessons'` 分支仍然保留：

```vue
<div class="booksite-layout">
  <aside class="reader-sidebar" :class="{ open: sidebarOpen }">
  <main class="reader-main">
  <aside class="resource-rail">
</div>
```

不要把课程目录页签改坏。

---

### Task 4：补材料页签书站式样式

**文件：**

- 修改：`frontend/src/views/CourseDetailView.vue`

**目标：** 桌面端呈现类似书站的左目录、中内容、右索引；移动端降级为单栏，不遮挡正文。

- [ ] **Step 1：替换或补充材料页样式**

保留 `.materials-content`，新增以下样式：

```css
.materials-content {
  padding: 0 0 4rem;
}

.materials-booksite-layout {
  max-width: 1480px;
  margin: 0 auto;
  padding: 24px 24px 80px;
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr) 300px;
  gap: 24px;
  align-items: flex-start;
}

.materials-sidebar,
.materials-rail {
  position: sticky;
  top: calc(var(--app-header-height) + 16px);
  max-height: calc(100vh - var(--app-header-height) - 32px);
  overflow-y: auto;
}

.materials-panel {
  padding: 16px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.materials-panel h2 {
  margin: 0 0 12px;
  color: var(--color-text);
  font-size: 1rem;
  font-weight: 900;
}

.material-toc-item {
  display: grid;
  gap: 4px;
  width: 100%;
  padding: 10px;
  margin-bottom: 6px;
  text-align: left;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  transition: background 160ms var(--ease-out), border-color 160ms var(--ease-out);
}

.material-toc-item:hover {
  background: var(--color-bg-alt);
  border-color: rgba(45, 106, 122, 0.18);
}

.material-toc-item span {
  color: var(--color-learn);
  font-size: 0.72rem;
  font-weight: 900;
}

.material-toc-item strong {
  color: var(--color-text);
  font-size: 0.9rem;
  line-height: 1.45;
}

.material-toc-item small,
.materials-empty-small {
  color: var(--color-text-muted);
  font-size: 0.8rem;
}

.materials-reader {
  min-width: 0;
  max-width: 900px;
  width: 100%;
  margin: 0 auto;
}

.materials-reader-header {
  margin-bottom: 24px;
  padding: 32px 36px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.materials-reader-header h2 {
  margin: 0 0 10px;
  color: var(--color-text);
  font-size: 1.55rem;
  font-weight: 900;
}

.materials-reader-header p:last-child {
  max-width: 680px;
  margin: 0;
  color: var(--color-text-secondary);
  line-height: 1.8;
}

.material-flow {
  display: grid;
  gap: 16px;
}

.materials-rail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
```

- [ ] **Step 2：调整旧 `.stage-section` 和 `.material-grid` 影响范围**

现有 `.stage-section` 可继续复用，但需要确保材料流不再强制两列。把旧材料网格样式保留给其他潜在位置，或改为：

```css
.material-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.25rem;
}
```

材料页新模板使用 `.material-flow`，不再使用 `.material-grid`。

- [ ] **Step 3：补 1180px 响应式**

在已有 `@media (max-width: 1180px)` 中加入：

```css
.materials-booksite-layout {
  grid-template-columns: 240px minmax(0, 1fr);
}

.materials-rail {
  grid-column: 2;
  position: static;
  max-height: none;
}
```

- [ ] **Step 4：补 900px 移动端响应式**

在已有 `@media (max-width: 900px)` 中加入：

```css
.materials-booksite-layout {
  display: block;
  padding: 18px 16px 60px;
}

.materials-sidebar,
.materials-rail {
  position: static;
  max-height: none;
}

.materials-sidebar {
  margin-bottom: 18px;
}

.materials-reader-header {
  padding: 24px 20px;
}

.materials-rail {
  margin-top: 18px;
}
```

预期：移动端按“资料目录、资料正文、右侧信息”顺序纵向展示，不做抽屉，避免和现有课程目录抽屉混在一起。

---

### Task 5：更新项目记录

**文件：**

- 修改：`docs/superpowers/project-map.md`

**目标：** 记录这次页面改造，并明确服务器部署影响。

- [ ] **Step 1：在“修改记录”顶部新增记录**

新增内容：

```markdown
### 2026-07-03 课程资料页书站式展示

- 问题：用户指定 `/learn/course/2?tab=materials` 的文件展示需要效仿古月居书站，但现有“学习资料”页签仍是阶段标题加两列资料卡片；书站式三栏布局只覆盖课程目录/课时阅读页签。
- 修复：`CourseDetailView.vue` 的“学习资料”页签改为书站式三栏布局，左侧为资料目录，中间为按阶段组织的连续资料阅读流，右侧为资料类型统计、快速打开和学习提示。
- 保留：公开学习接口、资料预览弹窗、公开资料文件 URL、教师端和管理员端上传流程均不改变。
- 回归保护：更新 `frontend/tests/public-learning-static.test.mjs`，覆盖材料页签三栏结构、正常中文文案和目录跳转方法。
- 服务器部署影响：需要服务器拉取前端代码并重新构建、部署前端静态资源；不需要后端重启，不需要数据库迁移，不需要修改环境变量或 Nginx 配置。
```

---

### Task 6：验证

**文件：**

- 无新增业务文件。

- [ ] **Step 1：运行静态测试**

```bash
cd frontend
node ./tests/public-learning-static.test.mjs
```

预期：

```text
public-learning-static: 所有断言通过
```

- [ ] **Step 2：运行前端构建**

```bash
cd frontend
npm run build
```

预期：构建通过。允许保留当前项目已有 chunk size warning，但不能有 TypeScript 或 Vite 构建错误。

- [ ] **Step 3：浏览器截图验证桌面端**

```bash
npx playwright screenshot --viewport-size=1440,1000 http://127.0.0.1:5173/learn/course/2?tab=materials output/playwright/learn-course-materials-booksite-desktop.png
```

验收：

- 能看到左侧“资料目录”。
- 中间不再是两列网格，而是按阶段纵向排列的资料阅读流。
- 右侧能看到“本页资料”和快速打开。
- “预览”按钮仍存在。
- 页面无中文乱码。

- [ ] **Step 4：浏览器截图验证移动端**

```bash
npx playwright screenshot --viewport-size=390,844 http://127.0.0.1:5173/learn/course/2?tab=materials output/playwright/learn-course-materials-booksite-mobile.png
```

验收：

- 内容单栏展示。
- 资料目录、资料正文、资料索引不互相遮挡。
- 顶部固定导航不压住正文。
- 按钮文字不溢出。

---

## 五、验收标准

1. `/learn/course/2?tab=materials` 桌面端呈现书站式文件展示：左资料目录、中资料阅读流、右资料索引。
2. 资料仍按阶段分组展示，未分类资料有“其他 / 未分类资料”分组。
3. PDF、视频、链接三类资料都能显示类型、标题、摘要、元信息和预览入口。
4. 点击左侧阶段目录能滚动到对应资料阶段。
5. 点击右侧快速打开或资料卡片预览按钮仍打开现有资料预览弹窗。
6. 课程目录页签现有三栏课时阅读不退化。
7. 移动端不出现目录、正文、右栏互相遮挡。
8. 页面所有新增文案为正常中文，无乱码。
9. `node ./tests/public-learning-static.test.mjs` 通过。
10. `npm run build` 通过。

---

## 六、风险与处理

1. 风险：材料页签和课时阅读页签都使用右侧栏样式，可能样式互相影响。
   - 处理：材料页签使用 `.materials-*` 独立命名，不复用 `.booksite-layout` 作为根类。
2. 风险：移动端如果沿用抽屉，会和课时目录抽屉交互混淆。
   - 处理：材料页签移动端不做抽屉，直接纵向展示资料目录。
3. 风险：课程没有阶段但有未分类资料时页面为空。
   - 处理：`materialSections` 将 `uncategorized_materials` 推入“其他 / 未分类资料”。
4. 风险：资料很多时右侧快速打开过长。
   - 处理：右侧快速打开只显示前 8 个，完整资料仍在中间资料流中展示。
5. 风险：只改视觉但用户仍以为服务器已生效。
   - 处理：修改记录和总结必须明确服务器需要重新构建并部署前端静态资源。

---

## 七、执行交接

计划完成后，执行前需要用户明确说“开始写代码”或“执行计划”。

建议执行方式：

1. **Subagent-Driven（推荐）**：按 Task 1-6 分段执行，每段后检查 diff 和测试。
2. **Inline Execution**：在当前会话内按任务顺序实现，每完成一个任务更新计划状态。
