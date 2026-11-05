# 03: Full-Stack Docker Containerization (Dockerfile, Gunicorn, WhiteNoise & Compose)

**What to build:** Containerize the Django API and Celery worker using a unified `python:3.12-slim` image with `gunicorn` and `whitenoise` static file serving, add a `.dockerignore` configuration, and wire the `web` and `celery` services into Docker Compose alongside `postgres`, `redis`, `minio`, and `mailpit` with healthchecked dependencies so the entire DicoEvent stack launches with a single command.

**Blocked by:** 02: Automated OpenAPI 3.0 Documentation (drf-spectacular)

**Status:** ready-for-agent

- [ ] `gunicorn` and `whitenoise` are added to project dependencies, `WhiteNoiseMiddleware` is configured after `SecurityMiddleware`, and `STATIC_ROOT` is configured so static assets for Swagger UI, Redoc, Silk, and Django Admin are served directly by the application container.
- [ ] A root `Dockerfile` based on `python:3.12-slim` installs dependencies, collects static files, and provides an entrypoint that runs database migrations before starting `gunicorn`.
- [ ] A `.dockerignore` file excludes virtual environments, `.git`, `.pytest_cache`, `.scratch`, and local log files from the Docker build context.
- [ ] Docker Compose defines healthchecks for `postgres` and `redis` and adds the `web` (Django API on port `8000`) and `celery` (Celery worker) services configured to connect to `postgres`, `redis`, `minio`, and `mailpit`.
- [ ] Automated tests verify the static-files/WhiteNoise configuration, `Dockerfile`, `.dockerignore`, and Docker Compose service and dependency definitions.
