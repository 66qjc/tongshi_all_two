# 共享题库标签可选已有项 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 教师端与管理员端共享题库的新增/编辑标签与列表筛选，支持手输新标签并从全站已有标签中点选。

**Architecture:** 后端从活跃共享题 `tags` JSON 聚合去重标签，分别暴露教师 `/api/questions/tags` 与管理员 `/api/admin/question-bank/tags`；前端 `el-select` 绑定选项并保留 `allow-create`。列表 `tag` 筛选语义保持模糊匹配不变。

**Tech Stack:** FastAPI + SQLAlchemy；Vue 3 + Element Plus；后端 pytest；前端 Node 静态断言测试。

**设计依据：** `docs/superpowers/specs/2026-07-19-shared-question-tag-options-design.md`

**说明：** 用户要求本轮直接写代码且不提交 git；计划中的 commit 步骤跳过。

---

### Task 1: 后端标签聚合服务 + 接口

**Files:**
- Modify: `backend/app/services/question_service.py`
- Modify: `backend/app/api/v1/routes/question_routes.py`
- Modify: `backend/app/api/v1/routes/admin_question_bank_routes.py`
- Modify: `backend/app/services/admin_question_bank_service.py`（可选薄封装）
- Test: `backend/tests/test_question_tags.py`（新建）

- [x] **Step 1: 写失败测试**
- [x] **Step 2: 实现 `list_question_tags` 与两端 GET 路由**
- [x] **Step 3: 跑通相关测试**

### Task 2: 前端 API + 教师/管理员页面

**Files:**
- Modify: `frontend/src/api/question.ts`
- Modify: `frontend/src/api/adminQuestionBank.ts`
- Modify: `frontend/src/views/teacher/TeacherQuestions.vue`
- Modify: `frontend/src/views/admin/AdminQuestionBank.vue`
- Test: `frontend/tests/teacher-question-bank-static.test.mjs`
- Test: `frontend/tests/admin-question-bank-static.test.mjs`

- [x] **Step 1: 更新静态测试（先红）**
- [x] **Step 2: API 与页面绑定 tagOptions**
- [x] **Step 3: 跑静态测试与必要 type-check/build**

### Task 3: 文档同步

**Files:**
- Modify: `backend/docs/项目修改记录.md`（或项目惯用修改记录）
- 设计/计划状态勾选

- [x] **Step 1: 记录改动与服务器部署影响**
- [x] **Step 2: 不提交 git**

## 验收要点

1. 弹窗可选已有标签 + 手输创建
2. 列表筛选可选/可手输
3. 软删题标签不出现
4. 无 DB 迁移；需重启后端 + 重建前端
