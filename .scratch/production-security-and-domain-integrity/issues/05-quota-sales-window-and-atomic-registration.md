# 05: Venue Quota Allocation, Active Sales Windows, and Atomic `Registration` Intake

**What to build:** Enforce venue and admission capacity invariants across `Event`, `Ticket`, and `Registration` workflows: prevent `Ticket` quota allocations from exceeding parent `Event` capacity (`SUM(Ticket.quota) <= Event.quota`), prevent duplicate registrations by the same `User` for the same `Ticket`, enforce active `Ticket` sales windows (`sales_start <= now <= sales_end`), and lock `Ticket` and `Event` rows atomically during `Registration` intake so concurrent requests cannot oversell capacity.

**Blocked by:** 04: Relational Audit Protection (`PROTECT`) and `409 Conflict` Deletion Guards

**Status:** resolved

- [x] Creating or updating a `Ticket` is rejected with `400 Bad Request` if the sum of all `Ticket` quotas for that `Event` would exceed `Event.quota`, and updating an `Event`'s `quota` is rejected with `400 Bad Request` if the new `Event.quota` is less than the sum of its existing `Ticket` quotas.
- [x] A database `UniqueConstraint` on `(ticket, user)` prevents a `User` from creating more than one `Registration` for the same `Ticket`, returning `400 Bad Request` on duplicate attempts.
- [x] Creating a `Registration` when the current timestamp is before `Ticket.sales_start` or after `Ticket.sales_end` is rejected with `400 Bad Request`.
- [x] Creating a `Registration` locks the target `Ticket` and parent `Event` rows inside an atomic transaction (`select_for_update()`) and rejects the request with `400 Bad Request` when existing registrations for that `Ticket` have reached `Ticket.quota` or total registrations across the `Event` have reached `Event.quota`.
- [x] Automated HTTP API tests verify `Ticket`/`Event` quota sum allocation, sales window boundaries, duplicate `(User, Ticket)` rejection, and quota exhaustion enforcement.
