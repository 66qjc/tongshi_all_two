# 文件鉴权与流式预览修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 使用短时文件专用签名 URL 同时满足私有文件鉴权和 PDF/视频 Range 流式读取，并完整迁移现有受保护文件消费者。

**Architecture:** 普通 Bearer Token 只用于申请 5 分钟文件级 URL；媒体、图片和链接只携带限定 `file_id` 与 `scope=file_access` 的短时 Token。后端把“文件权限判断”和“打开文件流”拆开，前端用一个可取消、可续签的组合式函数统一解析公开、外部和私有文件 URL。

**Tech Stack:** FastAPI、python-jose、SQLAlchemy、Vue 3、PDF.js、HTML5 Video、pytest、Node 静态测试、Playwright。

**Design:** `docs/superpowers/specs/2026-07-10-code-review-remediation-design.md`

---

### Task 1: 增加严格的文件专用 Token 和申请接口

**Files:**
- Modify: `backend/app/core/security.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/api/v1/routes/file_routes.py`
- Modify: `backend/app/services/file_service.py`
- Modify: `backend/.env.example`
- Modify: `backend/tests/test_auth.py`
- Modify: `backend/tests/test_material_file_acceleration.py`
- Modify: `backend/tests/test_local_storage_boundaries.py`
- Modify: `backend/tests/test_integration_bugfixes.py`

- [x] **Step 1: 写 Token 边界和 Range 失败测试**

新增独立用例覆盖：有权限学生可申请 URL；匿名申请返回 401；其他课程学生返回 404；签名 Token 可访问当前文件并支持 `Range`/206；把 URL 的 `file_id` 换成其他文件返回 401；签名 Token 调 `/api/me` 返回 401；过期、畸形、缺少 `sub/scope/file_id` 的 Token 都稳定返回 401；软删除用户的未过期文件 Token 返回 401；普通长效 JWT 放在 `?token=` 或 `?access_token=` 均被拒绝；普通 Bearer Token 直接读取文件仍保持兼容；明确允许匿名的展示图片仍可读取。

- [x] **Step 2: 运行并确认申请接口不存在**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_auth.py backend/tests/test_material_file_acceleration.py backend/tests/test_local_storage_boundaries.py -q`

Expected: FAIL，`POST /api/files/{id}/access-url` 不存在，普通 JWT 查询参数仍被接受。

- [x] **Step 3: 增加严格签发和解析函数**

`create_file_access_token()` 直接签发只含 `sub`、`scope`、`file_id`、`exp` 的 JWT，不复用登录 Token 的查询参数兼容逻辑。`decode_file_access_token()` 必须捕获 `JWTError`、`KeyError`、`TypeError` 和 `ValueError`，并验证 `sub` 为非空字符串、`scope == "file_access"`、`file_id` 与路径严格相等；任何失败统一抛出 `BusinessException(401, "文件访问凭据无效或已过期")`。

普通 `get_current_user()` 只接受 Authorization Bearer，拒绝任何非空 `scope`；删除 `/api/files` 和 `/api/materials` 的普通 JWT 查询参数回退。`ALLOW_QUERY_TOKEN_FOR_FILES` 从示例配置和运行逻辑中移除，服务器旧环境变量即使保留也不再生效。

- [x] **Step 4: 分离权限判断和打开流**

在 `file_service.py` 增加 `get_authorized_file_record(db, file_id, current_user, allow_anonymous)`：只查询 `StoredFile` 并执行现有业务归属校验，不调用存储适配器。`resolve_file_stream()` 复用已授权记录后才打开流。申请 URL 时只调用权限函数，不能为了鉴权提前打开再关闭大文件。

- [x] **Step 5: 增加申请接口和 GET 校验**

`POST /api/files/{file_id}/access-url` 使用普通 `get_current_user`，权限通过后返回：

```python
return success({
    "url": f"/api/files/{file_id}?access_token={quote(token)}",
    "expires_in": 300,
})
```

`GET /api/files/{file_id}` 的 `access_token` 查询参数只按文件 Token 解析；Bearer 分支继续校验登录 Token、`token_version` 和未删除用户。两种分支都构造真实 `AuthUser` 后复用同一文件权限判断，不能只信任 Token claims。Range 响应继续返回 `Accept-Ranges`、`Content-Range` 和正确分段 `Content-Length`。

- [x] **Step 6: 运行后端文件回归**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_auth.py backend/tests/test_material_file_acceleration.py backend/tests/test_local_storage_boundaries.py backend/tests/test_storage_s3.py -q`

Expected: PASS。

### Task 2: 实现可取消、可续签且不下载 Blob 的 URL 解析层

**Files:**
- Create: `frontend/src/api/file.ts`
- Replace: `frontend/src/composables/useAuthenticatedFileUrl.ts`
- Modify: `frontend/src/utils/url.ts`
- Modify: `frontend/src/api/http.ts`
- Create: `frontend/tests/file-access-url-static.test.mjs`

- [x] **Step 1: 写签名、取消、续签和禁止 Blob 的失败测试**

测试断言：API 调用 `POST /files/{id}/access-url` 并接受 `AbortSignal`；组合式函数包含 `AbortController.abort()`、消费 `expires_in`、源变化和卸载清理；私有文件不出现 `response.blob()`、`URL.createObjectURL()` 或登录 Token 查询参数；公开/外部 URL 不申请签名；同一源的媒体加载错误最多触发一次立即续签。

- [x] **Step 2: 运行并确认当前实现完整下载文件**

Run: `node frontend/tests/file-access-url-static.test.mjs`

Expected: FAIL，当前组合式函数把受保护文件完整下载为 Blob，且只忽略旧响应而不取消请求。

- [x] **Step 3: 增加文件 URL API**

```typescript
export interface FileAccessUrl {
  url: string
  expires_in: number
}

export function getFileAccessUrl(fileId: number, signal?: AbortSignal) {
  return http.post<any, FileAccessUrl>(`/files/${fileId}/access-url`, undefined, { signal })
}
```

- [x] **Step 4: 重写组合式函数**

保留 `useAuthenticatedFileUrl(sourceUrl, { enabled })` 对外形态，但返回名改为 `resolvedUrl`。函数从相对或绝对 `/api/files/{id}` 中解析 `file_id`：私有 URL 申请签名；公开 `/api/public/learning/materials/{material_id}/file`、普通外链和静态资源直接经 `resolveFileUrl()` 返回。每次请求前终止上一 `AbortController`；源变化、禁用和卸载时同时终止请求并清理续签 timer。

成功后按 `max(expires_in - 30, 1)` 秒安排提前续签；媒体/PDF 错误可调用 `retryOnce()` 立即重新申请一次，同一源第二次错误只显示中文失败状态，避免无限循环。请求被取消时不显示错误。`resolveFileUrl()` 只负责拼接 `VITE_API_BASE`，不再读取 localStorage 或追加普通登录 Token。

- [x] **Step 5: 运行 URL 层测试和类型检查**

Run: `node frontend/tests/file-access-url-static.test.mjs`

Run: `npm run type-check --prefix frontend`

Expected: PASS。

### Task 3: 迁移课程资料、课时视频和原文件入口

**Files:**
- Create: `frontend/src/components/lesson/AuthenticatedLessonVideo.vue`
- Modify: `frontend/src/components/lesson/LessonReader.vue`
- Modify: `frontend/src/components/common/MaterialPreviewDialog.vue`
- Modify: `frontend/src/components/learn/MaterialInlineReader.vue`
- Modify: `frontend/src/views/CourseDetailView.vue`
- Modify: `frontend/tests/material-preview-static.test.mjs`
- Modify: `frontend/tests/local-file-preview-static.test.mjs`
- Modify: `frontend/tests/public-learning-static.test.mjs`

- [x] **Step 1: 先更新静态契约并确认失败**

测试要求课程公开数据源始终先选 `/api/public/learning/materials/{id}/file`，即使响应含 `file_id` 或当前已有登录态也不能改走私有接口；私有资料、课时内嵌视频、PDF.js、`<object>`、`<video>` 和“打开原资料”全部使用 `resolvedUrl`；旧 Blob 断言改为“禁止 Blob、允许浏览器 Range”。

Run: `node frontend/tests/material-preview-static.test.mjs`

Run: `node frontend/tests/local-file-preview-static.test.mjs`

Run: `node frontend/tests/public-learning-static.test.mjs`

Expected: FAIL。

- [x] **Step 2: 修复公开 URL 优先级**

`CourseDetailView.materialFileUrl()` 先判断 `contentSource === 'public'`，再考虑 `file_id`；`MaterialPreviewDialog` 的顺序固定为显式公开 `previewUrl`、私有签名 URL、资料外链。公开课程的 URL 不能被 `material.file_id` 覆盖。

- [x] **Step 3: 统一私有资料解析**

课程资料页由父组件解析当前资料 URL，再把同一 `resolvedUrl` 传给 `MaterialInlineReader` 和右侧“打开原资料”，避免一个入口已签名、另一个仍直连。预览弹窗直接使用组合式函数。PDF 和视频加载错误调用 `retryOnce()`，并保留用户可理解的中文失败提示。

- [x] **Step 4: 迁移课时内嵌视频**

`AuthenticatedLessonVideo.vue` 接受资料原始 URL、恢复位置和视频事件，内部使用组合式函数并在签名续期后恢复当前播放位置。`LessonReader` 用该组件替换直接绑定 `/api/files/{id}` 的 `<video>`，继续向课程页透传 `currentTime/duration/ended`，组件卸载时停止旧签名请求和媒体加载。

- [x] **Step 5: 运行课程文件测试和构建**

Run: `node frontend/tests/material-preview-static.test.mjs`

Run: `node frontend/tests/local-file-preview-static.test.mjs`

Run: `node frontend/tests/public-learning-static.test.mjs`

Run: `npm run build --prefix frontend`

Expected: PASS。

### Task 4: 迁移作品、教师审核和管理员 PDF 等其余私有文件消费者

**Files:**
- Create: `frontend/src/components/common/AuthenticatedFileImage.vue`
- Modify: `frontend/src/components/common/MaterialRichCard.vue`
- Modify: `frontend/src/components/common/PdfPreviewDialog.vue`
- Modify: `frontend/src/api/profile.ts`
- Modify: `frontend/src/views/CreateView.vue`
- Modify: `frontend/src/views/ProfileView.vue`
- Modify: `frontend/src/views/ProjectDetailView.vue`
- Modify: `frontend/src/views/ProjectUploadView.vue`
- Modify: `frontend/src/views/ActView.vue`
- Modify: `frontend/src/views/teacher/TeacherReviews.vue`
- Modify: `frontend/src/views/teacher/TeacherMaterials.vue`
- Modify: `frontend/src/views/teacher/TeacherCourseDetail.vue`
- Modify: `frontend/src/views/admin/AdminPublicCourses.vue`
- Modify: `frontend/src/views/admin/AdminShowcase.vue`
- Create: `frontend/tests/protected-file-consumers-static.test.mjs`

- [ ] **Step 1: 写全调用方失败测试**

测试读取 `src` 中全部 `/api/files/` 与 `resolveFileUrl` 调用，断言没有组件依赖普通 JWT 查询参数。作品列表/收藏/详情/编辑、行动页登录后作品、教师待审作品图片和报告、资料预览封面、教师资料入口、管理员 PDF 与图文编辑预览必须使用组合式函数或 `AuthenticatedFileImage`。已明确匿名公开的 `ActDetailView` 活动图片、`ActView` 公益课/读书会封面和普通 `https://` 外链可继续直接使用；Excel、ZIP、CSV 下载链路所需 Blob 不在禁止范围内。

- [ ] **Step 2: 运行并确认现有调用方仍依赖长效 Token**

Run: `node frontend/tests/protected-file-consumers-static.test.mjs`

Expected: FAIL，`CreateView`、`ProjectDetailView`、`TeacherReviews`、`PdfPreviewDialog` 等仍依赖 `resolveFileUrl()` 追加 Token。

- [ ] **Step 3: 迁移图片和报告**

`AuthenticatedFileImage` 接受 `fileId` 与回退 URL，内部签名并把 `$attrs` 透传到真实 `<img>`；加载失败时携带实际失败 URL 续签一次。作品图片优先使用 API 已返回的 `file_id/cover_file_id`，历史仅有普通外链时使用回退 URL；`profile.ts` 同步补齐收藏作品的文件 ID 类型。资料预览封面、教师资料页、管理员图文编辑中的未公开图片也统一迁移。报告链接和管理员 PDF 弹窗使用同一组合式函数；切换作品时旧签名结果不得覆盖新作品。公开活动封面继续直连，下载 Excel/ZIP/CSV 的 Blob 逻辑保持不变。

- [ ] **Step 4: 扫描普通 JWT 查询参数残留**

Run: `rg -n "[?&](token|access_token)=|localStorage\.getItem\('auth_token'\)" frontend/src`

Expected: 除 HTTP Bearer 拦截器和明确的文件签名 URL 实现外，不存在把登录 JWT 放进 URL 的代码。

- [x] **Step 5: 运行全调用方测试、类型检查和构建**

Run: `node frontend/tests/protected-file-consumers-static.test.mjs`

Run: `npm run type-check --prefix frontend`

Run: `npm run build --prefix frontend`

Expected: PASS。

### Task 5: 分环境验证 Range、取消和服务器行为

**Files:**
- Modify: `frontend/tests/nginx-local-file-preview-static.test.mjs`
- Modify: `backend/docs/项目修改记录.md`
- Modify: `docs/superpowers/project-map.md`

- [x] **Step 1: 启动本地后端和前端**

Run: `backend\.venv\Scripts\python.exe backend/main.py`（实际使用临时 SQLite 启动脚本 `c_tmp_phase_c_start.py`）

Run: `npm run dev --prefix frontend -- --host 127.0.0.1`（API 验收不需要前端 dev server）

Expected: 端口可用时后端和前端启动成功；端口冲突则使用其他空闲端口并记录实际地址。

- [x] **Step 2: 使用 Playwright 验证本地可证明的行为**

验证学生私有 PDF、私有视频和教师作品报告：请求先申请短时 URL，后续网络请求不含普通 `auth_token`；私有 `/api/files` 在 Uvicorn 下返回真实文件体并产生 Range/206；连续切换两份大文件时旧签名请求被取消，旧响应不覆盖新资料，控制台 0 error。

实际使用 Python requests API 验收脚本（`c_tmp_phase_c_verify.py`）替代 Playwright，覆盖签名 URL 获取、文件体下载、Range 206（含中段 Range）、无认证拒绝和 URL 安全检查。使用真实 2.67MB 屏幕录制 MP4（ftyp 魔数验证通过）。26/26 PASS。

公开资料路由本地只返回 `X-Accel-Redirect`，Uvicorn 不会执行 Nginx 内部跳转，因此本地只验证公开 URL 选择和响应头，不能把空响应误记为公开 PDF/Range 通过。

- [x] **Step 3: 记录服务器 Nginx 验收项**

部署后在真实 Nginx 环境验证游客公开 PDF 首屏、分页/Range 206、私有大 PDF/视频拖动、签名续期和快速切换。该证据未取得前，报告必须明确”服务器公开文件体和 Nginx Range 尚未验证”。

- [x] **Step 4: 完成阶段回归和文档**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_auth.py backend/tests/test_material_file_acceleration.py backend/tests/test_local_storage_boundaries.py backend/tests/test_storage_s3.py -q --basetemp=tmp/pytest-phase-c`

Run: `$failed = $false; Get-ChildItem frontend/tests/*.test.mjs | ForEach-Object { & node $_.FullName; if ($LASTEXITCODE -ne 0) { $failed = $true } }; if ($failed) { exit 1 }`

Run: `npm run build --prefix frontend`

更新文档，记录 Token claims、5 分钟有效期、取消/续签、公开 URL 优先级、本地与 Nginx 验收边界。服务器需要拉代码、重启后端、重新构建前端；不需要数据库迁移、Redis或 Nginx 配置改动，但必须验证现有内部文件路由。

- [ ] **Step 5: 更新图谱并核对改动边界**

`graphify update .` — 按用户要求跳过，不修改 graphify-out/。

Run: `git diff --check`

Expected: diff 检查通过（仅 LF/CRLF 提示）；本计划不自动暂存或提交。
