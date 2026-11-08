# 03: Scoped RBAC Visibility for `User`, `Registration`, and `Payment` Endpoints

**What to build:** Lock private domain resources (`User`, `Registration`, and `Payment`) behind authentication and role-scoped visibility while keeping catalog browsing (`Event`, `Event Poster`, and `Ticket`) publicly readable. Allow `User`s to list and retrieve their own `Registration` and `Payment` records, allow `Organizer`s to list and retrieve `Registration` and `Payment` records for `Event`s they personally own (read-only), and return the union of both scopes when an actor holds both roles.

**Blocked by:** 01: Milestone Tag, Modular Environment Settings (`base`, `dev`, `prod`, `test`), and CORS Whitelisting

**Status:** ready-for-agent

- [ ] Unauthenticated `GET` requests to `Event` list/detail, `Event Poster` list, and `Ticket` list/detail remain publicly accessible (`200 OK`), while unauthenticated `GET` requests to `User`, `Registration`, and `Payment` list or detail endpoints are rejected with `401 Unauthorized`.
- [ ] An authenticated `User` can `GET` and `PUT`/`PATCH` their own `User` detail endpoint (`200 OK`), is rejected with `403 Forbidden` when attempting to `GET`, `PUT`, `PATCH`, or `DELETE` another `User` or list all `User`s, while `Admin` and `Superuser` actors can list and retrieve all `User` profiles.
- [ ] An authenticated `User` calling `GET /api/registrations/`, `GET /api/registrations/<id>/`, `GET /api/payments/`, or `GET /api/payments/<id>/` receives only their own `Registration` and `Payment` records and is denied access to other participants' records (`404 Not Found` or `403 Forbidden`).
- [ ] An `Organizer` calling `GET /api/registrations/`, `GET /api/registrations/<id>/`, `GET /api/payments/`, or `GET /api/payments/<id>/` receives read-only visibility into `Registration` and `Payment` records belonging to `Event`s they personally own, and receives the union of their owned-`Event` records and their personal participant records when they also register/pay as a `User` on another host's `Event`.
- [ ] An `Organizer` attempting to `PUT`, `PATCH`, or `DELETE` another participant's `Registration` or `Payment` on their `Event` is rejected with `403 Forbidden`, whereas `Admin` and `Superuser` actors retain full platform-wide visibility and management access.
- [ ] All scoped `Registration` and `Payment` list and detail endpoints maintain constant `O(1)` SQL query counts under `django_assert_num_queries` verification.
