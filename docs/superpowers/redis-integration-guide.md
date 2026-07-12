# Redis 集成使用指南

## ✅ 已完成的基础集成

### 1. 依赖安装
- `requirements.txt` 已添加 `redis>=5.0.0`

### 2. 配置项
- `app/core/config.py` 已添加 Redis 配置类
- `.env.example` 已添加 Redis 配置示例

### 3. 核心模块
- `app/db/redis_client.py` - Redis 连接管理（单例模式）
- `app/core/cache.py` - 缓存装饰器和工具函数

---

## 🚀 如何使用

### 方法 1：使用装饰器缓存（推荐）

```python
from app.core.cache import cache_result

# 简单缓存（自动生成键）
@cache_result("teacher:info", ttl=600)
def get_teacher_info(teacher_id: int):
    # 第一次调用查询数据库
    # 后续调用返回缓存结果（10分钟内）
    return db.query(Teacher).filter(Teacher.id == teacher_id).first()

# 自定义缓存键
@cache_result("course:detail", ttl=180, key_builder=lambda course_id: str(course_id))
def get_course_detail(course_id: int):
    return db.query(Course).filter(Course.id == course_id).first()
```

### 方法 2：手动管理缓存

```python
from app.core.cache import get_cached, set_cached, invalidate_cache

# 读取缓存
cached_data = get_cached("course:public:list")
if cached_data is None:
    # 查询数据库
    cached_data = db.query(Course).filter(Course.is_public == True).all()
    # 写入缓存
    set_cached("course:public:list", cached_data, ttl=300)

# 删除缓存
invalidate_cache("course:detail:123")  # 删除单个
invalidate_cache("course:public:*")    # 删除所有公共课程缓存
```

---

## 📋 推荐的缓存场景

### 高优先级（立即应用）

#### 1. 公共课程列表
```python
# app/services/course_service.py
from app.core.cache import cache_result, invalidate_cache

@cache_result("course:public:list", ttl=300)
def get_public_courses():
    """获取公共课程列表（缓存5分钟）"""
    return db.query(Course).filter(Course.is_public == True).all()

# 管理员发布/修改公共课程时，删除缓存
def publish_public_course(course_id: int):
    # ... 更新数据库
    invalidate_cache("course:public:*")
```

#### 2. 教师信息
```python
# app/services/auth_service.py 或相关文件
from app.core.cache import cache_result

@cache_result("teacher:info", ttl=600, key_builder=lambda teacher_id: str(teacher_id))
def get_teacher_info(teacher_id: int):
    """获取教师信息（缓存10分钟）"""
    return db.query(User).filter(User.id == teacher_id, User.role == "teacher").first()
```

#### 3. 课程详情
```python
# app/services/course_service.py
@cache_result("course:detail", ttl=180, key_builder=lambda course_id: str(course_id))
def get_course_detail(course_id: int):
    """获取课程详情（缓存3分钟）"""
    return db.query(Course).filter(Course.id == course_id).first()

# 教师修改课程时，删除该课程缓存
def update_course(course_id: int, data: dict):
    # ... 更新数据库
    invalidate_cache(f"course:detail:{course_id}")
```

### 中优先级（可选）

#### 4. 作品点赞数
```python
from app.core.cache import get_cached, set_cached

def get_project_likes(project_id: int) -> int:
    """获取作品点赞数（缓存1分钟）"""
    cache_key = f"project:likes:{project_id}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    count = db.query(ProjectLike).filter(ProjectLike.project_id == project_id).count()
    set_cached(cache_key, count, ttl=60)
    return count

def like_project(project_id: int, user_id: int):
    """点赞（同步更新缓存）"""
    # ... 写入数据库
    cache_key = f"project:likes:{project_id}"
    invalidate_cache(cache_key)
```

#### 5. 消息未读数
```python
@cache_result("notification:unread", ttl=300, key_builder=lambda user_id: str(user_id))
def get_unread_count(user_id: int) -> int:
    """获取未读消息数（缓存5分钟）"""
    return db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).count()
```

---

## 🛠️ 服务器部署步骤

### Step 1：安装 Redis

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install redis-server -y

# 启动 Redis
sudo systemctl start redis
sudo systemctl enable redis

# 验证安装
redis-cli ping
# 应该返回：PONG
```

### Step 2：配置 Redis（生产环境）

```bash
# 编辑配置文件
sudo vim /etc/redis/redis.conf

# 修改以下配置：
# 1. 设置密码（推荐）
requirepass <强密码>

# 2. 限制访问（仅本地）
bind 127.0.0.1

# 3. 最大内存（建议 200-500MB）
maxmemory 256mb
maxmemory-policy allkeys-lru

# 重启 Redis
sudo systemctl restart redis
```

### Step 3：更新后端配置

```bash
# 编辑 .env
cd ~/tongshi_all_two/backend
vim .env

# 添加 Redis 配置
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=<你设置的密码>
REDIS_DB=0
REDIS_POOL_SIZE=10
REDIS_SOCKET_TIMEOUT=5
```

### Step 4：安装 Python 依赖

```bash
cd ~/tongshi_all_two/backend
source .venv/bin/activate
pip install redis>=5.0.0

# 或者
pip install -r requirements.txt
```

### Step 5：重启后端服务

```bash
sudo systemctl restart tongshi-backend

# 验证服务启动
sudo systemctl status tongshi-backend
sudo journalctl -u tongshi-backend -n 20
```

### Step 6：验证 Redis 连接

```bash
# 方法 1：使用 redis-cli
redis-cli -a <密码>
127.0.0.1:6379> keys *
(empty list or list of strings)

# 方法 2：测试接口
curl http://localhost:8050/api/courses/public
# 第一次：查询数据库（慢）
# 第二次：命中缓存（快）

# 方法 3：查看 Redis 命中率
redis-cli -a <密码> info stats | grep hit
```

---

## 📊 监控和调优

### 查看 Redis 状态

```bash
# 内存使用
redis-cli -a <密码> info memory | grep used_memory_human

# 缓存命中率
redis-cli -a <密码> info stats | grep keyspace

# 查看所有键
redis-cli -a <密码> keys "course:*"

# 查看键的 TTL
redis-cli -a <密码> ttl "course:public:list"
```

### 性能优化建议

```bash
# 1. 合理设置 TTL
高频访问：60-180 秒（如课程详情）
中频访问：300-600 秒（如公共课程列表）
低频访问：600-1800 秒（如教师信息）

# 2. 控制缓存大小
单个值不超过 1MB
总缓存大小控制在 200-500MB

# 3. 定期清理
使用 LRU 策略自动清理
或定期手动清理过期数据
```

---

## ⚠️ 注意事项

### 1. 降级策略
```python
# 所有缓存操作都有 try-except
# Redis 故障时自动降级到直接查询数据库
try:
    redis_client = get_redis_client()
    cached = redis_client.get(key)
    if cached:
        return json.loads(cached)
except Exception as e:
    logger.warning(f"Redis 查询失败，降级到 MySQL: {e}")

# 继续执行数据库查询
result = db.query(...)
```

### 2. 缓存一致性
```python
# 更新数据时必须删除对应缓存
def update_course(course_id: int, data: dict):
    # 1. 更新数据库
    db.query(Course).filter(Course.id == course_id).update(data)
    db.commit()

    # 2. 删除缓存（重要！）
    invalidate_cache(f"course:detail:{course_id}")
    invalidate_cache("course:public:*")  # 如果是公共课程
```

### 3. 不要缓存的数据
```bash
❌ 用户密码、Token
❌ 实时性要求高的数据（如在线人数）
❌ 经常变化的数据（如购物车）
❌ 大对象（> 1MB）
```

---

## 🎯 预期收益

### 性能提升

| 接口 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 公共课程列表 | 200ms | 20ms | 90% |
| 课程详情 | 150ms | 15ms | 90% |
| 教师信息 | 100ms | 10ms | 90% |

### 资源节约

- MySQL 查询频率降低 **60-80%**
- 服务器 CPU 使用率降低 **30-50%**
- 响应速度提升 **5-10 倍**

### 用户体验

- 页面加载更快
- 减少等待时间
- 提升并发能力

---

## 📝 后续任务

### 立即执行（必须）
1. ✅ 基础集成（已完成）
2. ⏳ 服务器安装 Redis
3. ⏳ 更新 .env 配置
4. ⏳ 安装 Python 依赖
5. ⏳ 重启后端服务

### 可选执行（推荐）
6. ⏳ 应用公共课程列表缓存
7. ⏳ 应用教师信息缓存
8. ⏳ 应用课程详情缓存
9. ⏳ 监控缓存命中率
10. ⏳ 性能测试验证

---

## 💡 常见问题

### Q1：Redis 挂了怎么办？
A：代码已实现自动降级，会直接查询 MySQL，不影响业务。

### Q2：缓存会不会太多？
A：使用 LRU 策略，配置了最大内存（256MB），自动淘汰旧数据。

### Q3：如何验证缓存生效？
A：
```bash
# 方法 1：查看日志
tail -f /var/log/tongshi_backend.log | grep "缓存"

# 方法 2：查看 Redis
redis-cli -a <密码> monitor

# 方法 3：接口响应时间对比
```

### Q4：如何清空所有缓存？
A：
```bash
# 谨慎使用！只在必要时清空
redis-cli -a <密码> flushdb
```

---

## 📚 相关文档

- [Redis 官方文档](https://redis.io/documentation)
- [redis-py 文档](https://redis-py.readthedocs.io/)
- [缓存最佳实践](https://redis.io/docs/manual/patterns/)
