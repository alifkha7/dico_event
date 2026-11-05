# DevEx, Containerization, and Query Profiling Architecture

To provide interactive SQL query inspection without breaking deterministic query-count assertions (`django_assert_num_queries`), `django-silk` (`SilkyMiddleware`) is enabled in development/Docker (`ENABLE_SILK=True`, exposed at `/silk/`) but bypassed by default during `pytest` runs unless explicitly enabled by a test. Because `SilkyMiddleware` persists request and SQL telemetry rows into its own database tables on every request, keeping it active during standard test runs would inflate SQL query counts and mask N+1 query regressions.

In addition, the project standardizes on:
1. **Ruff (`pyproject.toml`)** as the single linter and formatter (`E`, `F`, `I`, `W`, line-length `120`, excluding `migrations/`), verified alongside `pytest` (backed by PostgreSQL and Redis service containers) in GitHub Actions (`.github/workflows/ci.yml`).
2. **`drf-spectacular`** for automated OpenAPI 3.0 schema generation (`/api/schema/`) and public interactive documentation (`/api/docs/` Swagger UI and `/api/redoc/` Redoc).
3. **Unified `Dockerfile` (`python:3.12-slim`) with `gunicorn` and `whitenoise`** shared across the `web` and `celery` services in `docker-compose.yml` so static UI assets (`/api/docs/`, `/api/redoc/`, `/silk/`, `/admin/`) render without external web server dependencies.
