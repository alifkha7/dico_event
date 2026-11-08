# 01: Milestone Tag, Modular Environment Settings (`base`, `dev`, `prod`, `test`), and CORS Whitelisting

**What to build:** Preserve the Dicoding submission snapshot under Git tag `v2.0-dicoding-submission`, split the application's configuration into dedicated `base`, `dev`, `prod`, and `test` environment modules (with dynamic `DJANGO_ENV` package routing so container builds, CLI commands, and test runners resolve cleanly), enforce fail-fast production startup checks and HTTPS/cookie/HSTS security headers in `prod`, honor both fast in-memory local testing and PostgreSQL/Redis CI testing in `test`, and enable explicit `CORS_ALLOWED_ORIGINS` whitelisting for cross-origin browser requests.

**Blocked by:** None (can start immediately)

**Status:** claimed

- [ ] The pre-transition commit is tagged as `v2.0-dicoding-submission` in Git history.
- [ ] Application configuration is separated into `base`, `dev`, `prod`, and `test` modules, with root package imports routing via `DJANGO_ENV` (defaulting to `dev`) and `BASE_DIR` resolving to the repository root across all environments.
- [ ] Loading the `prod` settings module forces `DEBUG=False`, raises `ImproperlyConfigured` if `SECRET_KEY` is missing or uses the insecure default placeholder or if `ALLOWED_HOSTS` is missing, empty, or contains `"*"`, and enables `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, and HSTS settings by default (overridable via explicit environment flags).
- [ ] Loading the `test` settings module disables SQL profiling middleware by default, enables eager Celery execution and fast password hashing, defaults to in-memory SQLite and local-memory cache when `USE_SQLITE_TEST` is `True` (or omitted), and switches to PostgreSQL and Redis when `USE_SQLITE_TEST` is set to `False`.
- [ ] Cross-Origin Resource Sharing (`django-cors-headers`) is configured with `CorsMiddleware` placed immediately after `WhiteNoiseMiddleware` (preserving the `SecurityMiddleware` -> `WhiteNoiseMiddleware` ordering invariant) and enforces explicit `CORS_ALLOWED_ORIGINS` without wildcard exposure in production.
- [ ] Automated tests at the settings-loader seam and HTTP API seam verify `prod` fail-fast behavior, `test` backend switching, middleware ordering, and `Access-Control-Allow-Origin` response headers for allowed vs disallowed origins.
