# 05: Payments Domain Application (`payments`) & Legacy Monolith Removal

**What to build:** Complete the Multi-App Django architecture by extracting **Payment** settlement into a dedicated `payments` Django application (`db_table = "payments"`, cascading delete from **Registration**, and ADR-0001 case-insensitive `"completed"` -> `"Completed"` normalization), migrating all remaining cross-domain test suites (`payments`, cascading deletes, query optimization, and OpenAPI schema validation) to the new domain applications, and permanently deleting the legacy monolithic `api` directory and its old migrations.

**Blocked by:** 04: Deepened Registrations & Reminder Lifecycle Application (`registrations`)

**Status:** ready-for-agent

- [ ] The `payments` application is registered in Django's installed applications under the `payments` label and owns the **Payment** model (`db_table = "payments"`, cascading delete from **Registration**) and its initial migration.
- [ ] `PaymentSerializer` inherits from `DualKeyModelSerializer` to resolve `registration` / `registration_id` (with `select_related("user")`), enforces positive `amount_paid`, and normalizes case-insensitive `"completed"` to `"Completed"` (ADR-0001).
- [ ] `PaymentViewSet` configures `select_related("registration", "registration__user")`, uses `PartialUpdateMixin` and the declarative permission policy (**Admin**/**Superuser** full access, **User** ownership via `registration.user_id`, and ADR-0001 unauthenticated detail `retrieve`), and mounts `/api/payments` routes via the `core` URL aggregator.
- [ ] The legacy monolithic `api` directory (including all legacy files and migrations) is completely removed from the repository, and zero imports from `api` remain anywhere in the codebase or test suite.
- [ ] All cross-domain test suites (**Payment**, cascading deletes, `O(1)` query optimization, OpenAPI schema validation, Docker, CI, and `ruff` linting/formatting) are updated to reference the canonical `apps.*` modules and pass 100%.
