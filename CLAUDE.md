# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目简介

中国计量大学理工科大一学生 AI 通识教育课程平台，围绕"探·练·创·行"四大学习环节设计。共 6 章：AI 概述、计算机基础、AI 理论基础、AI 工具使用、AI 前沿与应用、AI 伦理与未来。

## 平台功能

### 学生端
- **探·学无止境（/learn）** — 按章节浏览课程内容，在线观看视频和阅读 PDF 教材，追踪学习进度
- **练·学以致用（/practice）** — 按章节进行在线测验，支持选择题和填空题，即时批改并展示解析
- **造·智创未来（/create）** — 浏览和提交 AI 项目作品，支持标签分类、点赞、详情查看
- **行·知行合一（/act）** — 查看课程活动时间线与动态
- **成长档案（/portfolio）** — 个人学习数据可视化，包含雷达图展示各章掌握程度

### 教师端（/teacher）
- **工作台概览** — 教学数据总览仪表盘
- **资料管理** — 上传和管理课程视频/PDF 资料
- **题库管理** — 增删改查题目（选择题/填空题）
- **学生数据** — 查看学生学习进度与成绩统计
- **作品审核** — 审批学生提交的项目作品（通过/驳回）

### 公共页面
- 登录/注册、关于平台、隐私政策、联系我们

## 常用命令

### 后端（Python / FastAPI）
```bash
cd backend
pip install -r requirements.txt
py database_setup.py          # 初始化/重置 MySQL 数据库 + 建表 + 填充种子数据
py main.py                    # 启动 FastAPI 服务，端口 8050
# Windows 下也可使用：start_backend.bat（自动安装依赖 + 检查数据库 + 启动服务）
```

### 前端（Vue 3 / Vite）
```bash
cd frontend
npm install
npm run dev                   # Vite 开发服务器（默认端口 5173）
npm run build                 # 类型检查 + 生产构建
npm run preview               # 预览生产构建产物
```

### API 文档
FastAPI 自动生成的 Swagger UI：http://127.0.0.1:8050/docs

## 项目架构

### 后端 — 分层架构：Routes → Services → Models

- `backend/main.py` — FastAPI 应用入口，CORS、静态文件挂载、全局异常处理
- `backend/app/api/v1/routes/` — 9 个路由模块，全部挂载在 `/api` 前缀下
- `backend/app/services/` — 8 个业务逻辑服务模块
- `backend/app/models/entities.py` — 所有 8 个 SQLAlchemy ORM 模型集中在一个文件
- `backend/app/schemas/common.py` — 所有 Pydantic 请求/响应 Schema 集中在一个文件
- `backend/app/core/` — 配置（读取 `.env`）、JWT/密码安全、统一响应格式、自定义异常
- `backend/app/db/session.py` — SQLAlchemy 引擎 + 会话工厂

**统一响应格式：** 所有接口返回 `{"code": 0, "data": ..., "message": "ok"}`（成功）或 `{"code": <错误码>, "data": null, "message": "..."}`（失败）。HTTP 状态码始终为 200。

**数据库：** MySQL（数据库名 `tongshi`），通过 `backend/.env` 配置连接串 `mysql+pymysql://`。存在 `tongshi.db` SQLite 文件作为早期开发残留，正式环境仅使用 MySQL。

### 前端 — Vue 3 单页应用

- `frontend/src/api/http.ts` — Axios 实例，JWT 拦截器（从 localStorage 读取 token），401 自动跳转登录
- `frontend/src/api/*.ts` — 10 个类型化 API 模块，对应后端各业务域
- `frontend/src/stores/auth.ts` — Pinia 认证状态管理（登录/注册/登出），JWT 持久化到 localStorage
- `frontend/src/router/index.ts` — 20+ 路由，`beforeEach` 鉴权守卫 + 教师角色校验
- `frontend/src/views/` — 页面组件（Composition API + Element Plus）
- `frontend/src/views/teacher/` — 教师端子页面（布局 + 5 个视图）
- `frontend/src/views/content/` — VideoPlayer 和 PdfViewer 组件

Vite 开发服务器将 `/api` 和 `/uploads` 代理到 `http://127.0.0.1:8050`。

### 数据库表（8 张）

`users`、`chapters`、`materials`、`questions`、`quiz_attempts`、`student_progress`、`projects`、`project_likes`、`activity_events`

### 约定

- 用户 `id` 即学号或工号，同时作为主键
- 前端统一使用 `<script setup>` + TypeScript
- 新增 Pydantic Schema 往 `common.py` 中追加
- 新增 ORM 模型往 `entities.py` 中追加
- 在实施计划之前要先做好规划在工作

## 语言要求

- 所有对话必须使用中文。
- 所有文档必须使用中文。
- 所有代码注释必须使用中文。

## 执行要求

- 在生成说明、总结、计划、提交说明时，统一使用中文。
- 在新增或修改 Markdown 文档时，统一使用中文。
- 在新增或修改代码注释时，统一使用中文。

### 设计文档

规格说明和实施计划位于 `docs/superpowers/`：
- `specs/` — 功能设计规格（前端深化、认证/教师/学习模块、前后端集成）
- `plans/` — 实施任务清单
