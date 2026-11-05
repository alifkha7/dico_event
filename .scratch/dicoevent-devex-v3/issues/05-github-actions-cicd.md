/im# 05: GitHub Actions CI/CD Pipeline (.github/workflows/ci.yml)

**What to build:** Create an automated GitHub Actions CI/CD workflow triggered on `push` and `pull_request` that provisions PostgreSQL 15 and Redis 7 service containers, runs `ruff check .` and `ruff format --check .`, applies database migrations, and executes the complete `pytest` suite against the live PostgreSQL and Redis services.

**Blocked by:** 04: Unified Linting & Formatting with Ruff (pyproject.toml)

**Status:** ready-for-agent

- [ ] A GitHub Actions workflow is defined for `push` and `pull_request` events with health-checked `postgres:15-alpine` and `redis:7-alpine` service containers.
- [ ] The workflow installs project dependencies on Python 3.12, runs `ruff check .` and `ruff format --check .`, runs `python manage.py migrate`, and executes `pytest` with `USE_SQLITE_TEST=False` against the PostgreSQL and Redis service containers.
- [ ] Automated tests verify the structure, triggers, service containers, environment variables, and verification steps of the CI workflow, and confirm that any newly added test files pass `ruff check .` and `ruff format --check .`.
