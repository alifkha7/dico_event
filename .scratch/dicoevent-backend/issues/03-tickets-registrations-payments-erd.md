# 03: Tickets, Registrations, Payments & V1 ERD

**What to build:** Complete the DicoEvent Versi 1 domain lifecycle by enabling Ticket creation and management for Events, User Registrations for Tickets, and Payment creation and status updates for Registrations—including cascading deletes from Ticket to Registration and Payment, optional trailing slashes on detail routes, and the Entity Relationship Diagram (`ERD-DicoEvent-versi-1`).

**Blocked by:** 02: Events CRUD, Organizer Ownership RBAC & Paginated Queries

**Status:** resolved

- [x] `Ticket` entity uses a UUID primary key (`id`), references `Event` (`on_delete=CASCADE`), and stores `name`, `price` (number), `sales_start`, `sales_end`, and `quota` (number).
- [x] `POST /api/tickets/` creates a Ticket (`201 Created`), `GET /api/tickets/` returns `{"tickets": [...]}` (`200 OK`), `GET /api/tickets/<id>[/]` returns Ticket details with `event` as a UUID string (`200 OK`), `PUT /api/tickets/<id>/` updates the Ticket (`200 OK`), and `DELETE /api/tickets/<id>/` deletes the Ticket (`204 No Content`, subsequent `GET` -> `404 Not Found`).
- [x] `Registration` entity uses a UUID primary key (`id`) and references `Ticket` (`on_delete=CASCADE`) and `User` (`on_delete=CASCADE`).
- [x] `POST /api/registrations/` with `{"ticket_id", "user_id"}` creates a Registration and returns `201 Created` with `id`, `ticket` (UUID string), and `user` (UUID string).
- [x] `GET /api/registrations/` returns `{"registrations": [...]}` for `Admin` and `Superuser` (`200 OK`), `GET /api/registrations/<id>[/]` returns Registration details (`200 OK`), `PUT /api/registrations/<id>/` updates the Registration (`200 OK`), and `DELETE /api/registrations/<id>/` deletes it (`204 No Content`, subsequent `GET` -> `404 Not Found`).
- [x] `Payment` entity uses a UUID primary key (`id`), references `Registration` (`on_delete=CASCADE`), and stores `payment_method`, `payment_status`, and `amount_paid` (number).
- [x] `POST /api/payments/` with `{"registration_id", "payment_method", "payment_status", "amount_paid"}` creates a Payment and returns `201 Created` with `id`, `registration` (UUID string), `payment_method`, `payment_status`, and `amount_paid`.
- [x] `GET /api/payments/` returns `{"payments": [...]}` for `Admin` and `Superuser` (`200 OK`), `GET /api/payments/<id>[/]` returns Payment details (`200 OK`), `PUT /api/payments/<id>/` updates the Payment (`200 OK`, normalizing `"completed"` to `"Completed"` per ADR-0001), and `DELETE /api/payments/<id>/` deletes the Payment (`204 No Content`).
- [x] Deleting a Ticket (`DELETE /api/tickets/<id>/`) cascades and deletes its associated Registrations and Payments so that subsequent `GET /api/payments/<paymentId>[/]` returns `404 Not Found` (per ADR-0001).
- [x] An Entity Relationship Diagram image depicting the normalized DicoEvent schema is generated and saved at the repository root as `ERD-DicoEvent-versi-1.png` (and `ERD-DicoEvent-versi-1.jpg`).
- [x] Automated HTTP API tests verify all `[Mandatory] Tickets`, `[Mandatory] Registrations`, and `[Mandatory] Payments` Postman scenarios.
