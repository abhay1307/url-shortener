import redis

from app.config import settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client


def cache_url(code: str, original_url: str, ttl: int = 86400) -> None:
    """Cache short_code → original_url mapping for 24 hours by default."""
    try:
        get_redis().set(f"url:{code}", original_url, ex=ttl)
    except Exception as e:
        print(f"[Cache] Write failed for {code}: {e}")


def get_cached_url(code: str) -> str | None:
    """Return cached original URL or None on miss/error."""
    try:
        return get_redis().get(f"url:{code}")
    except Exception as e:
        print(f"[Cache] Read failed for {code}: {e}")
        return None


def delete_cached_url(code: str) -> None:
    try:
        get_redis().delete(f"url:{code}")
    except Exception as e:
        print(f"[Cache] Delete failed for {code}: {e}")


def get_cache_stats() -> dict:
    try:
        r = get_redis()
        info = r.info()
        return {
            "hit_rate": round(
                info.get("keyspace_hits", 0)
                / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1), 1)
                * 100,
                1,
            ),
            "total_keys": info.get("db0", {}).get("keys", 0) if "db0" in info else 0,
            "memory_used": info.get("used_memory_human", "N/A"),
        }
    except Exception:
        return {"hit_rate": 0, "total_keys": 0, "memory_used": "N/A"}
