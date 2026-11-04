# 01: Foundation, Custom User Auth (JWT 3h), Groups, Role Assignment & Loguru Logging

**What to build:** Establish the DicoEvent backend foundation so Users can register and authenticate with 3-hour JWT tokens, the pre-seeded Superuser (`Aras`) can log in immediately, Superusers can manage role Groups (`admin`, `organizer`) and assign roles to Users, Admins and Superusers can administer Users while standard Users are blocked from listing all Users, and all `INFO` and `ERROR` operational events are recorded to daily-rotated Loguru log files (`application.log` and `error.log`).

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] Project dependencies are declared in a Pipfile targeting Django LTS 4.2 and Django REST Framework, and backing services (PostgreSQL, Redis, MinIO, Mailpit) are defined for local development.
- [x] PostgreSQL connection settings are read from `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, and `DATABASE_PORT` environment variables.
- [x] Custom `User` entity uses a UUID primary key (`id`), enforces a unique constraint on `email`, and stores `username`, `password`, `first_name`, and `last_name`.
- [x] Pre-seeded Superuser (`username="Aras"`, `password="1234qwer!@#$"`) is available out of the box and can log in via `POST /api/login/` to receive `200 OK` with `access` and `refresh` JWT tokens.
- [x] JWT authentication is configured as the default authentication scheme with a 3-hour access token lifetime, and `POST /api/token/` exchanges a valid `refresh` token for a new `access` token (`200 OK`).
- [x] `POST /api/users/` registers a new User without requiring authentication and returns `201 Created` with string UUID `id` and `username`.
- [x] `GET /api/users/` returns `200 OK` with `{"users": [...]}` for `Admin` and `Superuser`, and returns `403 Forbidden` when requested by a standard `User`.
- [x] `GET /api/users/<id>/` returns `200 OK` with `id`, `username`, `email`, `first_name`, and `last_name` (including unauthenticated `GET` retrieve requests per ADR-0001).
- [x] `PUT /api/users/<id>/` updates the User's `username` and `password` (`200 OK`), and `DELETE /api/users/<id>/` by an `Admin` or `Superuser` returns `204 No Content` with subsequent detail lookups returning `404 Not Found`.
- [x] `Superuser` can create (`POST /api/groups/` -> `201 Created` with numeric `id > 0` and `name`), list (`GET /api/groups/` -> `200 OK` with `{"groups": [...]}`), update (`PUT /api/groups/<id>/` -> `200 OK`), and delete (`DELETE /api/groups/<id>/` -> `204 No Content`, subsequent `GET` -> `404 Not Found`) role Groups.
- [x] `POST /api/assign-roles/` with `{"user_id", "group_id"}` succeeds with `201 Created` for a `Superuser` and returns `403 Forbidden` when attempted by an `Admin` or standard `User`.
- [x] Loguru is configured with the format `{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}`, writing `INFO` logs to `application.log` and `ERROR` logs to `error.log` with 1-day file rotation.
- [x] Automated HTTP API tests verify all `[Mandatory] Users`, `[Mandatory] Groups`, and `[Mandatory] Admin` Postman scenarios plus Loguru log output.
