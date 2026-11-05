# 02: Automated OpenAPI 3.0 Documentation (drf-spectacular)

**What to build:** Configure `drf-spectacular` as the default DRF schema generator and expose public (`AllowAny`) endpoints for the OpenAPI 3.0 schema (`/api/schema/`), interactive Swagger UI (`/api/docs/`), and Redoc documentation (`/api/redoc/`), with clean serializer and view metadata so the entire DicoEvent API is self-documented and browsable without errors.

**Blocked by:** 01: Database Query Optimization, Indexing & django-silk Profiling

**Status:** ready-for-agent

- [ ] `drf-spectacular` is added to project dependencies and configured as the `DEFAULT_SCHEMA_CLASS` in Django REST Framework settings with `SPECTACULAR_SETTINGS` metadata (`title="DicoEvent API"`, `version="2.0.0"`, `SERVE_INCLUDE_SCHEMA=False`).
- [ ] Unauthenticated `GET` requests to `/api/schema/`, `/api/docs/`, and `/api/redoc/` (with or without trailing slashes per ADR-0001) return `200 OK`.
- [ ] The generated OpenAPI 3.0 schema contains documented paths for `/api/login/`, `/api/token/`, `/api/users/`, `/api/groups/`, `/api/assign-roles/`, `/api/events/`, `/api/events/upload/`, `/api/tickets/`, `/api/registrations/`, and `/api/payments/` without schema generation errors.
- [ ] Automated tests verify `GET /api/schema/`, `GET /api/docs/`, and `GET /api/redoc/` responses and schema completeness.
