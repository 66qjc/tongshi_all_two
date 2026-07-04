# Element Plus 白名单注册优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 移除 `app.use(ElementPlus)` 全量 JS 注册，按项目实际 `<el-*>` 用量注册 Element Plus 组件，继续降低首屏必须下载和执行的 Element Plus vendor 成本。

**架构：** 保留 `element-plus/dist/index.css` 全局样式和中文 locale，避免拆样式造成全站样式缺失；JS 层改为命名导入实际使用组件并循环 `app.use(component)`。通过 `provideGlobalConfig({ locale: zhCn }, app, true)` 维持中文配置，通过 `ElLoading` 安装器维持 `v-loading` 指令和 `$loading` 服务。

**技术栈：** Vue 3、Element Plus、Vite、Node 静态断言测试。

---

## 范围

### 本轮做

1. 新增 `frontend/tests/element-plus-whitelist-static.test.mjs`。
2. 修改 `frontend/src/main.ts`，移除默认 `ElementPlus` 插件安装。
3. 在 `main.ts` 显式导入并注册当前项目实际使用的 Element Plus 组件。
4. 保留 `ElMessage`、`ElMessageBox` 等按页面局部导入的服务调用方式，不改业务页面。
5. 运行静态测试和完整构建，观察 `vendor-element-plus` 体积变化。

### 本轮不做

1. 不拆 Element Plus CSS。
2. 不改任意业务页面模板。
3. 不引入自动按需插件。
4. 不删除页面内已有 `ElMessage` / `ElMessageBox` 导入。

## 验收标准

1. 静态测试在修改前失败，失败原因指向 `main.ts` 仍默认导入或安装 Element Plus。
2. 修改后静态测试通过。
3. `node ./tests/chunk-optimization-static.test.mjs` 和 `node ./tests/vendor-chunk-splitting-static.test.mjs` 仍通过。
4. `npm.cmd run build` 通过。
5. 构建产物中 `vendor-element-plus` JS 明显低于第二阶段的约 885.50 kB。
6. `v-loading` 指令仍通过 `ElLoading` 安装器注册。
7. 中文 locale 仍通过 `provideGlobalConfig` 写入全局配置。

## 任务

### Task 1：白名单注册静态测试

**Files:**
- Create: `frontend/tests/element-plus-whitelist-static.test.mjs`

- [ ] **Step 1：写失败测试**

测试读取 `frontend/src/main.ts`，断言：

```js
assert.doesNotMatch(main, /import\s+ElementPlus\s+from\s+['"]element-plus['"]/, '入口不能默认导入 ElementPlus 全量插件')
assert.doesNotMatch(main, /app\.use\(ElementPlus/, '入口不能安装 ElementPlus 全量插件')
assert.match(main, /provideGlobalConfig\(\{\s*locale:\s*zhCn\s*\},\s*app,\s*true\)/, '入口应保留 Element Plus 中文全局配置')
assert.match(main, /app\.use\(ElLoading\)/, '入口应保留 v-loading 指令和 $loading 服务')
```

并检查当前实际使用的组件名都出现在导入和注册数组里。

- [ ] **Step 2：运行测试确认失败**

Run:

```bash
cd frontend
node ./tests/element-plus-whitelist-static.test.mjs
```

Expected: FAIL，提示入口仍默认导入或安装 ElementPlus。

### Task 2：实现白名单注册

**Files:**
- Modify: `frontend/src/main.ts`

- [ ] **Step 1：替换导入**

从 `element-plus` 命名导入：

```ts
import {
  ElAlert,
  ElButton,
  ElCard,
  ElCollapse,
  ElCollapseItem,
  ElDatePicker,
  ElDialog,
  ElDrawer,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElIcon,
  ElInput,
  ElInputNumber,
  ElLoading,
  ElOption,
  ElPagination,
  ElPopconfirm,
  ElProgress,
  ElRadioButton,
  ElRadioGroup,
  ElSelect,
  ElSkeleton,
  ElSwitch,
  ElTable,
  ElTableColumn,
  ElTabPane,
  ElTabs,
  ElTag,
  ElUpload,
  provideGlobalConfig,
} from 'element-plus'
```

- [ ] **Step 2：注册组件和全局配置**

```ts
const elementPlusComponents = [
  ElAlert,
  ElButton,
  ElCard,
  ElCollapse,
  ElCollapseItem,
  ElDatePicker,
  ElDialog,
  ElDrawer,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElIcon,
  ElInput,
  ElInputNumber,
  ElOption,
  ElPagination,
  ElPopconfirm,
  ElProgress,
  ElRadioButton,
  ElRadioGroup,
  ElSelect,
  ElSkeleton,
  ElSwitch,
  ElTable,
  ElTableColumn,
  ElTabPane,
  ElTabs,
  ElTag,
  ElUpload,
]

elementPlusComponents.forEach(component => {
  app.use(component)
})
app.use(ElLoading)
provideGlobalConfig({ locale: zhCn }, app, true)
app.component('Loading', Loading)
```

### Task 3：验证与记录

**Files:**
- Modify: `docs/superpowers/project-map.md`

- [ ] **Step 1：运行静态测试**

Run:

```bash
cd frontend
node ./tests/element-plus-whitelist-static.test.mjs
node ./tests/vendor-chunk-splitting-static.test.mjs
node ./tests/chunk-optimization-static.test.mjs
```

- [ ] **Step 2：运行完整构建**

Run:

```bash
cd frontend
npm.cmd run build
```

- [ ] **Step 3：更新修改记录**

记录 Element Plus 白名单注册、构建结果和服务器部署影响。
