from urllib.parse import parse_qsl, urlencode
from django.conf import settings
from django.core.cache import cache

CACHE_TTL = getattr(settings, 'CACHE_TTL', 3600)
EVENT_DETAIL_KEY_PREFIX = "events:detail:"
EVENT_LIST_KEY_PREFIX = "events:list:"
EVENT_LIST_REGISTRY_KEY = "events:list:registry"


def normalize_query_string(query_string: str) -> str:
    """Normalize query parameters in sorted order for deterministic cache keys."""
    if not query_string:
        return ""
    pairs = parse_qsl(query_string, keep_blank_values=True)
    pairs.sort()
    return urlencode(pairs)


def get_event_detail_cache_key(pk) -> str:
    """Return deterministic cache key for a single event detail."""
    return f"{EVENT_DETAIL_KEY_PREFIX}{str(pk).lower()}"


def get_event_list_cache_key(query_string: str) -> str:
    """Return deterministic cache key for an event list query."""
    normalized = normalize_query_string(query_string)
    return f"{EVENT_LIST_KEY_PREFIX}{normalized}"


def get_cached_event_detail(pk):
    """Retrieve event detail payload from cache if present."""
    if not pk:
        return None
    return cache.get(get_event_detail_cache_key(pk))


def set_cached_event_detail(pk, data):
    """Store event detail payload into cache for 1 hour."""
    if not pk:
        return
    key = get_event_detail_cache_key(pk)
    cache.set(key, data, timeout=CACHE_TTL)


def get_cached_event_list(query_string: str):
    """Retrieve event list payload from cache if present."""
    key = get_event_list_cache_key(query_string)
    return cache.get(key)


def set_cached_event_list(query_string: str, data):
    """Store event list payload into cache and register the key for bulk invalidation."""
    key = get_event_list_cache_key(query_string)
    registry = cache.get(EVENT_LIST_REGISTRY_KEY)
    if not isinstance(registry, set):
        registry = set()
    registry.add(key)
    cache.set(EVENT_LIST_REGISTRY_KEY, registry, timeout=CACHE_TTL)
    cache.set(key, data, timeout=CACHE_TTL)


def invalidate_event_detail_cache(pk):
    """Invalidate a specific event detail cache entry."""
    if pk:
        cache.delete(get_event_detail_cache_key(pk))


def invalidate_event_list_cache():
    """Invalidate all active event list cache entries across query variations."""
    registry = cache.get(EVENT_LIST_REGISTRY_KEY)
    if registry and isinstance(registry, (set, list)):
        for key in registry:
            cache.delete(key)
        cache.delete(EVENT_LIST_REGISTRY_KEY)

    # Invalidate by pattern if backed by django-redis
    if hasattr(cache, 'delete_pattern'):
        try:
            cache.delete_pattern(f"{EVENT_LIST_KEY_PREFIX}*")
        except Exception:
            pass


def invalidate_all_event_caches(pk=None):
    """Invalidate all event list cache entries and optionally a specific detail cache entry."""
    invalidate_event_list_cache()
    if pk:
        invalidate_event_detail_cache(pk)
