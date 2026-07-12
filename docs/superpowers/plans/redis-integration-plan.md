# Redis 集成实施计划

## 目标
为 tongshi 平台增加 Redis 缓存层，提升系统性能和并发能力。

## 背景
当前项目仅使用单个 MySQL 数据库，存在以下问题：
- 高频查询直接打 MySQL（如课程列表、教师信息）
- Session 管理完全依赖 JWT，无法实现强制登出
- 热点数据（点赞数、浏览数）写入压力大
- 大文件预览链接每次重新生成

## 方案设计

### 第一阶段：基础缓存（优先级高）

#### 1. 环境配置
**后端 requirements.txt 新增：**
```python
redis>=5.0.0
```

**backend/.env.example 新增配置：**
```bash
# Redis
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
REDIS_POOL_SIZE=10
REDIS_SOCKET_TIMEOUT=5
```

#### 2. Redis 连接封装
**新建文件：`backend/app/db/redis_client.py`**
```python
"""Redis 客户端封装"""
import redis
from app.core.config import settings

redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    password=settings.redis_password,
    db=settings.redis_db,
    decode_responses=True,
    socket_timeout=settings.redis_socket_timeout,
    max_connections=settings.redis_pool_size,
)

def get_redis():
    """获取 Redis 连接（依赖注入用）"""
    return redis_client
```

#### 3. 缓存装饰器
**新建文件：`backend/app/core/cache.py`**
```python
"""通用缓存装饰器"""
import json
from functools import wraps
from typing import Optional
from app.db.redis_client import redis_client

def cache_result(key_prefix: str, ttl: int = 300):
    """
    结果缓存装饰器
    Args:
        key_prefix: 缓存键前缀
        ttl: 过期时间（秒）
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{args}:{kwargs}"

            # 尝试从缓存读取
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)

            # 执行函数
            result = await func(*args, **kwargs)

            # 写入缓存
            redis_client.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator
```

#### 4. 应用场景优先级

**高优先级（立即实施）：**
1. **公共课程列表缓存**（管理员端、学生端）
   - 缓存键：`course:public:list`
   - TTL：300 秒（5 分钟）
   - 失效时机：管理员发布/修改公共课程

2. **教师信息缓存**（权限验证）
   - 缓存键：`teacher:info:{teacher_id}`
   - TTL：600 秒（10 分钟）
   - 失效时机：教师信息修改

3. **课程详情缓存**（学生端高频访问）
   - 缓存键：`course:detail:{course_id}`
   - TTL：180 秒（3 分钟）
   - 失效时机：教师修改课程

**中优先级（第二批）：**
4. **作品点赞数缓存**
   - 缓存键：`project:likes:{project_id}`
   - TTL：60 秒（1 分钟）
   - 更新策略：写入时同步更新缓存

5. **消息未读数**
   - 缓存键：`notification:unread:{user_id}`
   - TTL：300 秒（5 分钟）
   - 失效时机：新消息通知、用户已读

6. **资料预览链接缓存**
   - 缓存键：`material:preview:{file_id}`
   - TTL：3600 秒（1 小时）
   - 失效时机：文件删除

**低优先级（可选）：**
7. **成绩统计缓存**（教师端导出时）
8. **班级学生列表缓存**

### 第二阶段：Session 管理（可选）

#### Token 黑名单
实现强制登出功能：
```python
# 登出时将 Token 加入黑名单
redis_client.setex(f"token:blacklist:{token}", ttl, "1")

# 验证时检查黑名单
if redis_client.exists(f"token:blacklist:{token}"):
    raise AuthException("Token 已失效")
```

### 第三阶段：分布式锁（未来扩展）

处理并发场景：
- 作品点赞防重复
- 任务提交防并发
- 文件上传防冲突

## 实施步骤

### Step 1：服务器安装 Redis
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install redis-server

# 启动 Redis
sudo systemctl start redis
sudo systemctl enable redis

# 验证
redis-cli ping
# 返回 PONG 说明成功
```

### Step 2：后端代码修改
1. 修改 `backend/requirements.txt` 新增 redis
2. 修改 `backend/app/core/config.py` 新增 Redis 配置项
3. 新建 `backend/app/db/redis_client.py`
4. 新建 `backend/app/core/cache.py`
5. 修改 `backend/.env.example` 新增 Redis 配置模板
6. 修改 `backend/.env` 配置实际 Redis 连接（不提交）

### Step 3：应用缓存（逐个接口改造）
从高优先级场景开始，逐个改造：
1. `backend/app/api/v1/routes/courses.py` - 公共课程列表
2. `backend/app/services/course_service.py` - 课程详情查询
3. `backend/app/services/project_service.py` - 点赞数统计
4. ...

### Step 4：本地测试
```bash
# 启动 Redis
redis-server

# 测试缓存效果
# 第一次请求：查询 MySQL
# 第二次请求：命中缓存（响应时间明显降低）

# 查看 Redis 键
redis-cli keys "course:*"
```

### Step 5：服务器部署
```bash
# 1. 安装 Redis
sudo apt install redis-server

# 2. 配置 Redis（生产环境建议设置密码）
sudo vim /etc/redis/redis.conf
# 修改：requirepass <强密码>

# 3. 重启 Redis
sudo systemctl restart redis

# 4. 更新后端 .env
cd /path/to/backend
vim .env
# 新增 Redis 配置

# 5. 安装依赖
pip install -r requirements.txt

# 6. 重启后端服务
# 如果使用 systemd
sudo systemctl restart tongshi-backend

# 如果使用 supervisor
sudo supervisorctl restart tongshi-backend
```

## 验收标准

### 功能验收
- [ ] Redis 连接正常（`redis-cli ping` 返回 PONG）
- [ ] 公共课程列表第二次请求明显加速
- [ ] 课程详情缓存生效（检查 Redis keys）
- [ ] 管理员修改课程后缓存自动失效

### 性能验收
- [ ] 课程列表接口响应时间从 200ms 降低到 50ms 以内
- [ ] 课程详情接口响应时间从 150ms 降低到 30ms 以内
- [ ] MySQL 查询频率降低 60% 以上

### 稳定性验收
- [ ] Redis 连接失败时自动降级到直接查询 MySQL
- [ ] 缓存雪崩测试（批量失效不影响服务）
- [ ] 服务器重启后 Redis 数据自动恢复

## 风险和注意事项

### 风险
1. **缓存一致性**：更新数据时必须同步删除缓存
2. **缓存穿透**：查询不存在的数据绕过缓存直击 MySQL
3. **Redis 故障**：需要降级策略

### 降级方案
所有缓存查询必须有降级逻辑：
```python
try:
    cached = redis_client.get(key)
    if cached:
        return json.loads(cached)
except Exception as e:
    logger.warning(f"Redis 查询失败，降级到 MySQL: {e}")

# 降级到 MySQL 查询
result = db.query(...)
```

### 监控指标
- Redis 命中率（目标 > 80%）
- Redis 连接数
- 平均响应时间

## 成本估算

### 服务器资源
- Redis 内存：预计 512MB - 1GB（小型平台）
- CPU：几乎无影响
- 磁盘：RDB 持久化需要 < 1GB

### 开发成本
- 基础集成：2 小时
- 高优先级缓存（3 个场景）：4 小时
- 测试验证：2 小时
- **总计：1 个工作日**

### 运维成本
- Redis 运维难度低，几乎零维护
- 定期检查内存使用率即可

## 时间表

| 阶段 | 内容 | 预计时间 |
|------|------|----------|
| 准备 | 服务器安装 Redis | 0.5 小时 |
| 开发 | 基础集成 + 高优先级缓存 | 6 小时 |
| 测试 | 本地测试 + 性能验证 | 2 小时 |
| 部署 | 服务器配置 + 重启服务 | 1 小时 |
| **合计** | | **1.2 个工作日** |

## 总结

**推荐立即实施 Redis 集成，原因：**
1. ✅ 开发成本低（1 天）
2. ✅ 性能提升明显（接口响应时间降低 60%+）
3. ✅ 运维成本低（几乎零维护）
4. ✅ 未来扩展性好（支持 Session、分布式锁）
5. ✅ 教育平台的读多写少特性非常适合缓存

**不推荐的方案：**
- ❌ 继续单 MySQL：并发能力受限，性能瓶颈明显
- ❌ MongoDB：项目数据结构化，MySQL 已满足需求
- ❌ Elasticsearch：暂无全文搜索需求，过度设计
