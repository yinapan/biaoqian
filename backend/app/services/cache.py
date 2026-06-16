from cachetools import TTLCache
from app.config import settings

parse_cache: TTLCache = TTLCache(
    maxsize=settings.parse_cache_maxsize,
    ttl=settings.parse_cache_ttl,
)

tag_defs_cache: TTLCache = TTLCache(maxsize=100, ttl=settings.tag_cache_ttl)


def get_parse_cache_key(module_type: int, query: str) -> tuple:
    return (module_type, query)


def clear_all_caches():
    parse_cache.clear()
    tag_defs_cache.clear()
