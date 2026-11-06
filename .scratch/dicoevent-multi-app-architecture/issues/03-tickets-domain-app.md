# 03: Tickets Domain Application (`tickets`)

**What to build:** Extract **Ticket** management into a dedicated `tickets` Django application (`db_table = "tickets"`) with cascading deletion from **Event**, declarative dual-key serialization (`event` / `event_id`) via `DualKeyModelSerializer`, declarative **Organizer** ownership and ADR-0001 unauthenticated detail `retrieve` via `RoleOwnershipPermission`, and constant `O(1)` query eager-loading (`select_related("event", "event__organizer")`).

**Blocked by:** 02: Deepened Events & Event Posters Domain Application (`events`)

**Status:** ready-for-agent

- [ ] The `tickets` application is registered in Django's installed applications under the `tickets` label and owns the **Ticket** model (`db_table = "tickets"`, cascading delete from **Event**) and its initial migration.
- [ ] `TicketSerializer` inherits from `DualKeyModelSerializer` to resolve `event` / `event_id` with caller-supplied eager-loading hints and enforces non-negative `price`, positive `quota`, and `sales_start < sales_end`.
- [ ] `TicketViewSet` configures `select_related("event", "event__organizer")`, uses `PartialUpdateMixin` and the declarative permission policy (**Admin**/**Superuser** full access, **Organizer** ownership via `event.organizer_id` on create/update/destroy, and ADR-0001 unauthenticated detail `retrieve`), and mounts `/api/tickets` routes via the `core` URL aggregator.
- [ ] The **Ticket** test suite is updated to import from the `tickets` application, and the entire test suite and `ruff` checks pass.
