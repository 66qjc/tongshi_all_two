"""通用缓存装饰器和工具函数"""
import json
import logging
from functools import wraps
from typing import Optional, Callable, Any

from app.db.redis_client import get_redis_client

logger = logging.getLogger(__name__)


def cache_result(key_prefix: str, ttl: int = 300, key_builder: Optional[Callable] = None):
    """
    结果缓存装饰器

    Args:
        key_prefix: 缓存键前缀，例如 "course:public:list"
        ttl: 过期时间（秒），默认 300 秒（5 分钟）
        key_builder: 自定义缓存键生成函数，接收函数参数，返回键后缀

    Example:
        @cache_result("course:detail", ttl=180, key_builder=lambda course_id: f"{course_id}")
        def get_course_detail(course_id: int):
            return db.query(Course).filter(Course.id == course_id).first()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # 生成缓存键
            if key_builder:
                key_suffix = key_builder(*args, **kwargs)
                cache_key = f"{key_prefix}:{key_suffix}"
            else:
                # 默认使用参数的字符串表示
                args_str = "_".join(str(arg) for arg in args if arg is not None)
                kwargs_str = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()) if v is not None)
                key_suffix = f"{args_str}:{kwargs_str}" if args_str or kwargs_str else "default"
                cache_key = f"{key_prefix}:{key_suffix}"

            try:
                redis_client = get_redis_client()

                # 尝试从缓存读取
                cached = redis_client.get(cache_key)
                if cached:
                    logger.debug(f"缓存命中: {cache_key}")
                    return json.loads(cached)

                logger.debug(f"缓存未命中: {cache_key}")
            except Exception as e:
                logger.warning(f"Redis 查询失败，降级到直接查询: {e}")

            # 执行函数
            result = func(*args, **kwargs)

            # 写入缓存
            try:
                redis_client = get_redis_client()
                redis_client.set(cache_key, json.dumps(result, ensure_ascii=False), ex=ttl)
                logger.debug(f"缓存已写入: {cache_key}, TTL: {ttl}s")
            except Exception as e:
                logger.warning(f"Redis 写入失败: {e}")

            return result

        return wrapper
    return decorator


def invalidate_cache(key_pattern: str):
    """
    删除缓存

    Args:
        key_pattern: 缓存键模式，支持通配符 *

    Example:
        invalidate_cache("course:detail:123")  # 删除单个
        invalidate_cache("course:public:*")    # 删除所有公共课程缓存
    """
    try:
        redis_client = get_redis_client()

        # 如果是精确匹配，直接删除
        if "*" not in key_pattern:
            deleted = redis_client.delete(key_pattern)
            logger.info(f"缓存已删除: {key_pattern}")
            return deleted

        # 如果包含通配符，先查找再批量删除
        keys = redis_client.keys(key_pattern)
        if keys:
            deleted = redis_client.delete(*keys)
            logger.info(f"批量删除缓存: {len(keys)} 个键匹配 {key_pattern}")
            return deleted
        else:
            logger.debug(f"未找到匹配的缓存键: {key_pattern}")
            return 0
    except Exception as e:
        logger.error(f"删除缓存失败: {e}")
        return 0


def get_cached(key: str) -> Optional[Any]:
    """
    直接获取缓存值

    Args:
        key: 缓存键

    Returns:
        缓存的值，不存在返回 None
    """
    try:
        redis_client = get_redis_client()
        cached = redis_client.get(key)
        if cached:
            return json.loads(cached)
        return None
    except Exception as e:
        logger.warning(f"获取缓存失败: {e}")
        return None


def set_cached(key: str, value: Any, ttl: int = 300):
    """
    直接设置缓存值

    Args:
        key: 缓存键
        value: 要缓存的值（会被 JSON 序列化）
        ttl: 过期时间（秒）
    """
    try:
        redis_client = get_redis_client()
        redis_client.set(key, json.dumps(value, ensure_ascii=False), ex=ttl)
        logger.debug(f"缓存已设置: {key}, TTL: {ttl}s")
    except Exception as e:
        logger.warning(f"设置缓存失败: {e}")
