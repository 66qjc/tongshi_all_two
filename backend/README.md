# AI 通识课平台后端

后端采用 FastAPI + SQLAlchemy，提供前端所需的认证、课程、题库、资料、教师端、管理员端等 API。

## 目录

```text
backend/
├── main.py
├── database_setup.py
├── seed_data.py
├── scripts/
│   ├── check_deploy_env.py
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
DATABASE_URL=mysql+pymysql://tongshi_user:强密码@127.0.0.1:3306/tongshi?charset=utf8mb4
ALLOWED_ORIGINS=https://你的前端域名
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=5
DB_POOL_RECYCLE=3600
DB_POOL_TIMEOUT=30
STORAGE_BACKEND=local
LOCAL_UPLOAD_DIR=/data/tongshi/uploads
ALLOW_QUERY_TOKEN_FOR_FILES=false
```

说明：

- `SECRET_KEY` 不再有默认值，未配置时后端禁止启动。
- 第一阶段上线默认使用 `STORAGE_BACKEND=local`，把 `LOCAL_UPLOAD_DIR` 指向服务器持久化目录，并确保运行后端的系统用户可读写。
- `ALLOW_QUERY_TOKEN_FOR_FILES` 默认建议为 `false`。
- 公开业务接口必须使用 `Authorization` 请求头；仅文件预览兼容场景才允许按配置启用 URL token。
- 使用本地文件存储时，`LOCAL_UPLOAD_DIR` 如有配置，必须指向实际上传目录；未配置时默认使用 `backend/uploads`。
- 如果生产环境通过浏览器新窗口、iframe 或 video 标签访问 `/api/files/{id}`，需要启用 `ALLOW_QUERY_TOKEN_FOR_FILES=true`，普通业务接口仍不会接受 URL token。
- S3/SeaweedFS/MinIO 属于第二阶段对象存储接入任务；只有确认 S3 端点、bucket、权限和备份策略后，才把 `STORAGE_BACKEND` 切换为 `s3`。

## 部署检查

配置 `.env` 后先执行只读检查：

```bash
cd backend
py scripts/check_deploy_env.py
```

检查内容包括：

- `SECRET_KEY` 至少 32 位
- `ALLOWED_ORIGINS` 不能为 `*`
- `DATABASE_URL` 不能使用 `root:123456` 默认账号口令
- MySQL 端口可连接
- `STORAGE_BACKEND=local` 时上传目录存在且可写
- `STORAGE_BACKEND=s3` 时 S3 端点必须配置且可连接

如只想在离线环境验证配置格式，可临时使用：

```bash
py scripts/check_deploy_env.py --skip-mysql --skip-s3
```

## 生产启动

本地开发可以继续使用 `py main.py`。生产环境不要使用 `reload=True` 的开发入口，建议使用：

```bash
cd backend
py -m uvicorn main:app --host 127.0.0.1 --port 8050 --workers 4
```

Nginx 按仓库根目录 `deploy/nginx.conf` 托管前端构建产物，并反代 `/api/`、兼容 `/uploads/` 到后端 `8050`。

## 管理员初始化

管理员初始化由运维通过独立脚本执行，不依赖种子数据。

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
- Nginx 已按 `deploy/nginx.conf` 代理 `/api/` 和 `/uploads/` 到后端 `8050`
- 文件预览链路正常：PDF 新窗口查看不超时，视频 Range 请求返回 `206 Partial Content`
- 普通接口不接受 URL token；仅 `/api/files/{id}` 可按配置用于文件预览
