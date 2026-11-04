# 05: Redis Caching & Mutation Cache Invalidation for Events

**What to build:** Accelerate Event browsing by caching both the Event detail and Event list endpoints in Redis for 1 hour (`3600` seconds), exposing cache provenance via the `X-Data-Source` response header (`database` vs `cache`), and automatically invalidating cached Event data whenever an Event is created, updated, or deleted.

**Blocked by:** 04: Event Poster Upload & MinIO Object Storage

**Status:** resolved

- [x] Redis cache connection is configured using the `REDIS_HOST` environment variable with a cache TTL of 1 hour (`3600` seconds).
- [x] On a cache miss for `GET /api/events/` or `GET /api/events/<id>/`, the API fetches data from PostgreSQL, populates Redis for 1 hour, and returns `200 OK` with response header `X-Data-Source: database`.
- [x] On a subsequent request (cache hit) for `GET /api/events/` or `GET /api/events/<id>/`, the API serves the cached response with `200 OK` and response header `X-Data-Source: cache`.
- [x] Creating an Event (`POST /api/events/`) invalidates the Event list cache so the next `GET /api/events/` returns `X-Data-Source: database` and includes the newly created Event, followed by `X-Data-Source: cache` on subsequent reads.
- [x] Updating an Event (`PUT /api/events/<id>/`) invalidates both that Event's detail cache and the Event list cache so the next `GET /api/events/<id>/` and `GET /api/events/` return `X-Data-Source: database` with updated data, followed by `X-Data-Source: cache` on subsequent reads.
- [x] Deleting an Event (`DELETE /api/events/<id>/`) invalidates both that Event's detail cache and the Event list cache so the next `GET /api/events/<id>/` returns `404 Not Found` (not served from cache) and the next `GET /api/events/` returns `X-Data-Source: database` without the deleted Event.
- [x] Automated HTTP API tests verify the complete 15-step `[Optional] Caching Events` and `[Mandatory] Events` caching Postman sequence.
