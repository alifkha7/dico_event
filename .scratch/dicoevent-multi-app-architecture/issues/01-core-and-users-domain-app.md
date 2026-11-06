# 01: Core Infrastructure (`core`) & Users Domain Application (`users`) Cutover

**What to build:** Establish the shared `core` Django application (providing the `/api/` URL aggregator, public OpenAPI schema/Swagger/Redoc routes, declarative `DualKeyModelSerializer`, declarative `RoleOwnershipPermission`, `PartialUpdateMixin`, custom exception handling, and Loguru logging setup) alongside the dedicated `users` Django application (`AUTH_USER_MODEL = "users.User"`, `db_table = "users"`, seeded `Aras` **Superuser**, **User** and **Group** management, role assignment, and 3-hour JWT authentication). While other domain applications are still being extracted in subsequent tickets, keep temporary re-exports in the legacy package so the full test suite remains green throughout the expand phase.

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] The `core` and `users` applications are registered in Django's installed applications under their canonical short labels (`core` and `users`), and `AUTH_USER_MODEL` is configured as `"users.User"`.
- [x] The `core` application provides a model-agnostic `DualKeyModelSerializer` base module that resolves `<field>` or `<field>_id` inputs using caller-supplied querysets and outputs both `<field>` and `<field>_id` as strings.
- [x] The `core` application provides a declarative `RoleOwnershipPermission` module enforcing ADR-0001 unauthenticated detail `retrieve`, **Superuser** and **Admin** access, and **Organizer** / **User** resource ownership rules, alongside `PartialUpdateMixin`, custom exception handling, and Loguru logging configuration.
- [x] The `users` application owns the **User** model (`db_table = "users"`), its initial schema migration, and the data migration seeding the `Aras` **Superuser**, as well as **User** CRUD (`prefetch_related("groups")`), **Group** CRUD (**Superuser** only), role assignment (`/api/assign-roles`), and JWT token endpoints (`/api/login`, `/api/token` with 3-hour access token lifetime).
- [x] The root URL configuration delegates `/api/` routing to the `core` URL aggregator, which mounts the public OpenAPI endpoints (`/api/schema/`, `/api/docs/`, `/api/redoc/`) and the `users` routes while keeping remaining routes operational.
- [x] Identity, authentication, **Group**, logging, and settings test suites are updated to import directly from the `core` and `users` applications, and the entire test suite and `ruff` checks pass.
