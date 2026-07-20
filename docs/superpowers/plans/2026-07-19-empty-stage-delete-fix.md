# 空阶段删除失败修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复教师端与管理员端「阶段看起来无资料时删不掉」的问题：删除阶段前强制脱钩软删资料 `stage_id` 与入站 `source_stage_id` 引用。

**Architecture:** 以 `delete_stage` 服务层为正确性主路径——活跃资料按需软删写快照后，统一把本阶段全部资料 `stage_id` 置空，并把指向本阶段的 `source_stage_id` 置空，再物理删阶段。ORM/`schema_compat` 补 `ON DELETE SET NULL` 仅作防御。前端展示后端真实错误信息。

**Tech Stack:** FastAPI + SQLAlchemy；Vue 3 + Element Plus；pytest；前端静态断言测试。

**设计依据：** `docs/superpowers/specs/2026-07-19-empty-stage-delete-fix-design.md`

**说明：** 用户要求先写设计/计划再实现；实现阶段默认不提交 git。

---

### Task 1: 后端失败测试（先红）

**Files:**
- Modify/Create: `backend/tests/test_stage_material_delete_cascade.py`（或 `backend/tests/test_empty_stage_delete.py`）

- [x] **Step 1: 增加用例**
  - 完全空阶段 + `cascade_materials=true` 删除成功
  - 仅软删资料的阶段删除成功，且资料 `stage_id is None`、仍软删
  - 存在 `source_stage_id` 指向目标阶段时删除成功，引用方置 `NULL`
  - 回归：有活跃资料不传 cascade 仍拒绝；传 cascade 仍软删活跃资料并删阶段
  - 管理端：空公共阶段可删

- [x] **Step 2: 跑测试，确认至少「source_stage_id 引用」类失败（红）**

### Task 2: 实现 `delete_stage` 脱钩

**Files:**
- Modify: `backend/app/services/course_stage_service.py`
- Modify: `backend/app/models/entities.py`（`source_stage_id` ondelete）
- Modify: `backend/app/db/schema_compat.py`（MySQL FK 尽量补齐）
- Modify: `backend/app/api/v1/routes/admin_public_course_routes.py`（如需与服务层对齐注释/兜底）

- [x] **Step 1: 按设计顺序改 `delete_stage`**
  1. 活跃资料判断 / 非级联拒绝
  2. 级联时 soft_delete 活跃资料
  3. 全部资料 `stage_id = NULL`
  4. 全部 `source_stage_id = NULL` where 指向本阶段
  5. `db.delete(stage)`

- [x] **Step 2: ORM / schema_compat 防御对齐**

- [x] **Step 3: 跑 Task 1 测试至全绿**

### Task 3: 前端错误提示

**Files:**
- Modify: `frontend/src/views/teacher/TeacherCourseDetail.vue`
- Modify: `frontend/tests/course-stage-delete-static.test.mjs`

- [x] **Step 1: 静态测试要求教师删阶段 catch 使用 `error?.message`**
- [x] **Step 2: 改 `handleDeleteStage` 错误提示**
- [x] **Step 3: 静态测试通过**

### Task 4: 文档与验收

**Files:**
- Modify: `backend/docs/项目修改记录.md`
- Modify: 本计划勾选；设计状态改为已实现

- [x] **Step 1: 写第 N 轮修改记录与服务器部署影响**
- [x] **Step 2: 汇总验证命令结果**
- [x] **Step 3: 不提交 git**

## 验证命令

```bash
# 后端
cd backend
python -m pytest tests/test_stage_material_delete_cascade.py tests/test_empty_stage_delete.py -v

# 前端
cd frontend
node tests/course-stage-delete-static.test.mjs
```

## 服务器部署影响

- 需要：拉代码、重启后端、重建前端
- 不需要：业务数据迁移、环境变量、Nginx
