# 前端对接后端 API + 后端优化 设计文档

> **目标:** 前端所有 mock 数据替换为真实 API 调用；后端统一响应格式、全局异常处理、去掉 SQLite 改为 MySQL only、提供一键部署脚本。

## 一、后端优化

### 1.1 统一响应格式

所有 API 返回：
```json
{ "code": 0, "data": { ... }, "message": "ok" }
```
失败时：
```json
{ "code": 400, "data": null, "message": "该学号已注册" }
```

### 1.2 全局异常处理

- 新增 `app/core/exceptions.py`：`BusinessException(code, message)`
- `main.py` 注册 `exception_handler`，自动将 HTTPException 和 BusinessException 包装为统一格式
- SQLAlchemy 异常统一返回 500

### 1.3 MySQL Only

- `config.py` 默认 DATABASE_URL 改为 `mysql+pymysql://root:123456@127.0.0.1:3306/tongshi`
- `session.py` 去掉 SQLite PRAGMA 逻辑
- `.env` 更新

### 1.4 database_setup.py

一键脚本，功能：
- 连接 MySQL，创建 tongshi 数据库
- 建 9 张表（用 SQLAlchemy create_all）
- 插入种子数据

```bash
py database_setup.py          # 建库+建表+种子
py database_setup.py --reset  # 清空重建
py database_setup.py --check  # 检查连接
```

### 1.5 API 路径统一加 /api 前缀

所有路由从根路径改为 `/api` 前缀，方便前端代理区分。

## 二、前端对接

### 2.1 基础设施

- 安装 axios
- 创建 `src/api/http.ts`：axios 实例，baseURL `/api`，请求拦截器自动带 JWT，响应拦截器统一处理错误
- `vite.config.ts` 加 `server.proxy: { '/api': 'http://127.0.0.1:8050' }`

### 2.2 API 模块

按模块拆分：
- `src/api/auth.ts` — login, register, getMe
- `src/api/chapter.ts` — listChapters, getChapterContents
- `src/api/quiz.ts` — submitAnswer, getHistory, getStats
- `src/api/question.ts` — listQuestions, createQuestion, updateQuestion, deleteQuestion
- `src/api/project.ts` — listProjects, getProject, createProject, toggleLike
- `src/api/teacher.ts` — getStats, getStudents, getProjects, approve, reject
- `src/api/material.ts` — listMaterials, createMaterial, deleteMaterial
- `src/api/portfolio.ts` — getPortfolio
- `src/api/upload.ts` — uploadFile

### 2.3 Auth Store 改造

- `login()` → 调 `POST /api/token`，存 JWT + 用户信息
- `register()` → 调 `POST /api/register`
- 去掉 mockAccounts 和 mock-token 生成

### 2.4 View 层改造（12 个文件）

每个 View 的 `ref([...])` 改为 `onMounted` 里调 API，加 loading 状态。

## 三、实施顺序

1. 后端：统一响应 + 异常处理 + MySQL + database_setup.py
2. 前端：axios + API 层 + 代理配置
3. 前端：Auth Store 改造
4. 前端：逐个 View 对接 API
5. 联调验证
