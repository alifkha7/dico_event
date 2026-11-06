# 02: Deepened Events & Event Posters Domain Application (`events`)

**What to build:** Extract **Event** and **Event Poster** into a dedicated `events` Django application (`db_table = "events"` and `"event_posters"`), deepen **Event** caching behind a declarative `CachedEventViewSetMixin` seam that automatically manages Redis list/detail caching, `X-Data-Source` (`cache` vs `database`) headers, and cache invalidation on mutations, and deepen **Event Poster** intake behind an `attach_event_poster` module that enforces **Organizer** ownership, validates 500 KB and Pillow image integrity, uploads media to MinIO (`upload_poster_to_minio`), and persists the **Event Poster** record.

**Blocked by:** 01: Core Infrastructure (`core`) & Users Domain Application (`users`) Cutover

**Status:** ready-for-agent

- [ ] The `events` application is registered in Django's installed applications under the `events` label and owns the **Event** (`db_table = "events"`, with database indexes on `start_time`, `status`, and `category`) and **Event Poster** (`db_table = "event_posters"`) models and their initial migration.
- [ ] **Event** serialization uses `DualKeyModelSerializer` for `organizer` / `organizer_id` resolution, and **Event** permissions use the declarative RBAC/ownership policy (allowing public list/retrieve, **Admin**/**Superuser** full access, and **Organizer** ownership on mutations).
- [ ] `CachedEventViewSetMixin` in the `events` caching module encapsulates list and detail cache reads/writes, query-string normalization, `X-Data-Source` response header injection (`cache` or `database`), and automatic cache invalidation across create, update, and destroy operations, leaving `EventViewSet` free of manual cache orchestration.
- [ ] The `events` storage module provides `attach_event_poster` alongside `upload_poster_to_minio`, `get_minio_client`, and `parse_minio_endpoint`, encapsulating **Organizer** ownership verification, MinIO object upload, and **Event Poster** persistence; both poster upload and poster list views serialize responses via `EventPosterSerializer`.
- [ ] All **Event**, **Event** caching, and **Event Poster** test suites are updated to import from the `events` application, and the entire test suite and `ruff` checks pass.
