# 课程资料页直读式文档站调研与设计方向

## 背景

用户希望 `/learn/course/:courseId?tab=materials` 的资料展示接近 `https://book.guyuehome.com/` 这类学习文档站，而不是现在的资料卡片列表、预览按钮、弹窗式 PDF 查看。用户同时要求先做完整调研，不只参考一个网站。

本调研只做方向、边界和验收定义，不修改业务代码。

## 外部调研

### 古月居图书资源

- 地址：`https://book.guyuehome.com/`
- 观察截图：`output/webtest/research/guyuehome-home.png`
- 技术特征：页面 HTML 中可见 `mkdocs`、`material`、`md-header`、`md-sidebar`、`md-content`、`md-search`、`md-nav` 等结构，属于 Material for MkDocs 风格。
- 体验结构：顶部栏包含站点名、搜索和仓库入口；左侧是课程/章节目录树；中间是文档正文；右侧是本页目录。用户进入页面后看到的是可读内容本身，不是附件卡片。

可借鉴点：

1. 资料即正文，页面主体是阅读，不是资源管理。
2. 左侧目录负责切换章节或资料，不承担卡片展示。
3. 右侧目录只围绕当前正文，不展示大量统计。
4. 搜索和即时导航让用户觉得内容是一个“书站”，不是文件列表。

### Material for MkDocs

官方文档强调清晰导航是项目文档的重要部分，提供 navigation tabs、sections、instant loading、anchor tracking、table of contents 等能力。其“instant loading”会拦截内部链接并通过 XHR 注入页面，让搜索索引和导航状态在站内切换时保持连续。

对本项目的启发：

1. 不需要迁移到 MkDocs，但应学习其三层导航心智：站点/课程导航、章节树、当前页目录。
2. “实时更新”不应理解为重新加载整页，而应是资料切换、预览状态、目录高亮在当前页面内即时响应。
3. 如果后续资料很多，左侧目录要支持折叠、当前项高亮和轻量搜索。

参考：

- `https://squidfunk.github.io/mkdocs-material/setup/setting-up-navigation/`
- `https://squidfunk.github.io/mkdocs-material/setup/setting-up-site-search/`

### Docusaurus

Docusaurus 的 sidebar 用于把多个相关文档组织为有序树，并在这些文档之间提供共同侧边栏和上一篇/下一篇导航。

对本项目的启发：

1. 课程阶段应像 sidebar category，不只是“阶段 1 / 其他”的标签。
2. 每份资料应像 doc link，点击后中间阅读区切换到该资料。
3. 可以保留前后资料切换，降低学生在多个 PDF 之间来回找的成本。

参考：`https://docusaurus.io/docs/sidebar`

### VitePress

VitePress 默认主题把 sidebar 定义为文档主导航块，支持分组、嵌套、多侧边栏和折叠分组。页面同时有搜索入口和右侧 on this page 区域。

对本项目的启发：

1. 左侧目录应稳定、层级清楚，最多两层：阶段 -> 资料。
2. 移动端不应硬保留三栏，而应转为“当前资料栏 + 横向目录 + 阅读器 + 导读”。
3. 搜索入口可以后置，但目录结构要为搜索预留数据形态。

参考：`https://vitepress.dev/reference/default-theme-sidebar`

### GitBook、Mintlify、Nextra

GitBook 的页面组织围绕左侧 table of contents；Mintlify 通过 groups、pages、dropdowns、tabs、anchors 组织文档导航；Nextra Docs Theme 默认包含顶部导航、搜索、页面侧边栏和目录。

共同结论：

1. 学习网站不是文件仓库，核心是“页面/章节”。
2. 左侧目录用于组织内容，右侧目录用于理解当前页。
3. 搜索是长期必要能力，但第一阶段可以先完成目录切换和直读。
4. 页面要围绕当前阅读对象收敛，不要同时塞入统计卡、资源中心、资料瀑布流。

参考：

- `https://gitbook.com/docs/creating-content/content-structure/page`
- `https://www.mintlify.com/docs/organize/navigation`
- `https://nextra.site/docs/docs-theme/start`

## 本项目现状

当前主要文件：

- `frontend/src/views/CourseDetailView.vue`
- `frontend/src/components/common/MaterialRichCard.vue`
- `frontend/src/components/common/MaterialPreviewDialog.vue`
- `frontend/src/api/publicLearning.ts`
- `frontend/src/api/material.ts`

当前 `/learn/course/:courseId?tab=materials` 已经有三栏：

1. 左侧 `materials-sidebar`：资料目录，按阶段展示。
2. 中间 `materials-reader`：实际是阶段资料卡片流。
3. 右侧 `materials-rail`：资料统计和快速打开。

但它仍然不是目标体验：

1. 中间区域没有直接显示 PDF、视频或链接正文。
2. 每份资料仍通过 `MaterialRichCard` 展示为卡片。
3. 点击资料会调用 `previewMaterial`，打开 `MaterialPreviewDialog`。
4. PDF 和视频被放在弹窗里，不是页面主阅读区。
5. 链接资料只能提示“不支持站内预览”，再从新窗口打开。
6. 右侧快速打开也只是触发弹窗。

本地对比截图：

- 当前本项目资料页：`output/webtest/research/local-course-materials.png`
- 目标站截图：`output/webtest/research/guyuehome-home.png`

## 根因判断

当前页面把“资料”当成资源条目，而不是学习页面。虽然布局上已有三栏，但信息架构仍是资料库：

- 左侧是阶段跳转，不是资料切换。
- 中间是资料卡片，不是当前资料正文。
- 右侧是统计和快捷入口，不是当前资料导读。
- 预览弹窗是主阅读入口，不是备用入口。

因此仅继续美化卡片、加封面、加统计，无法满足用户目标。必须把资料页从“资料库”改为“直读式文档站”。

## 推荐方向

推荐采用“课程资料直读器”方案：

1. 左侧：阶段化资料目录。
2. 中间：当前资料阅读器。
3. 右侧：当前资料导读。

### 左侧：阶段化资料目录

结构：

- 课程名简短标题。
- 阶段分组，例如“阶段 1 公开学习资料”。
- 每个阶段下列出资料标题、类型、页数或时长。
- 当前资料高亮。
- 点击资料后只切换中间阅读区，不弹窗，不跳页。

交互：

- 默认展开所有有资料的阶段。
- 资料多时支持阶段折叠。
- 第一阶段暂不做全文搜索，但保留顶部小搜索框位置。

### 中间：当前资料阅读器

默认选中逻辑：

1. 优先选中第一份 PDF。
2. 没有 PDF 时选中第一份视频。
3. 没有视频时选中第一份链接。
4. 没有资料时显示清晰空状态。

PDF：

- 在页面中间直接使用 `<object>` 或 `<iframe>` 嵌入。
- 文件 URL 继续复用现有公开资料接口：`getPublicMaterialFileUrl(material.id)`。
- 认证态资料继续复用现有资料文件接口。
- 提供“新窗口打开”和“下载/打开原文件”作为备用，不作为主流程。
- 浏览器不支持内嵌 PDF 时，显示中文降级提示。

视频：

- 在同一个阅读区域中使用 `<video controls>`。
- 不打开弹窗。

链接：

- 不默认 iframe 外部网站，避免跨站限制和安全问题。
- 使用站内链接落地页样式：标题、摘要、来源、打开按钮。

### 右侧：当前资料导读

只展示当前资料相关信息：

- 资料摘要。
- 类型、页数、时长、大小、更新时间。
- 阅读建议，例如“先看第 1-2 页了解概念，再完成课堂讨论”。
- 相邻资料：上一份、下一份。
- 原文件操作：打开原文、下载。

不再展示：

- 全部资料统计卡。
- 前 8 个快速打开列表。
- 大面积资源中心。
- 多个资料卡片详情。

### 实时更新

第一阶段不引入 WebSocket，也不改后端。采用前端轻量刷新：

1. 页面进入资料 tab 时立即加载最新资料。
2. 当 `preview.status` 是 `pending` 或 `processing` 时，每 15-20 秒静默刷新一次课程资料数据。
3. 页面不可见时暂停刷新，回到页面时重新拉取。
4. 切换资料不刷新整页，只更新当前资料阅读区和右侧导读。

这能覆盖“预览生成中变成预览就绪”“教师刚更新资料后学生刷新可见”等基础需求。真正多人实时协同不是本阶段范围。

## 不推荐方向

### 不建议继续资料卡片流

原因：这只是资料管理视角，和学习网站的阅读心智相反。

### 不建议第一阶段把 PDF 全量转 Markdown

原因：需要后端抽取、版式还原、图片处理、目录生成、分页和质量校验，范围会明显扩大。第一阶段先用内嵌 PDF 直读达成主体验。

### 不建议迁移到 MkDocs / VitePress

原因：项目已经是 Vue 3 + FastAPI 的业务平台，资料有权限、上传、公开/认证两套访问链路。迁移静态文档站会破坏现有权限和后台流程。

## 改造边界

第一阶段建议只改前端：

- 主要修改：`frontend/src/views/CourseDetailView.vue`
- 可选新增：`frontend/src/components/learn/MaterialInlineReader.vue`
- 可选新增：`frontend/src/components/learn/MaterialDocToc.vue`
- 可选新增：`frontend/src/components/learn/MaterialGuideRail.vue`
- 测试更新：`frontend/tests/public-learning-static.test.mjs`

不做：

- 不改后端接口。
- 不改数据库结构。
- 不改上传流程。
- 不改教师端和管理员端资料管理页面。
- 不删除 `MaterialPreviewDialog`，教师端和管理端仍可能需要它。

## 验收标准

1. 打开 `/learn/course/:courseId?tab=materials` 后，中间直接显示第一份 PDF，不需要点击“预览”按钮。
2. 左侧目录按阶段列出资料，点击资料后中间阅读器同步切换。
3. PDF、视频、链接都进入同一个阅读框架。
4. 右侧只展示当前资料导读和相邻资料，不恢复资料统计卡或资源中心。
5. 弹窗预览不再是学生端资料页主路径，只作为备用。
6. 移动端阅读区仍是主区域，目录和导读不遮挡 PDF。
7. 公开资料继续走 `getPublicMaterialFileUrl(material.id)`。
8. 认证资料继续走现有资料文件接口。
9. `public-learning-static.test.mjs` 增加直读结构断言：`activeMaterial`、`selectMaterial`、`material-inline-reader`、`object` 或 `iframe`、PDF 降级提示。
10. 浏览器验收需要截图桌面端和移动端。

## 后续实施建议

建议先做一版最小但完整的直读体验：

1. 在 `CourseDetailView.vue` 增加 `activeMaterialId`、`activeMaterial`、`selectMaterial`、`materialFileUrl`。
2. 把资料 tab 中间区域从 `MaterialRichCard` 列表替换为当前资料阅读器。
3. 左侧目录从阶段跳转改为资料选择。
4. 右侧从统计卡改为当前资料导读。
5. 保留弹窗组件，但不在资料 tab 主流程使用。
6. 加静态测试，再用 Playwright 截图验收。

## 服务器部署影响

本调研文档本身不影响服务器，不需要拉代码、重启服务、重建前端、数据库迁移、环境变量修改或 Nginx 配置调整。

如果后续按本设计改正式前端页面，上线时需要服务器拉取前端代码并重新构建、部署前端静态资源；不需要后端重启，不需要数据库迁移，不需要环境变量或 Nginx 修改。
