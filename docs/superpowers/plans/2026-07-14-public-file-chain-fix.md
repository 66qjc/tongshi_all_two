# 学生端公开文件链路修复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复学生端“学”页面 PDF 预览失败和“悟”页面正文图片无法展示的问题，同时保持现有私有文件鉴权、软删除过滤和大文件传输行为不变。

**Architecture:** 公开资料继续使用后端鉴权后返回 `X-Accel-Redirect`，由 Nginx 内部映射实际上传目录；该响应不声明由 ASGI 空响应体承担的 `Content-Length`。悟页面正文图片继续使用统一 `/api/files/{file_id}`，由文件权限服务识别激活展示内容 `content_blocks` 中的图片引用，不把上传目录或所有文件公开。

**Tech Stack:** FastAPI、SQLAlchemy、Uvicorn、Nginx、Vue 3、TypeScript、pytest、前端静态测试。

---

### Task 1: 后端 PDF X-Accel 响应回归测试

**Files:**
- Modify: `backend/tests/test_material_file_acceleration.py`
- Modify: `backend/tests/test_public_learning.py`

- [x] **Step 1: 写失败测试**

覆盖公开资料文件响应不设置 `Content-Length`，并保留 `X-Accel-Redirect`、`Content-Disposition` 和 `Accept-Ranges`。

- [x] **Step 2: 运行受影响测试确认失败**

运行：`python -m pytest backend/tests/test_material_file_acceleration.py backend/tests/test_public_learning.py -q`

预期：新增断言在当前实现下失败，原因是公开资料服务仍把数据库文件大小写入响应头。

### Task 2: 修复公开资料响应与悟页面图片权限

**Files:**
- Modify: `backend/app/api/v1/routes/material_routes.py`
- Modify: `backend/app/services/public_learning_service.py`
- Modify: `backend/app/services/file_service.py`
- Modify: `backend/tests/test_material_file_acceleration.py`
- Modify: `backend/tests/test_showcase_content_blocks.py`

- [x] **Step 1: 移除 X-Accel 空响应的 Content-Length**

仅从 `open_material_file()` 和 `resolve_public_material_file()` 移除手工 `Content-Length`；普通 `/api/files/{file_id}` 流式响应的 Range 和长度逻辑保持不变。

- [x] **Step 2: 增加 content_blocks 图片引用识别**

增加中文注释的辅助逻辑，读取激活 `ShowcaseItem.content_blocks` 中 `type=image` 且 `data.file_id` 为正整数的引用；接入 `_can_read_showcase_file()`、`_has_any_file_reference()` 和 `_has_active_file_reference()`，确保激活展示图片可匿名读取，停用/删除展示和无业务引用文件仍被拒绝。

- [x] **Step 3: 运行后端测试确认通过**

运行：`python -m pytest backend/tests/test_material_file_acceleration.py backend/tests/test_public_learning.py backend/tests/test_showcase_content_blocks.py -q`

预期：新增 PDF 响应头测试、公开正文图片读取测试和现有权限测试全部通过。

### Task 3: Nginx 配置与部署文档收口

**Files:**
- Modify: `deploy/nginx.conf`
- Modify: `deploy/README.md`
- Modify: `docs/superpowers/project-map.md`

- [x] **Step 1: 固化生产上传目录映射**

补充 `location /_protected_uploads/`，使用 `internal` 和 `/data/tongshi/uploads/`，并明确该路径不能直接公网访问；同步部署说明和服务器部署影响。

- [x] **Step 2: 添加静态配置回归检查**

扩展现有部署静态测试，确认配置包含 `internal`、`alias /data/tongshi/uploads/`，且没有把上传目录作为普通公开静态目录暴露。

- [x] **Step 3: 运行部署配置测试**

运行：`python -m pytest backend/tests/test_deploy_files_static.py backend/tests/test_deploy_env_check.py -q`

### Task 4: 悟页面图片加载容错

**Files:**
- Modify: `frontend/src/views/ActDetailView.vue`
- Create or modify: `frontend/tests/act-showcase-detail-static.test.mjs`

- [x] **Step 1: 写失败静态测试**

验证正文图片仍使用 `/api/files/{file_id}`，并存在图片加载失败后的可理解占位/错误状态，不改成绕过鉴权的 `/uploads` 直链。

- [x] **Step 2: 实现最小前端容错**

为正文图片增加按 `file_id` 的失败状态，加载失败时显示中文占位提示；封面和旧版 `images` 回退逻辑保持不变。

- [x] **Step 3: 运行前端静态检查与构建**

运行：`node frontend/tests/act-showcase-detail-static.test.mjs`、`npm run type-check --prefix frontend`、`npm run build --prefix frontend`。

### Task 5: 服务器部署与端到端验收

**Files:**
- Modify: 无业务代码新增；仅部署已验证代码和 Nginx 配置
- Verify: 服务器 `/etc/nginx/conf.d/tongshi.conf`、`tongshi-backend.service`、公网接口

- [x] **Step 1: 备份并更新服务器配置**

先备份现有 Nginx 配置，再同步代码和配置；不修改服务器 `.env`，不删除上传文件。

- [x] **Step 2: 配置检查并平滑重载**

运行 `nginx -t`，通过后执行 `systemctl reload nginx`；随后重启后端服务使 Python 代码生效。

- [x] **Step 3: 验证 PDF**

检查公开 PDF 响应的 `Content-Type`、`X-Accel-Redirect`、首字节 `%PDF`、实际长度和 Range 请求；确认不再出现 `Response content shorter than Content-Length`。

- [x] **Step 4: 验证悟页面图片**

分别请求封面和 `content_blocks` 图片，确认返回真实 `image/png` 或 `image/jpeg`，无权限文件仍被拒绝。

- [x] **Step 5: 更新变更记录**

记录代码、Nginx、重启和验证结果，并明确服务器部署影响；运行 `graphify update .` 和 `git diff --check`。

### 实施结果（2026-07-14）

- 后端相关测试 46 passed；前端 type-check、静态回归测试和生产构建通过。
- 服务器已同步后端代码和前端 dist，备份原 Nginx 配置，执行 `nginx -t`、reload，并重启 `tongshi-backend.service`。
- 真实验收初次发现 Nginx worker 无法遍历 `/data/tongshi/uploads`；已将该目录组改为 `nginx` 并保持 `750`，未向其他用户开放上传目录。
- 公开资料 PDF `material_id=22` 返回 `200 application/pdf`、首字节 `%PDF-`；Range 请求返回 `206`、`Content-Range` 正常。
- “悟”正文 `content_blocks` 图片 `file_id=66-71、78` 返回真实 PNG/JPEG；无业务引用和停用内容仍由后端权限逻辑拒绝。
- 服务器部署影响：已完成 Nginx reload、后端重启和前端静态资源发布；无需数据库迁移、无需修改环境变量。后续新增上传目录时必须继承 `nginx` 组可遍历权限。

### 后续验收补充：PDF.js Worker MIME（2026-07-14）

- 浏览器真实控制台发现 `pdf.worker.min-*.mjs` 被 Nginx 返回为 `application/octet-stream`，导致 PDF.js Worker 被严格 MIME 校验拒绝。
- 已在 `deploy/nginx.conf` 为 `.mjs` 增加 `application/javascript` 映射，并新增部署静态回归测试。
- 本补充只影响 Nginx 静态资源响应；服务器无需重启后端或执行数据库迁移。
