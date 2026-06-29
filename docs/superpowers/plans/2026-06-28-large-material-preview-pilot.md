# 课程大文件预览加速试点方案

> 日期：2026-06-28
> 状态：第一版已实施，待服务器压测
> 范围：课程资料文件访问链路、学生端课程详情页、教师端资料管理和课程详情页、生产 Nginx 配置

## 一、试点目标

本次不一次性完成 CDN、对象存储、多码率转码和完整内容理解，而是先做一个可验证的闭环：

1. 让 1GB 级别 PDF / 视频不再主要由 FastAPI 长时间转发，改为后端鉴权后交给 Nginx 传输。
2. 让学生在课程详情页先看到资料封面、摘要、页数或时长、大小等图文信息，而不是只看到标题。
3. 让教师端也采用图文资料卡片和站内预览，确认学生看到的文件、封面、摘要和播放效果是否正常。
4. 通过固定测试方法对比改造前后效果，判断是否继续投入第二阶段。

## 二、当前已核实基础

- 上传接口已经分块写盘，避免一次性把 1GB 文件读入内存。
- `/api/files/{id}` 已支持 `Range` 请求，视频拖动和 PDF 分段加载具备基础条件。
- 生产示例 `deploy/nginx.conf` 已代理 `/api/` 与 `/uploads/`，并透传 `Range` / `If-Range`。
- 学生端课程详情页当前主要展示资料标题、类型、大小、日期，点击后新窗口打开文件。
- 当前长期约定是新文件优先通过 `file_id` 访问 `/api/files/{id}`，生产预览 PDF / 视频优先走 Nginx 代理。

## 三、本轮只做什么

### 1. 大文件加速最小闭环

新增面向资料的打开接口，建议使用：

```text
GET /api/materials/{material_id}/file
```

接口职责：

- 通过 `material_id` 找到资料和 `file_id`。
- 校验当前用户是否有权访问该资料：
  - 学生只能访问自己已加入班级对应课程下的资料。
  - 教师只能访问自己课程下的资料。
  - 管理员可访问全部资料。
- 本地存储时返回 `X-Accel-Redirect`，由 Nginx 直接读取上传目录并传输文件。
- S3 / MinIO 暂不在本轮实现，只保留接口扩展点。

不建议第一轮直接大改 `/api/files/{id}`，因为该接口还被图片、作品报告、公益活动图文内容等复用。先新增资料专用打开接口，降低影响范围。

## 四、其他可选方案与取舍

除本试点方案外，仍有几种可选路径，但不建议作为第一轮实践：

| 方案 | 说明 | 优点 | 缺点 | 结论 |
| --- | --- | --- | --- | --- |
| A. 只加服务器带宽 | 保持现有 FastAPI 文件流，提升服务器出口带宽 | 改动小；见效直接 | 后端 worker 仍会被大文件传输占用；并发越高越不稳；不能解决只有标题的问题 | 不作为主方案 |
| B. 直接上对象存储 + CDN | 文件上传到 MinIO / S3，再通过 CDN 分发 | 并发能力最好；跨地域访问更稳 | 部署和运维复杂度高；需要存储桶、签名、CORS、回源、费用评估 | 适合作为第二阶段 |
| C. 全部资料转成图片分页 | PDF 每页都转图片，前端只看图片 | 首屏可控；兼容性好 | 1GB PDF 转换成本高；图片占用可能更大；文字选择、搜索、清晰度体验下降 | 只适合少量重点资料 |
| D. 上传时强制压缩/拆分 | 限制教师上传 1GB 原文件，要求压缩或拆章节上传 | 技术简单；文件更小 | 改变教师工作流；已有大文件仍要处理；用户体验依赖人工规范 | 可作为管理规范，不替代技术优化 |
| E. 视频直接 HLS 分片 | 上传后转成 m3u8 分片播放 | 视频体验最好；拖动和弱网更稳 | 转码耗 CPU 和存储；第一轮会拉长实施周期 | 视频专项第二阶段再做 |
| F. 只做前端懒加载和骨架屏 | 页面先显示骨架、点击后再加载文件 | 开发快；视觉上不空白 | 不解决大文件传输链路；后端压力不降 | 只能作为辅助 |

第一版敲定方案仍采用：**资料专用鉴权接口 + Nginx `X-Accel-Redirect` 直传 + 资料预览元数据 + 学生端图文资料卡片 + 教师端图文资料卡片和站内预览**。

理由：

- 与当前“本地上传目录 + `file_id` 访问 + 生产优先 Nginx 代理”的项目约定一致。
- 改动范围可控，不需要立即引入 CDN / MinIO。
- 可以同时验证三件事：大文件是否不再拖住后端、学生是否能先看到资料内容、教师是否能在发布后检查资料效果。
- 后续升级到对象存储、CDN、HLS 时，前端图文卡片和预览元数据仍可复用。

### 2. Nginx 内部文件传输

生产 Nginx 增加一个只能内部跳转访问的上传目录：

```nginx
location /_protected_uploads/ {
    internal;
    alias /var/www/tongshi/uploads/;
    sendfile on;
    tcp_nopush on;
    aio threads;
    add_header Accept-Ranges bytes;
    add_header Cache-Control "private, max-age=0";
}
```

后端鉴权通过后返回：

```text
X-Accel-Redirect: /_protected_uploads/<object_key>
Content-Type: application/pdf 或 video/mp4
Content-Disposition: inline; filename*=UTF-8''...
```

预期效果：

- 浏览器仍请求业务接口。
- 权限仍由后端判断。
- 真实 1GB 文件传输由 Nginx 完成。
- Range 请求由 Nginx 原生处理，减少 Python 后端 worker 占用。

### 3. PDF 图文预览

新增资料预览元数据，建议新增表 `material_previews`：

```text
id
material_id
status              pending / processing / ready / failed
cover_file_id       PDF 第一页封面或视频封面帧
summary             资料摘要，第一轮先从 PDF 前几页文字提取
page_count          PDF 页数
duration_seconds    视频时长
resolution          视频分辨率
error_message
created_at
updated_at
```

PDF 处理方式：

- 使用 PyMuPDF 读取页数。
- 渲染第一页为小图，保存为新的 `StoredFile`，`biz_type=material_preview`。
- 提取前 3 页文本，生成 120 到 200 字摘要。
- 可选执行 `qpdf --linearize` 生成 Web 优化 PDF；如果服务器存储压力允许，建议在试点中启用。

第一轮不做 OCR，不做 AI 总结，不做全文索引。

### 4. 视频图文预览

视频第一轮只做轻量处理：

- 使用 `ffprobe` 获取时长、分辨率、编码信息。
- 使用 `ffmpeg` 截取第 3 秒或 10% 位置作为封面图。
- 前端使用 `<video controls preload="metadata">`，播放地址使用新的资料打开接口。

第一轮不做 HLS 转码和多清晰度，只验证 Nginx 直传与 metadata 加载体验。若 1GB 视频仍卡，再进入第二阶段做 HLS。

### 5. 学生端图文资料卡片

改造 `frontend/src/views/CourseDetailView.vue`：

- 资料卡片左侧展示封面图。
- 右侧展示标题、摘要、类型、大小、页数或时长、上传日期。
- 预览未生成时显示“预览生成中”，仍允许打开原文件。
- 预览失败时显示“预览生成失败，可直接打开资料”。
- 点击 PDF 打开站内预览弹窗或页面。
- 点击视频打开站内播放器。

第一轮的重点是让学生在进入课程详情页后立即看到资料内容概览，不要求做复杂阅读器。

### 6. 教师端图文资料卡片、站内预览和状态反馈

改造 `frontend/src/views/teacher/TeacherMaterials.vue` 和 `frontend/src/views/teacher/TeacherCourseDetail.vue`：

- 教师端资料展示与学生端同理，也使用图文资料卡片：封面图、标题、摘要、类型、大小、页数或时长、上传日期、预览状态。
- `TeacherMaterials.vue` 可保留筛选和分页，但资料主体建议由纯表格升级为图文列表或“表格 + 展开预览摘要”的混合视图，避免教师端仍只有标题。
- `TeacherCourseDetail.vue` 的阶段资料卡片与学生端保持同一套视觉信息，只额外保留编辑、删除、移动阶段等管理动作。
- 表格或卡片中增加“预览状态”。
- 资料上传成功后显示“预览生成中”。
- 失败时显示失败原因和“重新生成预览”入口。
- 资料管理和课程详情中的“查看/预览”打开站内预览弹窗，弹窗内展示 PDF 或视频，并保留“新窗口打开原文件”入口。
- 教师课程详情页资料卡片中的“查看”同样打开站内预览弹窗，方便教师按课程阶段检查资料。
- 教师端资料卡片和预览使用与学生端相同的资料预览数据、`MaterialPreviewDialog` 和 `GET /api/materials/{material_id}/file`，避免两套展示和预览逻辑。
- 教师端预览前仍走后端权限校验，只能预览自己课程下的资料。
- 保持现有上传、筛选、删除逻辑不变。

## 五、本轮明确不做什么

- 不接 CDN。
- 不强制迁移到 S3 / MinIO。
- 不做 HLS 视频分片和多码率转码。
- 不做 PDF 全文搜索。
- 不做 OCR。
- 不做 AI 语义摘要。
- 不改课程、阶段、题目、作品等业务结构。
- 不把文件改成第三方网盘链接。

## 六、建议涉及文件

### 后端

- `backend/app/models/entities.py`
  - 新增 `MaterialPreview` ORM。
- `backend/app/schemas/common.py`
  - 新增 `MaterialPreviewOut`。
  - `MaterialOut` 增加 `preview` 字段。
- `backend/app/db/schema_compat.py`
  - 增加 `material_previews` 表兼容创建逻辑。
- `backend/app/services/material_service.py`
  - 增加资料文件权限校验和预览状态返回。
- `backend/app/services/file_service.py`
  - 增加构建 Nginx 内部跳转路径的方法。
- `backend/app/services/material_preview_service.py`
  - 新增 PDF / 视频预览生成服务。
- `backend/app/api/v1/routes/material_routes.py`
  - 新增 `GET /materials/{material_id}/file`。
  - 新增 `POST /materials/{material_id}/preview/rebuild`。
- `backend/app/api/v1/routes/upload_routes.py`
  - 创建资料后触发或记录预览生成任务，本轮也可以先由管理命令手动生成。

### 前端

- `frontend/src/api/material.ts`
  - 扩展 `Material` 类型，增加 `preview`。
  - 增加资料文件 URL 构造方法。
- `frontend/src/views/CourseDetailView.vue`
  - 改造资料卡片为图文卡片。
  - 增加 PDF / 视频预览弹窗。
- `frontend/src/views/teacher/TeacherMaterials.vue`
  - 增加图文资料卡片或混合列表、预览状态、站内预览入口和重建入口。
- `frontend/src/views/teacher/TeacherCourseDetail.vue`
  - 将阶段资料卡片升级为与学生端同理的图文资料卡片，并将“查看”改为站内预览。
- `frontend/src/components/common/MaterialPreviewDialog.vue`
  - 新增统一预览弹窗，学生端和教师端共用，PDF 与视频共用入口。

### 部署

- `deploy/nginx.conf`
  - 增加内部上传目录。
  - 保留 `/api/` 代理。
  - 保留 `Range` / `If-Range` 相关配置。

### 测试

- `backend/tests/test_material_file_acceleration.py`
  - 校验资料文件接口权限。
  - 校验授权后返回 `X-Accel-Redirect`。
  - 校验未加入课程的学生不能访问。
- `backend/tests/test_material_preview_service.py`
  - 校验 PDF 预览记录生成。
  - 校验视频元数据记录生成。
  - 校验失败状态可记录。
- `frontend/tests/material-preview-static.test.mjs`
  - 校验课程详情页不再只有标题。
  - 校验封面、摘要、页数或时长、预览状态存在。
  - 校验教师端资料管理和教师课程详情不再只有标题，能展示图文资料卡片信息。
  - 校验教师端资料管理和教师课程详情使用统一站内预览入口。
- `frontend/tests/nginx-local-file-preview-static.test.mjs`
  - 更新 Nginx 静态检查，确认内部目录和 Range 配置。

## 七、试点验收指标

### 功能指标

1. 学生只能打开自己课程下的资料。
2. 教师只能打开自己课程下的资料。
3. 未授权用户无法通过资料接口打开文件。
4. 课程详情页资料卡片展示封面、摘要、类型、大小、页数或时长。
5. PDF 和视频能在站内预览。
6. 教师端资料管理页能以图文资料卡片或混合列表展示封面、摘要、页数或时长、预览状态，并能站内预览 PDF 和视频。
7. 教师端课程详情管理页能以图文资料卡片展示阶段资料，并能站内预览。
8. 预览生成失败时不影响原文件打开。

### 性能指标

在服务器环境使用 1GB PDF 测试：

| 指标 | 目标 |
| --- | --- |
| 课程详情页图文卡片出现 | 1 到 2 秒内，取决于课程接口响应 |
| PDF 预览弹窗打开并开始显示 | 2 到 8 秒内为理想，弱网不超过 15 秒 |
| Range 请求状态 | 返回 206 |
| FastAPI worker 占用 | 不因 1GB 文件传输长时间占用 |
| 5 人同时打开同一 1GB PDF | 不出现 502 / 504，不明显拖慢普通 API |
| 后端 CPU | 单文件传输时主要压力应转移到 Nginx，Python CPU 不应持续升高 |

如果服务器出口带宽很低，完整下载 1GB 仍然会慢；本轮验收看的是“多久能看到内容”和“后端是否被大文件拖住”。

## 八、测试方法

### 1. 改造前基线

准备资料：

- 一个 1GB 左右 PDF。
- 一个 1GB 左右 MP4 或 WebM。
- 一个普通 20 到 100MB PDF 作为对照。

记录：

- 浏览器打开课程详情页到资料卡片可见耗时。
- 点击 PDF 到第一页可见耗时。
- 点击视频到 metadata 加载完成耗时。
- DevTools Network 中是否出现 206。
- 后端进程 CPU、内存、请求耗时。
- Nginx 或后端 access log。

命令示例：

```powershell
curl.exe -I -H "Range: bytes=0-1048575" "https://域名/api/files/文件ID?token=测试token"
curl.exe -L -o NUL -w "time_starttransfer=%{time_starttransfer} time_total=%{time_total} speed=%{speed_download}\n" -H "Range: bytes=0-1048575" "https://域名/api/files/文件ID?token=测试token"
```

### 2. 改造后复测

使用新的资料打开接口：

```powershell
curl.exe -I -H "Range: bytes=0-1048575" "https://域名/api/materials/资料ID/file?token=测试token"
curl.exe -L -o NUL -w "time_starttransfer=%{time_starttransfer} time_total=%{time_total} speed=%{speed_download}\n" -H "Range: bytes=0-1048575" "https://域名/api/materials/资料ID/file?token=测试token"
```

重点确认：

- 响应是 206。
- `Accept-Ranges: bytes` 存在。
- 后端日志中接口只做鉴权和内部跳转，不持续输出 1GB 文件流。
- Nginx access log 记录了大文件传输。
- 浏览器中 PDF / 视频仍可正常打开和拖动。

### 3. 并发验证

用 5 个浏览器窗口或简单压测工具同时访问同一资料：

- 同时打开课程详情页。
- 同时点击 1GB PDF。
- 同时拖动视频进度条。

记录：

- 是否有 502 / 504。
- 普通 API 是否还能正常响应。
- 首屏资料卡片是否仍能快速出现。
- Python 后端是否出现 worker 堵塞。

## 九、风险和处理

| 风险 | 处理 |
| --- | --- |
| `object_key` 被构造为非法路径 | 后端只允许数据库中的 `object_key`，并做路径规范化，禁止 `..` |
| token 出现在 URL 中 | 第一轮沿用现有机制；后续改为短期预览票据 |
| PDF 未线性化导致首次打开慢 | 试点中加入 `qpdf --linearize` 对照测试 |
| PDF 预览生成耗时长 | 第一轮允许异步或手动命令生成，页面显示“生成中” |
| 视频 1GB 仍然慢 | 第一轮先验证 Nginx 直传；失败后进入 HLS 分片 |
| Nginx 路径和服务器上传目录不一致 | 部署前明确 `LOCAL_UPLOAD_DIR` 与 Nginx `alias` 映射 |
| 预览生成失败影响学习 | 原文件打开入口必须保留 |

## 十、回滚方案

- 保留现有 `/api/files/{id}` 访问方式。
- 前端通过配置开关决定使用新资料接口还是旧 `file_id` 地址。
- Nginx 内部目录配置可单独移除，不影响普通 API。
- `material_previews` 表只提供增强信息，缺失时前端回退到标题、类型、大小。

## 十一、推荐实施顺序

1. 先做基线测试，记录当前 1GB PDF / 视频的真实耗时。
2. 增加资料专用文件接口和权限校验。
3. 配置 Nginx `X-Accel-Redirect` 内部目录。
4. 用同一个 1GB PDF 复测 Range、首字节、后端占用。
5. 增加 `material_previews` 表和 PDF 封面/摘要生成。
6. 改造学生端课程详情页资料卡片。
7. 增加视频封面和时长。
8. 改造教师端资料管理页和教师课程详情页，接入同理的图文资料卡片和统一站内预览。
9. 跑后端测试、前端静态测试和前端构建。
10. 整理测试对比结果，决定是否进入第二阶段：CDN / MinIO / HLS。

## 十二、服务器部署影响

本试点需要服务器修改：

- 服务器需要拉取代码。
- 后端需要重启。
- 前端需要重新构建并部署。
- Nginx 需要增加内部上传目录并 reload。
- 数据库需要新增 `material_previews` 表。
- 服务器需要安装或确认存在：
  - `ffmpeg`
  - `ffprobe`
  - `qpdf`（如果测试 PDF 线性化）
  - Python 依赖 `PyMuPDF`
- 环境变量需要核对：
  - `LOCAL_UPLOAD_DIR`
  - `ALLOW_QUERY_TOKEN_FOR_FILES`

第一轮不需要配置 CDN，不需要配置 S3 / MinIO。
