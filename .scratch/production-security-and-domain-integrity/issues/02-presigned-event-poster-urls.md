# 02: Presigned `Event Poster` URLs with Public Endpoint Signing

**What to build:** Expose a directly renderable, time-limited `image_url` field alongside `image` and `event` on `Event Poster` upload and listing responses, signed locally against the configured public MinIO endpoint (`MINIO_PUBLIC_ENDPOINT_URL`, falling back to `MINIO_ENDPOINT_URL`) so browser clients on the host machine or in production can load poster images without manual URL construction or extra network round-trips.

**Blocked by:** 01: Milestone Tag, Modular Environment Settings (`base`, `dev`, `prod`, `test`), and CORS Whitelisting

**Status:** ready-for-agent

- [ ] Uploading an `Event Poster` (`POST /api/events/upload/`) and listing `Event Poster`s (`GET /api/events/<id>/posters/` and `GET /api/event-posters/`) return `id`, `image` (the stored object key), `image_url` (a presigned GET URL with configurable expiry defaulting to 3600 seconds), and `event`.
- [ ] Presigned URL generation uses `MINIO_PUBLIC_ENDPOINT_URL` when configured (falling back to `MINIO_ENDPOINT_URL`) with an explicit default region so cryptographic signing executes locally without requiring a network call to MinIO, and Docker Compose configures `MINIO_PUBLIC_ENDPOINT_URL` for host browser resolution.
- [ ] If presigned URL generation encounters a configuration or client error, the error is logged as a warning via Loguru and `image_url` gracefully falls back to `null` instead of failing the HTTP request with `500 Internal Server Error`.
- [ ] Automated HTTP API tests verify `image_url` presence, public endpoint host substitution, expiry configuration, and graceful `null` fallback.
