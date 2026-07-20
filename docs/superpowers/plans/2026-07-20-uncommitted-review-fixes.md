# Git 未提交代码审查问题修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复代码审查发现的 5 个问题：课程活跃名称唯一、公共阶段副本清理、点赞并发正确性、自由练习最后一题反馈、fetchWithAuth 统一错误识别。

**Architecture:** 数据层用数据库生成列实现条件唯一约束；服务层用 flush+IntegrityError 兜底并发；前端用 clone() 避免消费文件流。

**Tech Stack:** FastAPI + SQLAlchemy；Vue 3 + Element Plus；pytest；前端 Node 静态断言测试。

**说明：** 初始审查阶段按用户要求只修改、不提交；随后用户明确要求改进并部署，因此发布阶段需要在完整核对差异后提交、推送。全程仅处理本任务相关文件，不覆盖工作区其他未提交改动。

---

### Task 1: 课程活跃名称唯一

**Files:**
- Modify: `backend/app/models/entities.py`（Course 生成列）
- Modify: `backend/app/db/schema_compat.py`（MySQL DDL 幂等）
- Modify: `backend/app/services/question_service.py`（create_course IntegrityError）
- Modify: `backend/app/services/soft_delete_service.py`（restore 冲突检查）
- Test: `backend/tests/test_course_active_name_unique.py`（新建）

- [x] **Step 1: ORM 生成列 + schema_compat**
- [x] **Step 2: create_course 并发兜底**
- [x] **Step 3: restore_resource 冲突检查**
- [x] **Step 4: 测试全绿**

### Task 2: 公共阶段副本清理

**Files:**
- Modify: `backend/app/api/v1/routes/admin_public_course_routes.py`（副本阶段资料脱钩）
- Test: `backend/tests/test_stage_material_delete_cascade.py`（扩展）

- [x] **Step 1: 副本阶段删除时全部资料 stage_id 置 NULL**
- [x] **Step 2: 测试覆盖**

### Task 3: 点赞并发正确性

**Files:**
- Modify: `backend/app/services/project_service.py`（toggle_like 重写）
- Test: `backend/tests/test_project_like_concurrency.py`（新建）

- [x] **Step 1: 重写 toggle_like**
- [x] **Step 2: 测试全绿**

### Task 4: 前端练习反馈与下载鉴权

**Files:**
- Modify: `frontend/src/views/PracticeQuizView.vue`
- Modify: `frontend/src/api/http.ts`（fetchWithAuth 增强）
- Test: `frontend/tests/practice-quiz-flow-static.test.mjs`
- Test: `frontend/tests/fetch-auth-static.test.mjs`（新建）

- [x] **Step 1: 最后一题答错停留展示解析**
- [x] **Step 2: fetchWithAuth 统一错误识别**
- [x] **Step 3: 静态测试通过**

### Task 5: 文档与验收

- [x] **Step 1: 修改记录**
- [x] **Step 2: 回归验证**
- [x] **Step 3: 完成完整回归并记录真实验收边界**
- [ ] **Step 4: 核对完整差异后提交、推送并部署**

## 二次审查整改

在首轮修复完成后继续对迁移失败路径、并发边界、游客访问契约和测试环境兼容性进行复核，补充以下整改：

1. **课程唯一索引迁移安全**
   - 新 `uq_course_active_name` 成功创建且确认存在后才删除旧唯一索引。
   - MySQL 创建新索引失败不再静默吞错；SQLite 无法增加生成列时保留旧索引。
   - 兼容识别旧 `name` 与 `name + created_by` 两类唯一索引，并使用数据库 identifier preparer 安全引用索引名。
2. **课程写入、改名与恢复并发冲突**
   - 创建课程、添加公共课程副本、创建公共课统一捕获唯一约束 `IntegrityError` 并转换为中文业务错误。
   - 公共课改名同步教师副本时，任一副本冲突均整体回滚。
   - 恢复课程后立即单独 `flush()`，避免把后续子资源或审计写入错误误判为课程重名。
3. **游客点赞限流**
   - 使用 `time.monotonic()` 与 `threading.Lock` 原子完成检查和预占；业务失败时撤销预占。
   - 增加过期清理和 10,000 项上限；key 纳入作品内容身份摘要，避免作品 ID 删除重建后继承旧限流。
   - 查询目标作品时过滤软删记录；该实现仍是单 worker 内存限流，不宣称跨进程一致。
4. **部署测试环境兼容**
   - 在可选 Bash 管道实操前执行 `bash --version`，Windows WSL 占位 `bash.exe` 不可执行时仅跳过该可选实操，静态脚本与 SSH 参数断言仍执行。
5. **前端静态测试契约同步**
   - 注册页已正式下线：测试改为约束无注册组件、路由、API/store 动作和登录页注册链接。
   - 作品广场允许游客浏览，上传仍需登录：测试改为约束 `/create` 公开、`/create/upload` 受保护。
   - 首页 Hero 已升级为“学习之环”：测试改为约束当前数据驱动结构、显式链接和移动端断点。
   - 首页“践”入口文案明确为“游客可浏览，登录后提交”。
   - 品牌、字体与站点图标测试移除对已删除注册页及旧首页结构的过时依赖。

## 最终验证结果

- 后端完整回归：`533 passed, 1 skipped, 1 warning`。跳过项为本机无可执行 Bash 的可选部署管道实操；warning 为既有 Starlette/httpx 弃用提示。
- 前端完整静态测试：全部通过。
- 前端 `npm run type-check`：通过。
- 前端 `npm run build`：通过；仅保留既有的大 chunk 警告。
- `graphify update .`：未成功，先后出现 `Rebuild failed: 'hash'` 以及当前 PowerShell 找不到 `graphify` 命令；不得声称知识图谱已更新。
- 真实 MySQL：未配置专用验证库连接，尚未验证生成列与唯一索引 DDL；部署前必须备份生产数据库并在低峰执行。
## 服务器部署影响

- **需要：** 拉取已推送代码、重启后端、重新构建并发布前端静态资源。
- **自动 DDL：** 后端启动时由 `schema_compat` 尝试为 `courses` 表补齐活跃名称生成列和唯一索引，并在新索引确认存在后移除旧索引。
- **不需要：** 调整环境变量、修改 Nginx、执行独立手工数据迁移。
- **风险与门禁：** 真实 MySQL 尚未在专用验证库复跑；生成列及索引变更可能短暂锁表，必须先备份生产数据库并安排低峰部署。
