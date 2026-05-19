# AI 通识课平台 — 后端服务

> FastAPI + SQLAlchemy + MySQL 的分层架构后端，为前端 Vue 3 SPA 提供 RESTful API。

---

## 建议先从这里理解项目

```text
backend/
├── main.py                       # 应用入口：FastAPI 工厂 + lifespan + 全局异常处理
├── requirements.txt              # Python 依赖清单
├── database_setup.py             # 一键部署脚本（建库 → 建表 → 种子数据）
├── seed_data.py                  # 开发/演示用种子数据
├── alembic.ini                   # Alembic 数据库迁移配置
│
├── app/
│   ├── api/v1/
│   │   ├── __init__.py           # 路由聚合器，挂载所有子路由到 /api
│   │   └── routes/
│   │       ├── auth_routes.py    # 登录、注册、获取当前用户
│   │       ├── chapter_routes.py # 章节列表、详情、状态/排课更新
│   │       ├── material_routes.py# 学习资料（视频/PDF）CRUD
│   │       ├── question_routes.py# 题库 CRUD + Excel 导入 + 课程管理
│   │       ├── quiz_routes.py    # 答题提交、历史、统计
│   │       ├── project_routes.py # 作品广场、提交、点赞
│   │       ├── teacher_routes.py # 教师工作台、审核、批量下载
│   │       ├── class_routes.py   # 班级管理 + Excel 批量导入学生
│   │       ├── announcement_routes.py  # 公告/任务发布、已读/完成追踪
│   │       ├── portfolio_routes.py     # 学生成长档案（雷达图+统计）
│   │       └── upload_routes.py # 通用文件上传
│   │
│   ├── services/                 # 业务逻辑层
│   │   ├── auth_service.py       # 登录认证、注册
│   │   ├── chapter_service.py    # 章节查询 + 进度计算
│   │   ├── material_service.py   # 资料 CRUD
│   │   ├── question_service.py   # 题目 CRUD + Excel 导入 + 课程管理
│   │   ├── quiz_service.py       # 答题批改 + 进度更新 + 统计
│   │   ├── project_service.py    # 作品 CRUD + 点赞 + 审核
│   │   ├── teacher_service.py    # 教师仪表盘统计 + 学生数据
│   │   ├── class_service.py      # 班级 CRUD + 学生注册 + Excel 导入
│   │   ├── announcement_service.py     # 公告/任务 CRUD + 未读计数
│   │   ├── task_service.py       # 任务完成追踪 + 完成报告
│   │   └── portfolio_service.py  # 成长档案数据聚合
│   │
│   ├── models/
│   │   └── entities.py           # 所有 SQLAlchemy ORM 模型集中定义（11 张表）
│   │
│   ├── schemas/
│   │   └── common.py             # 所有 Pydantic 请求/响应 Schema 集中定义
│   │
│   ├── core/
│   │   ├── config.py             # 读取 .env 配置
│   │   ├── security.py           # JWT 签发/校验 + 密码哈希 + 角色依赖
│   │   ├── exceptions.py         # 自定义业务异常
│   │   ├── response.py           # 统一响应格式 {"code": 0, "data": ..., "message": "ok"}
│   │   └── upload_validation.py  # 文件上传安全校验（类型白名单 + 大小限制）
│   │
│   └── db/
│       └── session.py            # SQLAlchemy 引擎 + 会话工厂
│
├── migrations/
│   ├── env.py                    # Alembic 迁移环境（自动读 .env 数据库配置）
│   └── script.py.mako            # 迁移脚本模板
│
├── tests/
│   ├── conftest.py               # 测试夹具：SQLite 内存库 + TestClient + 种子数据
│   └── test_auth.py              # 集成测试（14 例）：认证、章节、答题
│
├── docs/
│   └── 项目修改记录.md            # 项目演进历史
│
└── uploads/                      # 上传文件存储目录（运行时自动创建）
```

---

## 运行方式

```bash
cd backend

# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置数据库（复制 .env 并填写 MySQL 连接信息）
#   DATABASE_URL=mysql+pymysql://root:密码@127.0.0.1:3306/tongshi?charset=utf8mb4

# 3. 初始化数据库（建库 + 建表 + 种子数据）
py database_setup.py

# 4. 启动服务（端口 8050）
py main.py
```

启动后访问：
- API 文档：http://127.0.0.1:8050/docs
- 健康检查：http://127.0.0.1:8050/health

---

## 核心设计

### 请求处理流程

```
Client 请求
  → FastAPI Router（路由层：鉴权 + 参数校验 + 调用 Service）
    → Service（业务逻辑层：组装数据 + 调用 Model）
      → SQLAlchemy Model（数据层：ORM 映射到 MySQL 表）
        → 响应：统一格式 {"code":0, "data":{...}, "message":"ok"}
```

### 统一响应格式

所有接口 HTTP 状态码统一为 200，通过 `code` 字段区分成功/失败：

```json
// 成功
{ "code": 0, "data": {...}, "message": "ok" }

// 业务失败（如重复注册）
{ "code": 400, "data": null, "message": "该学号已注册" }

// 权限不足
{ "code": 403, "data": null, "message": "需要teacher权限" }
```

### 鉴权方案

- JWT（HS256），token 有效期 `ACCESS_TOKEN_EXPIRE_MINUTES`（默认 7 天）
- 密码存储：`pbkdf2_sha256` 加密
- 角色：`student`（学生）和 `teacher`（教师），通过 `require_role("teacher")` 依赖注入控制

### 数据库表（11 张）

| 表名 | 用途 |
|------|------|
| `users` | 用户（学生/教师），id=学号/工号 |
| `courses` | 课程 |
| `chapters` | 章节（6 章），含排课时间 |
| `materials` | 学习资料（视频/PDF） |
| `questions` | 题库（选择题/填空题） |
| `quiz_attempts` | 答题记录 |
| `student_progress` | 学生学习进度（按章节） |
| `projects` | 学生 AI 项目作品 |
| `project_likes` | 作品点赞关系 |
| `classes` | 班级 |
| `student_class_enrollment` | 学生-班级注册关系 |
| `announcements` | 公告/测验任务 |
| `announcement_reads` | 公告已读记录 |
| `task_completions` | 任务完成记录 |
| `activity_events` | 课程活动时间线 |

### 开发约定

- 新增 ORM 模型 → 追加到 `app/models/entities.py`
- 新增 Pydantic Schema → 追加到 `app/schemas/common.py`
- 新增路由 → 在 `app/api/v1/routes/` 新建，在 `__init__.py` 注册
- 新增业务逻辑 → 在 `app/services/` 新建
- 错误返回 → 抛出 `BusinessException(code, message)`
- 数据库迁移 → `alembic revision --autogenerate -m "说明"` 然后 `alembic upgrade head`

---

## 运行测试

```bash
cd backend
python -m pytest tests/ -v
```

14 个测试用例覆盖认证、章节、答题核心链路，使用 SQLite 内存数据库（无需 MySQL）。

---

## 其他命令

```bash
# 重置数据库（清空建表 + 重新种子）
py database_setup.py --reset

# 检查数据库连接
py database_setup.py --check

# 生成数据库迁移脚本（修改模型后使用）
alembic revision --autogenerate -m "描述本次变更"

# 执行迁移
alembic upgrade head
```
