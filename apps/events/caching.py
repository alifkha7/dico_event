from urllib.parse import parse_qsl, urlencode

from django.conf import settings
from django.core.cache import cache
from loguru import logger
from rest_framework import status
from rest_framework.response import Response

CACHE_TTL = getattr(settings, "CACHE_TTL", 3600)
EVENT_DETAIL_KEY_PREFIX = "events:detail:"
EVENT_LIST_KEY_PREFIX = "events:list:"
EVENT_LIST_REGISTRY_KEY = "events:list:registry"

__all__ = [
    "CACHE_TTL",
    "CachedEventViewSetMixin",
    "get_cached_event_detail",
    "get_cached_event_list",
    "get_event_detail_cache_key",
    "get_event_list_cache_key",
    "invalidate_all_event_caches",
    "invalidate_event_caches",
    "invalidate_event_detail_cache",
    "invalidate_event_list_cache",
    "normalize_query_string",
    "set_cached_event_detail",
    "set_cached_event_list",
]


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
    if hasattr(cache, "delete_pattern"):
        try:
            cache.delete_pattern(f"{EVENT_LIST_KEY_PREFIX}*")
        except Exception:
            pass


def invalidate_all_event_caches(pk=None):
    """Invalidate all event list cache entries and optionally a specific detail cache entry."""
    invalidate_event_list_cache()
    if pk:
        invalidate_event_detail_cache(pk)


# Spec Line 151: Invalidate both affected Event detail cache key and all Event list cache keys
invalidate_event_caches = invalidate_all_event_caches


class CachedEventViewSetMixin:
    """
    Deep seam mixin encapsulating Redis caching and automatic cache invalidation for Event views.
    Intercepts list and retrieve to serve cached data (X-Data-Source: cache)
    or database results (X-Data-Source: database).
    Intercepts perform_create, perform_update, and perform_destroy to automatically invalidate caches on mutations.
    """

    def list(self, request, *args, **kwargs):
        query_string = request.META.get("QUERY_STRING", "")
        cached_data = get_cached_event_list(query_string)
        if cached_data is not None:
            logger.info(f"Serving events list from cache (query: '{query_string}').")
            response = Response(cached_data, status=status.HTTP_200_OK)
            response["X-Data-Source"] = "cache"
            return response

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            logger.info(f"Listing events from database (paginated): count={self.paginator.page.paginator.count}")
            paginated_response = self.get_paginated_response(serializer.data)
            set_cached_event_list(query_string, paginated_response.data)
            paginated_response["X-Data-Source"] = "database"
            return paginated_response

        serializer = self.get_serializer(queryset, many=True)
        logger.info(f"Listing events from database: count={len(serializer.data)}")
        data = {"events": serializer.data}
        set_cached_event_list(query_string, data)
        response = Response(data, status=status.HTTP_200_OK)
        response["X-Data-Source"] = "database"
        return response

    def retrieve(self, request, *args, **kwargs):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        pk = kwargs.get(lookup_url_kwarg, kwargs.get("pk"))
        cached_data = get_cached_event_detail(pk)
        if cached_data is not None:
            logger.info(f"Serving event detail from cache (ID: {pk}).")
            response = Response(cached_data, status=status.HTTP_200_OK)
            response["X-Data-Source"] = "cache"
            return response

        instance = self.get_object()
        serializer = self.get_serializer(instance)
        set_cached_event_detail(pk, serializer.data)
        logger.info(f"Retrieved event from database: '{instance.name}' (ID: {instance.id})")
        response = Response(serializer.data, status=status.HTTP_200_OK)
        response["X-Data-Source"] = "database"
        return response

    def perform_create(self, serializer):
        super().perform_create(serializer)
        event = serializer.instance
        event_id = getattr(event, "id", None)
        invalidate_event_caches(event_id)
        username = (
            self.request.user.username
            if getattr(self, "request", None) and self.request.user and self.request.user.is_authenticated
            else "anonymous"
        )
        logger.info(f"Event created successfully: '{getattr(event, 'name', '')}' (ID: {event_id}) by user '{username}'")

    def perform_update(self, serializer):
        super().perform_update(serializer)
        event = serializer.instance
        event_id = getattr(event, "id", None)
        invalidate_event_caches(event_id)
        username = (
            self.request.user.username
            if getattr(self, "request", None) and self.request.user and self.request.user.is_authenticated
            else "anonymous"
        )
        logger.info(f"Event updated successfully: '{getattr(event, 'name', '')}' (ID: {event_id}) by user '{username}'")

    def perform_destroy(self, instance):
        event_id = str(instance.id)
        event_name = getattr(instance, "name", "")
        super().perform_destroy(instance)
        invalidate_event_caches(event_id)
        username = (
            self.request.user.username
            if getattr(self, "request", None) and self.request.user and self.request.user.is_authenticated
            else "anonymous"
        )
        logger.info(f"Event deleted successfully: '{event_name}' (ID: {event_id}) by user '{username}'")
