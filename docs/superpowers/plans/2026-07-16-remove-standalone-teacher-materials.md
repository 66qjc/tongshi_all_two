# 移除教师端独立「资料管理」页面实施计划

> **面向执行代理：** 必须按复选框逐项执行；开始编码前使用 `test-driven-development`，分任务执行时使用 `subagent-driven-development` 或 `executing-plans`，完成前使用 `verification-before-completion`。本文件仅是实施计划，当前未授权修改业务代码。

**目标：** 删除已无产品入口的 `TeacherMaterials.vue`、`/teacher/materials` 兼容路由和前端死代码，将「管理课程 -> 课程详情 -> 资料」固化为教师维护课程资料的唯一入口。

**架构：** 本次是纯前端退役清理。课程列表负责选择课程，`TeacherCourseDetail.vue` 继续负责阶段、资料上传、编辑、删除、预览和预览重建；后端资料路由、服务、模型和数据保持不变。旧 `/teacher/materials` 不再兼容跳转，交由现有全局未匹配路由展示 404。

**技术栈：** Vue 3、TypeScript、Vue Router、Vite、Element Plus、Node.js 静态回归测试。

**计划状态：** 路由决策已由用户确认；等待用户明确说“执行计划”或“开始写代码”后实施。

---

## 一、问题与已核实现状

### 1. 产品入口已经迁移

- 教师端左侧导航没有“资料管理”按钮，主入口是“管理课程”。
- 教师工作台“管理课程”和课程列表操作都会进入 `/teacher/courses` 或 `/teacher/courses/:courseId`。
- `TeacherCourseDetail.vue` 已覆盖阶段管理、PDF/视频上传、标题/阶段编辑、删除确认、资料预览和预览重建。
- `docs/superpowers/project-map.md` 与 `frontend-guidelines.md` 已将资料维护归入课程详情。

### 2. 独立页面只剩死代码

- `frontend/src/views/teacher/TeacherMaterials.vue` 没有被任何 Router 挂载。
- `/teacher/materials` 目前只是 `/teacher/courses` 的兼容 redirect。
- 用户已确认：既然前端没有对应按钮，就删除这条旧路由，不保留旧书签兼容。
- 删除 redirect 后，`/teacher/materials` 会命中现有 `/:pathMatch(.*)*`，显示 `NotFoundView.vue` 的“页面未找到”。

### 3. 旧页独有能力不迁移

独立页还保留跨课程筛选、关键词搜索和服务端分页。这些能力服务于“跨课程资料总表”，与课程详情的单课程管理边界不同。本次随独立页一起退役，不在课程详情重新实现，也不新增另一个跨课程资料入口。

### 4. 残留引用已经定位

- `getAllMaterials` 只被 `TeacherMaterials.vue` 调用；删除页面后可同步删除此前端 API 导出和未再使用的 `PaginatedResult` 类型导入。
- 后端 `GET /api/materials` 不删除。它是现有正式资料 API，且本计划不调整后端接口契约。
- 五份前端静态测试仍直接读取 `TeacherMaterials.vue`，必须按“等价迁移”或“删除旧页专属断言”处理，不能只删页面后放任测试报错。

## 二、已确定决策

1. **删除页面文件。** 仓库不再保留 `TeacherMaterials.vue`。
2. **删除兼容路由。** 从教师子路由中完整删除 `path: 'materials'`，不保留 redirect、别名或隐藏路由。
3. **旧地址进入 404。** 不新增针对 `/teacher/materials` 的特殊导航守卫或提示页。
4. **课程详情是唯一入口。** 教师先进入“管理课程”，再选择或直达一门课程维护资料。
5. **跨课程资料总表退役。** 不把跨课程搜索、筛选和分页迁入课程列表或课程详情。
6. **前端死导出删除。** 删除无人调用的 `getAllMaterials`；其他资料 API 客户端全部保留。
7. **后端接口保持不变。** 不删除 `GET /api/materials`，不修改 Routes、Services、Schemas、Models 或数据库。
8. **测试覆盖迁到真实入口。** 仍适用于课程详情的预览、安全和文案断言迁移到 `TeacherCourseDetail.vue`；只属于旧跨课程页面的布局、筛选和空状态断言直接删除。
9. **不重构课程详情。** 本计划只保护并验证既有资料能力，不借机调整资料 UI、阶段结构或上传流程。

## 三、范围边界

### 本轮包含

- 删除 `TeacherMaterials.vue`。
- 删除 `/teacher/materials` 教师子路由及其过时注释。
- 删除前端 `getAllMaterials` 导出和随之无用的类型导入。
- 清理所有有效源码中的 `TeacherMaterials`、`/teacher/materials` 残留；当前测试中仅允许新退役契约测试以反向断言形式引用这些字符串。
- 将五份静态测试改挂到课程详情或删除旧页专属断言。
- 新增独立页面退役契约测试。
- 更新当前稳定文档和项目修改记录。
- 验证课程详情资料管理、学生资料阅读和管理员公共资料管理未回退。

### 本轮不包含

- 不删除或修改后端 `GET /api/materials`、`POST /api/materials`、`PUT/DELETE /api/materials/{id}` 等接口。
- 不修改 `material_service.py`、`entities.py`、Pydantic Schema、数据库表或历史资料数据。
- 不删除 `createMaterial`、`updateMaterial`、`deleteMaterial`、`getCourseContents`、`rebuildMaterialPreview`、`getMaterialFileUrl`。
- 不修改 `MaterialRichCard`、`MaterialPreviewDialog`、`MaterialInlineReader` 的行为。
- 不改变课程详情中的阶段、资料上传、编辑、删除、预览和重建流程。
- 不新增跨课程资料搜索、筛选、分页或批量操作。
- 不调整学生端 `/learn` 资料直读和管理员公共课程资料管理。
- 不实施 `2026-07-16-remove-course-lessons.md` 中的课时拆除；两份计划可独立执行。
- 不改 Nginx、环境变量、Redis、文件存储或部署脚本。
- 不改写历史计划和审查报告中的原始记录；历史文档出现 `TeacherMaterials.vue` 属于历史事实。

## 四、退役后的产品与路由契约

### 教师资料管理主路径

```text
教师侧栏/工作台“管理课程”
  -> /teacher/courses 或最近管理的 /teacher/courses/:courseId
  -> 课程列表选择“管理课程”
  -> /teacher/courses/:courseId
  -> 课程详情“资料”区域
```

### 旧路径行为

| 场景 | 实施后行为 |
|---|---|
| 教师点击导航或按钮 | 只会进入 `/teacher/courses*`，不会生成 `/teacher/materials` |
| 直接访问 `/teacher/materials` | 命中全局未匹配路由，显示 404 |
| 访问 `/teacher/courses` | 正常展示课程列表 |
| 访问 `/teacher/courses/:courseId` | 正常管理该课程的阶段和资料 |

路由测试必须同时证明：`path: 'materials'` 已不存在，且全局 `/:pathMatch(.*)*` 仍存在。不能通过新增另一个 redirect 来让测试通过。

## 五、能力保留矩阵

| 能力 | 原独立页 | 课程详情 | 本次处理 |
|---|---:|---:|---|
| 按课程进入资料管理 | 支持课程下拉 | 由 URL 中 `courseId` 确定 | 保留课程详情方式 |
| PDF/视频上传 | 有 | 有 | 以课程详情为准 |
| 编辑标题 | 无独立编辑流程 | 有 | 保留课程详情能力 |
| 调整所属阶段 | 无 | 有 | 保留课程详情能力 |
| 删除及危险操作确认 | 有 | 有 | 测试迁到课程详情 |
| 站内预览 | 有 | 有 | 测试迁到课程详情 |
| 预览重建 | 有 | 有 | 测试迁到课程详情 |
| 阶段新增、改名、排序、删除 | 无 | 有 | 保留课程详情能力 |
| 跨课程资料总表 | 有 | 无 | 随旧页退役 |
| 关键词搜索和分页 | 有 | 无 | 随旧页退役，不迁移 |

## 六、文件变更清单

### 删除

- `frontend/src/views/teacher/TeacherMaterials.vue`

### 新增

- `frontend/tests/teacher-materials-retirement-static.test.mjs`

### 修改

- `frontend/src/router/index.ts`
- `frontend/src/api/material.ts`
- `frontend/tests/material-preview-static.test.mjs`
- `frontend/tests/local-file-preview-static.test.mjs`
- `frontend/tests/protected-file-consumers-static.test.mjs`
- `frontend/tests/mobile-admin-layout-static.test.mjs`
- `frontend/tests/copy-consistency-static.test.mjs`
- `docs/superpowers/project-map.md`
- `docs/superpowers/frontend-guidelines.md`
- `AGENTS.md`
- `backend/docs/项目修改记录.md`

### 只读核对，不应因本计划修改

- `frontend/src/views/teacher/TeacherCourseDetail.vue`
- `frontend/src/views/teacher/TeacherCourses.vue`
- `frontend/src/views/teacher/TeacherDashboard.vue`
- `frontend/src/views/teacher/TeacherLayout.vue`
- `frontend/src/views/NotFoundView.vue`
- `backend/app/api/v1/routes/material_routes.py`
- `backend/app/services/material_service.py`
- `backend/app/models/entities.py`

`TeacherLayout.vue` 当前已有“管理课程直达最近课程详情”的未提交改动，且已没有旧资料页迁移注释。本计划只读核对该页面，不修改其动态路径、最近课程记忆、侧栏顺序或高亮逻辑。

## 七、测试迁移规则

### 1. `material-preview-static.test.mjs`

- 删除 `TeacherMaterials.vue` 的读取。
- 删除旧页 `MaterialRichCard` 和 `rebuildMaterialPreview` 断言。
- 保留并强化现有 `TeacherCourseDetail.vue` 断言：`MaterialRichCard`、`compact`、`material-flat-list`、`MaterialPreviewDialog`、`rebuildMaterialPreview` 均存在。

### 2. `local-file-preview-static.test.mjs`

- 删除旧页读取。
- 将“教师资料管理应通过站内预览弹窗打开”改为断言 `TeacherCourseDetail.vue` 使用 `MaterialPreviewDialog`。
- 其他 PDF、学生课程详情、管理员公共资料和作品报告断言不变。

### 3. `protected-file-consumers-static.test.mjs`

- 删除旧页读取及其两个反向断言。
- 保留课程详情不得调用 `resolveFileUrl`、不得重新出现 `materialUrl()` / `openMaterial()` 的安全契约。
- 其他受保护文件消费者断言不变。

### 4. `mobile-admin-layout-static.test.mjs`

- 删除仅针对已退役 `TeacherMaterials.vue` 网格最小宽度的断言。
- 不把旧页的 `360px` 网格契约机械迁到课程详情；课程详情当前使用紧凑扁平列表，移动端验收由浏览器流程覆盖。
- 保留教师 Layout、管理员公共课程、管理员内容管理和成长档案的既有窄屏断言。

### 5. `copy-consistency-static.test.mjs`

- 删除旧页读取和“所选课程”专属空状态断言。
- 保留课程详情删除资料必须说明“本课程副本中的资料”和“不影响公共课程源内容”。
- 补充课程详情存在“上传新资料”和“暂无资料”的断言，确认空状态旁有明确可执行入口。

## 八、实施任务

### Task 1：先建立独立页面退役契约

**文件：**

- 新增：`frontend/tests/teacher-materials-retirement-static.test.mjs`

- [ ] **Step 1：编写失败的退役静态测试**

```javascript
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = relativePath => readFileSync(resolve(root, relativePath), 'utf8')

assert.equal(
  existsSync(resolve(root, 'src/views/teacher/TeacherMaterials.vue')),
  false,
  '独立教师资料管理页面应已删除',
)

const router = read('src/router/index.ts')
assert.doesNotMatch(
  router,
  /path:\s*['"]materials['"]|teacher-materials|TeacherMaterials/,
  '教师子路由不得保留独立资料页、redirect 或组件引用',
)
assert.match(router, /path:\s*['"]\/:pathMatch\(\.\*\)\*['"]/, '全局 404 路由必须保留')

const layout = read('src/views/teacher/TeacherLayout.vue')
const dashboard = read('src/views/teacher/TeacherDashboard.vue')
assert.doesNotMatch(layout, /\/teacher\/materials|资料管理/, '教师侧栏不得生成旧资料地址')
assert.doesNotMatch(dashboard, /\/teacher\/materials/, '教师工作台不得生成旧资料地址')

const materialApi = read('src/api/material.ts')
assert.doesNotMatch(materialApi, /getAllMaterials|PaginatedResult/, '前端应删除旧页专用分页 API')
assert.match(materialApi, /getCourseContents/, '课程详情资料列表 API 必须保留')
assert.match(materialApi, /createMaterial/, '课程详情上传资料 API 必须保留')
assert.match(materialApi, /updateMaterial/, '课程详情编辑资料 API 必须保留')
assert.match(materialApi, /deleteMaterial/, '课程详情删除资料 API 必须保留')
assert.match(materialApi, /rebuildMaterialPreview/, '课程详情预览重建 API 必须保留')

const courseDetail = read('src/views/teacher/TeacherCourseDetail.vue')
for (const pattern of [
  /MaterialRichCard/,
  /MaterialPreviewDialog/,
  /openUploadMaterial/,
  /handleSaveMaterial/,
  /handleDeleteMaterial/,
  /handleRebuildPreview/,
]) {
  assert.match(courseDetail, pattern, '课程详情必须继续承接资料管理能力')
}

console.log('独立教师资料管理页面退役检查通过')
```

- [ ] **Step 2：运行测试并确认旧页面仍在时失败**

工作目录：`frontend`

```powershell
node tests/teacher-materials-retirement-static.test.mjs
```

预期：因 `TeacherMaterials.vue`、`path: 'materials'` 或 `getAllMaterials` 仍存在而失败。

### Task 2：删除页面、旧路由与前端死 API

**文件：**

- 删除：`frontend/src/views/teacher/TeacherMaterials.vue`
- 修改：`frontend/src/router/index.ts`
- 修改：`frontend/src/api/material.ts`

- [ ] **Step 1：删除独立页面文件**

只删除 `TeacherMaterials.vue`，不得删除同目录其他教师页面或通用资料组件。

- [ ] **Step 2：删除教师子路由**

从 `router/index.ts` 完整删除以下路由对象及兼容说明：

```typescript
{
  path: 'materials',
  redirect: '/teacher/courses',
},
```

不得新增同名 route、alias、导航守卫或其他 redirect。

- [ ] **Step 3：删除前端 `getAllMaterials`**

从 `material.ts` 删除 `getAllMaterials` 函数和只为它存在的 `PaginatedResult` 导入。保留 `Material`、`MaterialPreview`、`getCourseContents` 和全部资料写入/预览方法。

- [ ] **Step 4：核对教师导航未产生旧地址**

只读检查 `TeacherLayout.vue` 与 `TeacherDashboard.vue`：两者不得生成 `/teacher/materials`。不要修改当前动态“管理课程”路径、最近课程记忆、侧栏顺序或高亮逻辑。

- [ ] **Step 5：运行退役测试**

工作目录：`frontend`

```powershell
node tests/teacher-materials-retirement-static.test.mjs
```

预期：通过。

### Task 3：迁移预览与文件安全测试

**文件：**

- 修改：`frontend/tests/material-preview-static.test.mjs`
- 修改：`frontend/tests/local-file-preview-static.test.mjs`
- 修改：`frontend/tests/protected-file-consumers-static.test.mjs`

- [ ] **Step 1：迁移资料预览断言**

按本计划“测试迁移规则”删除 `teacherMaterials` 变量，把预览、重建和图文卡片契约统一锚定到 `teacherCourseDetail`。不得删除学生直读、短时签名 URL、续签去重和 PDF/视频降级断言。

- [ ] **Step 2：迁移本地预览断言**

把教师资料的 `MaterialPreviewDialog` 正向断言改为课程详情；其他文件消费者保持不变。

- [ ] **Step 3：收敛受保护文件消费者断言**

删除旧页变量和旧页反向断言，保留 `TeacherCourseDetail.vue` 的安全反向断言。

- [ ] **Step 4：运行三份定向测试**

工作目录：`frontend`

```powershell
node tests/material-preview-static.test.mjs
node tests/local-file-preview-static.test.mjs
node tests/protected-file-consumers-static.test.mjs
```

预期：全部通过，且没有测试尝试读取已删除页面。

### Task 4：迁移移动端和文案测试

**文件：**

- 修改：`frontend/tests/mobile-admin-layout-static.test.mjs`
- 修改：`frontend/tests/copy-consistency-static.test.mjs`

- [ ] **Step 1：删除旧页专属移动端断言**

删除 `TeacherMaterials.vue` 的 `360px` 网格断言；保留该测试中其他页面的既有断言。

- [ ] **Step 2：迁移危险操作与空状态文案断言**

删除旧页变量和三条旧页文案断言；课程详情必须继续满足：

```javascript
assert.match(teacherCourseDetail, /本课程副本中的资料/)
assert.match(teacherCourseDetail, /不影响公共课程源内容/)
assert.match(teacherCourseDetail, /上传新资料/)
assert.match(teacherCourseDetail, /description="暂无资料"/)
```

- [ ] **Step 3：运行两份定向测试**

工作目录：`frontend`

```powershell
node tests/mobile-admin-layout-static.test.mjs
node tests/copy-consistency-static.test.mjs
```

预期：全部通过。

### Task 5：全量前端与浏览器验收

- [ ] **Step 1：做有效代码残留扫描**

```powershell
$patterns = 'TeacherMaterials|/teacher/materials|teacher-materials|getAllMaterials'

Get-ChildItem frontend/src -Recurse -File -Include *.ts,*.vue |
  Select-String -Pattern $patterns

Get-ChildItem frontend/tests -Recurse -File -Include *.mjs |
  Where-Object { $_.Name -ne 'teacher-materials-retirement-static.test.mjs' } |
  Select-String -Pattern $patterns
```

预期：两段扫描均无命中。新退役契约测试允许以反向断言引用这些字符串；历史 Markdown 文档不纳入“有效代码”扫描。

- [ ] **Step 2：运行全部前端静态测试**

工作目录：`frontend`

```powershell
Get-ChildItem tests -Filter *.test.mjs | ForEach-Object {
  node $_.FullName
  if ($LASTEXITCODE -ne 0) { throw "静态测试失败：$($_.Name)" }
}
```

预期：所有现存 `.test.mjs` 通过。

- [ ] **Step 3：运行类型检查与生产构建**

工作目录：`frontend`

```powershell
npm run type-check
npm run build
```

预期：类型检查和构建成功，没有 `TeacherMaterials.vue` 解析或动态导入错误。

- [ ] **Step 4：浏览器验收教师资料主流程**

至少覆盖桌面和 390px 移动视口：

- 教师侧栏无“资料管理”入口。
- 教师工作台和侧栏“管理课程”进入课程列表或课程详情。
- 课程列表“管理课程”可进入 `/teacher/courses/:courseId`。
- 课程详情可新增阶段、上传 PDF/视频、编辑标题与阶段、预览、重建预览、删除资料。
- 删除资料弹窗说明仅影响本课程副本、不影响公共课程源；取消不会删除。
- 无资料课程显示中文空状态，并有“上传新资料”入口。
- `/teacher/materials` 显示现有 404，不自动跳转。
- 教师课程详情窄屏无横向溢出、按钮重叠或乱码。

- [ ] **Step 5：回归相关非教师流程**

在可用测试数据上至少完成以下浏览器检查；若本地没有对应角色或资料数据，必须在总结中逐项记录未验证原因：

- 游客或学生打开 `/learn/course/{公开课程ID}?tab=materials`，能选择并打开一份公开 PDF、视频或链接资料。
- 管理员打开 `/admin/public-courses`，公共课程资料列表和预览入口能够加载。
- 浏览器控制台没有因为删除 `TeacherMaterials.vue`、`getAllMaterials` 或通用资料组件而产生动态导入/模块解析错误。

### Task 6：同步稳定文档、修改记录与知识图谱

**文件：**

- 修改：`docs/superpowers/project-map.md`
- 修改：`docs/superpowers/frontend-guidelines.md`
- 修改：`AGENTS.md`
- 修改：`backend/docs/项目修改记录.md`

- [ ] **Step 1：更新项目地图**

从当前教师端页面清单删除 `/teacher/materials` 兼容跳转条目，明确教师资料维护唯一入口为 `/teacher/courses/:courseId`。历史修改记录中的 `TeacherMaterials.vue` 原始事实保留，不做全文件机械替换。

- [ ] **Step 2：更新前端验收规范**

将“不再出现独立资料管理导航入口”收敛为“不再保留独立页面、路由或导航入口”；明确旧 `/teacher/materials` 返回 404，课程详情资料区继续覆盖上传、编辑、删除、预览和重建。

- [ ] **Step 3：写入项目修改记录**

记录删除页面、删除路由、退役跨课程资料总表、保留课程详情能力、验证结果和服务器部署影响。不得写成后端资料接口已删除。

- [ ] **Step 4：更新项目当前状态**

在 `AGENTS.md` 的“项目完成状态”新增本任务完成项，并把长期约定从“不再出现独立资料管理导航入口”收敛为“独立页面和路由均已删除，资料在课程详情维护”。不得改动与本任务无关的治理优先级和待实施计划。

- [ ] **Step 5：更新知识图谱**

工作目录：项目根目录。

```powershell
graphify update .
```

若本机 `graphify` 不可用，如实记录失败原因；不得声称图谱已更新，也不得因此跳过前端验证。

- [ ] **Step 6：最终差异检查**

```powershell
git status --short
git diff --check
git diff -- frontend/src/router/index.ts frontend/src/api/material.ts frontend/tests
```

当前工作区已有多个未提交修改，尤其包括 `router/index.ts`、`TeacherCourseDetail.vue`、`TeacherLayout.vue`、`material-preview-static.test.mjs`、`project-map.md` 和 `frontend-guidelines.md`。实施时必须逐文件核对和合并，不回滚、不覆盖用户已有改动，也不使用 `git add frontend` 等宽范围暂存命令。

## 九、验收标准

1. `frontend/src/views/teacher/TeacherMaterials.vue` 不存在。
2. 教师子路由中不存在 `path: 'materials'`、`teacher-materials`、`TeacherMaterials` 或对应 redirect。
3. `/teacher/materials` 显示现有 404，不跳转到课程列表或其他页面。
4. 教师侧栏、工作台和课程列表只生成 `/teacher/courses*` 资料管理路径。
5. 前端不存在 `getAllMaterials` 和随之无用的 `PaginatedResult` 导入。
6. 后端 `GET /api/materials` 及其他资料接口保持原样，数据库和历史资料不变。
7. 课程详情继续支持阶段管理、PDF/视频上传、编辑、删除确认、站内预览和预览重建。
8. 跨课程资料搜索、筛选和分页不再作为产品能力出现，也未被偷偷迁入其他页面。
9. 五份既有静态测试完成等价迁移或删除旧页专属断言，新退役测试通过。
10. 所有前端静态测试、`npm run type-check` 和 `npm run build` 通过。
11. 桌面和 390px 教师资料主流程可用，无横向溢出、按钮重叠、空白页或中文乱码。
12. `project-map.md`、`frontend-guidelines.md`、`AGENTS.md`、项目修改记录、服务器部署影响和知识图谱结果已同步或如实记录未完成原因。

## 十、风险与缓解

| 风险 | 影响 | 缓解与验收 |
|---|---|---|
| 误删后端 `/api/materials` | 学生、教师和管理员资料流程受损 | 后端文件列为只读；退役测试只要求删除前端 `getAllMaterials` |
| 误删课程详情资料能力 | 教师无法上传或维护资料 | 能力保留矩阵 + 课程详情正向静态断言 + 浏览器完整流程 |
| 把跨课程总表悄悄迁回其他页面 | 重复页面问题重新出现 | 明确将搜索/筛选/分页列为退役能力，验收禁止新增入口 |
| 测试只删除不迁移 | 资料预览和文件安全覆盖下降 | 按五份测试逐条标明迁移与删除规则 |
| 删除 redirect 后旧书签 404 | 旧地址不再可用 | 这是用户已确认行为；依赖现有 404 页面，不新增兼容逻辑 |
| 与课时拆除计划修改同一测试 | 合并时断言冲突或丢失 | 两份计划独立分步实施；每完成一份都重跑全部静态测试 |
| 覆盖工作区现有修改 | 丢失用户正在进行的导航/紧凑资料列表改动 | 实施前后检查 Git 差异，逐文件合并，禁止回滚和宽范围暂存 |
| 历史文档仍出现旧页名称 | 残留扫描看似不为零 | 有效代码/当前规范与历史记录分开扫描，历史事实不机械改写 |

## 十一、回滚方案

本次不改后端和数据库。需要回滚时必须作为同一组恢复：

1. 恢复 `TeacherMaterials.vue`。
2. 恢复 `/teacher/materials` 组件路由或此前兼容 redirect。
3. 恢复前端 `getAllMaterials` 导出和测试锚点。
4. 重新构建并部署前端静态资源。

由于后端 `GET /api/materials` 始终保留，不需要恢复后端代码、数据库数据或执行迁移。

## 十二、服务器部署影响

本计划文档本身的完善**不需要服务器修改**。将来执行代码计划并上线时：

- **需要服务器拉取前端代码。**
- **需要重新构建并部署前端静态资源。**
- **不需要重启后端服务。**
- **不需要数据库迁移、清表或数据回填。**
- **不需要修改环境变量、Nginx、Redis 或文件存储配置。**
- 本次不增删 npm 依赖，锁文件不应变化；服务器按既有前端构建流程执行即可。
- 部署后必须强制刷新一次并验证 `/teacher/materials` 为 404、`/teacher/courses/:courseId` 资料管理正常。
