# 02: Events CRUD, Organizer Ownership RBAC & Paginated Queries

**What to build:** Enable Superusers, Admins, and Organizers to publish and manage Events with UUID identifiers, allow Users to browse and inspect Events with pagination (`?page=1`), filtering, and ordering, and enforce resource-ownership RBAC so Organizers can modify or delete only the Events they personally own.

**Blocked by:** 01: Foundation, Custom User Auth (JWT 3h), Groups, Role Assignment & Loguru Logging

**Status:** resolved

- [x] `Event` entity uses a UUID primary key (`id`) and stores `name`, `description`, `location`, `start_time`, `end_time`, `status`, `quota` (integer), `category`, and `organizer` (referencing `User`).
- [x] `POST /api/events/` by a `Superuser`, `Admin`, or `Organizer` creates an Event and returns `201 Created` with `id` (UUID string), `name`, `description`, `location`, `start_time`, `end_time`, `status`, `category`, and `quota` (number).
- [x] `GET /api/events/` returns `200 OK` with `{"events": [...]}` and supports advanced ORM query parameters including `?page=1` pagination, filtering, and ordering while preserving the `{"events": [...]}` envelope.
- [x] `GET /api/events/<id>/` returns `200 OK` with the Event's full attributes (including unauthenticated `GET` retrieve requests per ADR-0001) and `404 Not Found` if the Event does not exist.
- [x] `PUT /api/events/<id>/` and `DELETE /api/events/<id>/` succeed (`200 OK` and `204 No Content`) when called by a `Superuser` or `Admin` on any Event, or by an `Organizer` on an Event where `organizer_id` matches the authenticated Organizer's User ID.
- [x] `PUT /api/events/<id>/` and `DELETE /api/events/<id>/` return `403 Forbidden` when an `Organizer` attempts to modify or delete an Event owned by another Organizer.
- [x] Automated HTTP API tests verify all `[Mandatory] Events`, `[Optional] Events`, and `[Optional] Organizer` Postman scenarios.
