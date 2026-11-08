# 04: Relational Audit Protection (`PROTECT`) and `409 Conflict` Deletion Guards

**What to build:** Protect historical `Ticket`, `Registration`, `User`, and `Payment` records from destructive cascading deletions by enforcing `on_delete=PROTECT` across transactional foreign keys and surfacing `409 Conflict` with a structured JSON error detail whenever a caller attempts to delete a record referenced by downstream transactional history.

**Blocked by:** 03: Scoped RBAC Visibility for `User`, `Registration`, and `Payment` Endpoints

**Status:** ready-for-agent

- [ ] Database foreign keys on `Ticket.event`, `Registration.ticket`, `Registration.user`, and `Payment.registration` enforce `on_delete=PROTECT` via applied schema migrations.
- [ ] Deleting an `Event` with no `Ticket`s, a `Ticket` with no `Registration`s, a `Registration` with no `Payment`s, or a `User` with no `Registration`s or owned `Event`s succeeds with `204 No Content`.
- [ ] Attempting to `DELETE` an `Event` that has `Ticket`s, a `Ticket` that has `Registration`s, a `User` that has `Registration`s, or a `Registration` that has `Payment`s is intercepted by the centralized exception handler, logged via Loguru, and rejected with `409 Conflict` and a JSON `{"detail": "..."}` response while leaving all database rows intact.
- [ ] Automated HTTP API tests replace the legacy ADR-0001 cascading-delete assertions with verification of `409 Conflict` audit protection and `204 No Content` clean deletion when unreferenced.
