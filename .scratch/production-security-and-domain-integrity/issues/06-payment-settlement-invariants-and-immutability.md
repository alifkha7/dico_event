# 06: `Payment` Settlement Invariants, Admin-Only Refunds, and Settled Record Immutability

**What to build:** Enforce financial settlement invariants on `Payment` workflows: require `amount_paid` to match the associated `Ticket` price (supporting `0` for free tickets), restrict `payment_status` to the canonical states (`Pending`, `Completed`, `Failed`, `Refunded` with case-insensitive normalization), restrict `Refunded` status transitions to `Admin` and `Superuser` actors (`403 Forbidden` for non-admins), prevent duplicate `Completed` payments for a single `Registration` under row locking, and reject `DELETE` requests on `Completed` or `Refunded` payments with `409 Conflict`.

**Blocked by:** 04: Relational Audit Protection (`PROTECT`) and `409 Conflict` Deletion Guards

**Status:** ready-for-agent

- [ ] Creating or updating a `Payment` requires `amount_paid` to equal the associated `Ticket.price` (including `amount_paid == 0` when `Ticket.price == 0`), rejecting any mismatch with `400 Bad Request`.
- [ ] `payment_status` is validated and normalized case-insensitively against `Pending`, `Completed`, `Failed`, and `Refunded`, rejecting unknown status strings with `400 Bad Request`.
- [ ] Non-admin actors (`User` or `Organizer`) attempting to create or update a `Payment` with `payment_status` set to `Refunded` are rejected with `403 Forbidden`, while `Admin` and `Superuser` actors succeed.
- [ ] Creating or updating a `Payment` to `Completed` locks the parent `Registration` inside an atomic transaction and rejects the request with `400 Bad Request` if that `Registration` already has a `Completed` payment.
- [ ] Attempting to `DELETE` a `Payment` whose status is `Completed` or `Refunded` is rejected with `409 Conflict`, whereas deleting a `Payment` in `Pending` or `Failed` status succeeds with `204 No Content`.
- [ ] Automated HTTP API tests verify exact price matching (paid and free tickets), canonical status validation, admin-only `Refunded` transitions, duplicate `Completed` settlement prevention, and `409 Conflict` deletion immutability on settled payments.
