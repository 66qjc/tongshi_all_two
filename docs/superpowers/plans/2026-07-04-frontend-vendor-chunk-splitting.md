# 前端 Vendor 分包优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 在第一阶段重依赖懒加载基础上，继续降低入口 `index` chunk 的体积和变更频率，让稳定第三方依赖进入独立可缓存 chunk。

**架构：** 使用 Vite 8 底层 Rolldown 的 `build.rolldownOptions.output.codeSplitting.groups`，只对首屏必然使用的 Vue、Element Plus 和 HTTP 基础依赖做命名分包。不使用宽泛 `node_modules` 总包，避免把已经异步加载的 wangeditor、ECharts、PDF 预览库重新合并到首屏依赖里。

**技术栈：** Vue 3、Vite 8、Rolldown code splitting、Node 静态断言测试。

---

## 范围

### 本轮做

1. 新增 `frontend/tests/vendor-chunk-splitting-static.test.mjs`，静态检查 Vite/Rolldown 分包配置。
2. 修改 `frontend/vite.config.ts`，新增 `build.rolldownOptions.output.codeSplitting.groups`。
3. 运行 `node ./tests/vendor-chunk-splitting-static.test.mjs` 和 `npm run build`，记录构建产物变化。
4. 更新 `docs/superpowers/project-map.md`，说明服务器部署影响。

### 本轮不做

1. 不改变业务代码、路由、接口、上传流程和页面 UI。
2. 不做宽泛 `node_modules` vendor 总包。
3. 不把 wangeditor、ECharts、vue-pdf-embed 纳入首屏 vendor。
4. 不在本步骤手动改全站 Element Plus 组件白名单；如构建结果显示它仍是入口主要成本，再作为第三阶段处理。

## 验收标准

1. 新增静态测试在修改前失败，失败原因指向缺少 `codeSplitting` 分包配置。
2. 修改后静态测试通过。
3. `npm run build` 通过。
4. 构建产物中出现 `vendor-vue-*`、`vendor-element-plus-*`、`vendor-http-*` 或等价命名 chunk。
5. 构建产物中 `index` JS 主文件继续低于第一阶段后的约 1,063.84 kB。
6. 修改记录写明服务器需要重新构建并部署前端静态资源，不需要后端重启和数据库迁移。

## 任务

### Task 1：静态分包测试

**Files:**
- Create: `frontend/tests/vendor-chunk-splitting-static.test.mjs`

- [ ] **Step 1：写失败测试**

测试读取 `frontend/vite.config.ts`，断言：

```js
assert.match(viteConfig, /rolldownOptions\s*:/, 'Vite 构建应显式配置 Rolldown 分包')
assert.match(viteConfig, /codeSplitting\s*:/, 'Rolldown 输出应使用 codeSplitting.groups')
assert.match(viteConfig, /name:\s*['"]vendor-vue['"]/, 'Vue 基础依赖应进入 vendor-vue chunk')
assert.match(viteConfig, /name:\s*['"]vendor-element-plus['"]/, 'Element Plus 应进入独立 vendor chunk')
assert.match(viteConfig, /name:\s*['"]vendor-http['"]/, 'HTTP 基础依赖应进入独立 vendor chunk')
assert.doesNotMatch(viteConfig, /test:\s*\/node_modules\/?/, '禁止使用宽泛 node_modules 总包，避免吞掉异步重依赖')
```

- [ ] **Step 2：运行测试确认失败**

Run:

```bash
cd frontend
node ./tests/vendor-chunk-splitting-static.test.mjs
```

Expected: FAIL，提示缺少 Rolldown 分包配置。

### Task 2：配置 Rolldown 分包

**Files:**
- Modify: `frontend/vite.config.ts`

- [ ] **Step 1：新增 build 配置**

在 `defineConfig` 根对象中新增：

```ts
  build: {
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            {
              name: 'vendor-vue',
              test: /node_modules[\\/](vue|vue-router|pinia|@vue)[\\/]/,
              priority: 30,
            },
            {
              name: 'vendor-element-plus',
              test: /node_modules[\\/](element-plus|@element-plus)[\\/]/,
              priority: 20,
            },
            {
              name: 'vendor-http',
              test: /node_modules[\\/]axios[\\/]/,
              priority: 10,
            },
          ],
        },
      },
    },
  },
```

### Task 3：验证与记录

**Files:**
- Modify: `docs/superpowers/project-map.md`

- [ ] **Step 1：运行静态测试**

Run:

```bash
cd frontend
node ./tests/vendor-chunk-splitting-static.test.mjs
```

Expected: 输出 `vendor-chunk-splitting-static: 所有断言通过`。

- [ ] **Step 2：运行完整构建**

Run:

```bash
cd frontend
npm run build
```

Expected: type-check 和 Vite build 均通过。允许异步富文本编辑器等 chunk 仍超过 500 kB，但入口 chunk 应被拆小。

- [ ] **Step 3：更新修改记录**

记录第二阶段分包策略、构建结果和服务器部署影响。

## 风险

1. 宽泛 vendor 总包会吞掉异步重依赖。
   - 处理：只配置命名基础依赖组，并用静态测试禁止宽泛 `node_modules` 规则。
2. 分包会增加首屏请求数。
   - 处理：只拆稳定第三方依赖，换取浏览器长期缓存和业务入口 chunk 降低。
3. 分包不能减少全量 Element Plus 本身的执行成本。
   - 处理：本阶段完成后根据构建结果决定是否进入 Element Plus 白名单注册阶段。
