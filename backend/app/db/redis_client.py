"""Redis 客户端封装"""
import redis
from typing import Optional
from app.core.config import settings


# 创建 Redis 连接池
_redis_pool: Optional[redis.ConnectionPool] = None
_redis_client: Optional[redis.Redis] = None


def get_redis_pool() -> redis.ConnectionPool:
    """获取 Redis 连接池（单例）"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password if settings.redis_password else None,
            db=settings.redis_db,
            decode_responses=True,
            socket_timeout=settings.redis_socket_timeout,
            max_connections=settings.redis_pool_size,
        )
    return _redis_pool


def get_redis_client() -> redis.Redis:
    """获取 Redis 客户端（单例）"""
    global _redis_client
    if _redis_client is None:
        pool = get_redis_pool()
        _redis_client = redis.Redis(connection_pool=pool)
    return _redis_client


def get_redis() -> redis.Redis:
    """获取 Redis 连接（依赖注入用）"""
    return get_redis_client()


def close_redis():
    """关闭 Redis 连接（应用关闭时调用）"""
    global _redis_client, _redis_pool
    if _redis_client:
        _redis_client.close()
        _redis_client = None
    if _redis_pool:
        _redis_pool.disconnect()
        _redis_pool = None
