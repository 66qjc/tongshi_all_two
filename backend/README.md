# AI 通识课平台后端

后端采用 FastAPI + SQLAlchemy，提供前端所需的认证、课程、题库、资料、教师端、管理员端等 API。

## 目录

```text
backend/
├── main.py
├── database_setup.py
├── seed_data.py
├── scripts/
│   └── create_admin.py
├── app/
│   ├── api/v1/routes/
│   ├── services/
│   ├── models/
│   ├── schemas/
│   ├── core/
│   └── db/
└── tests/
```

## 本地启动

```bash
cd backend
pip install -r requirements.txt
py database_setup.py
py main.py
```

启动后访问：

- API 文档：`http://127.0.0.1:8050/docs`
- 健康检查：`http://127.0.0.1:8050/health`

## 部署前必须配置

`.env` 中至少应显式配置：

```env
SECRET_KEY=请替换为至少32位随机字符串
DATABASE_URL=mysql+pymysql://root:密码@127.0.0.1:3306/tongshi?charset=utf8mb4
ALLOW_QUERY_TOKEN_FOR_FILES=false
```

说明：

- `SECRET_KEY` 不再有默认值，未配置时后端禁止启动。
- `ALLOW_QUERY_TOKEN_FOR_FILES` 默认建议为 `false`。
- 公开业务接口必须使用 `Authorization` 请求头；仅文件预览兼容场景才允许按配置启用 URL token。

## 管理员初始化

系统不会再通过 `seed_data.py` 自动创建默认管理员。

部署完成后，运维需要显式执行一次管理员初始化命令：

```bash
cd backend
py scripts/create_admin.py --id admin001 --name 系统管理员 --password "强密码"
```

行为说明：

- 若账号不存在，则创建 `role=admin` 用户，并标记 `needs_password_change=True`
- 若账号已存在，则提示跳过，不重复创建

## 安全约束

- `/api/register` 只允许注册学生或教师，不能注册 `admin`
- `SECRET_KEY` 必须显式配置
- 默认种子数据不得包含管理员或其他高权限默认账号
- 普通接口不接受 `?token=` 方式鉴权

## 测试

```bash
cd backend
py -m pytest tests/ -q
```

测试使用 SQLite 内存数据库，不依赖 MySQL。

## 上线前检查

- 已配置强随机 `SECRET_KEY`
- 数据库中不存在默认管理员账号
- 已手工执行 `scripts/create_admin.py`
- `/api/register` 无法创建 `admin`
- 文件预览链路正常，普通接口不接受 URL token
