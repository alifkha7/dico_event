# Production Security, Transactional Integrity, and Environment Separation

**Status:** ready-for-agent

## Problem Statement

DicoEvent currently retains four compatibility compromises originally introduced to pass the automated Dicoding Academy #788 Postman test suites (ADR-0001), alongside several unguarded domain invariants and single-file configuration defaults:

1. **Unauthenticated Exposure of Private Domain Records (IDOR Risk)**: Detail retrieval endpoints for `User`, `Registration`, and `Payment` records currently allow unauthenticated public read access (`AllowAny`), exposing participant identities, registrations, and payment settlements to anyone with a UUID. Conversely, collection listing endpoints for `Registration` and `Payment` restrict access exclusively to `Admin` and `Superuser` actors, preventing `User` participants from viewing their own history and preventing `Organizer` hosts from viewing participant registrations and settlements for their own `Event`s.
2. **Destructive Cascading Deletions on Financial & Registration History**: Deleting a `Ticket`, `Event`, or `User` cascades and physically deletes associated `Registration` and `Payment` records, and settled `Payment` records can be deleted directly, destroying financial audit trails.
3. **Unenforced Ticket Capacity, Sales Windows, and Settlement Invariants**: Creating a `Ticket` does not verify that the sum of ticket quotas stays within the parent `Event` quota. Creating a `Registration` does not verify whether the `Ticket` sales window is currently active, whether the `User` has already registered for the same `Ticket`, or whether concurrent registrations exceed the `Ticket` or `Event` quota. Creating or updating a `Payment` does not verify that `amount_paid` matches the `Ticket` price, allows arbitrary status strings, allows non-admin users to set `Refunded` status, and permits multiple `Completed` payments for a single `Registration`.
4. **Opaque Object Storage References & Missing CORS Controls**: `Event Poster` responses expose only the raw object storage key (`image`) without a directly renderable time-limited URL (`image_url`) that works across both host browsers and containerized networks, and the API lacks explicit Cross-Origin Resource Sharing (`CORS`) origin controls.
5. **Monolithic Settings Without Production Fail-Fast Guards**: All environment settings reside in a single configuration module that relies on runtime command-line inspection (`sys.argv`) to switch between test and production backends and falls back to an insecure default `SECRET_KEY` and wildcard `ALLOWED_HOSTS` even in production.

## Solution

Transition DicoEvent from autograder compatibility mode to a production-grade architecture (as recorded in ADR-0004) while preserving the submission milestone via Git tag `v2.0-dicoding-submission`:

1. **Scoped RBAC Read & Write Access Control**: Keep catalog browsing (`Event`, `Event Poster`, `Ticket`) publicly readable while locking `User`, `Registration`, and `Payment` endpoints behind authentication and role-scoped visibility. Allow `User`s to list and retrieve their own `Registration` and `Payment` records, allow `Organizer`s to list and retrieve `Registration` and `Payment` records for `Event`s they personally own (read-only), and combine scopes via union when an actor holds both roles.
2. **Relational Audit Protection (`PROTECT`) & Immutable Settlements**: Replace cascading deletions across `Ticket`, `Registration`, and `Payment` relationships with protective deletion guards that return `409 Conflict` when dependent transactional history exists. Lock `Payment` records in `Completed` or `Refunded` states against deletion (`409 Conflict`).
3. **Strict Quota Allocation, Sales Windows, & Atomic Intake**: Enforce a single `Registration` per `(User, Ticket)` pair, enforce `SUM(Ticket.quota) <= Event.quota` across each `Event`, validate active `Ticket` sales windows, and lock `Ticket` and `Event` rows atomically during `Registration` intake to prevent overselling. Enforce exact `Ticket` price settlement (`amount_paid == Ticket.price`, supporting `0` for free tickets), canonical `Payment` statuses (`Pending`, `Completed`, `Failed`, `Refunded`), admin-only `Refunded` transitions, and at most one `Completed` settlement per `Registration`.
4. **Presigned `Event Poster` URLs & Explicit CORS Whitelisting**: Add a locally signed, time-limited `image_url` field alongside `image` on `Event Poster` representations—supporting a dedicated public signing endpoint so URLs resolve in host browsers even when uploads route through internal container hostnames—and enforce explicit `CORS` origin whitelisting.
5. **Modular Environment Settings (`base`, `dev`, `prod`, `test`)**: Split configuration into dedicated environment modules where `prod` fails fast on missing or insecure secrets/hosts and enforces HTTPS/cookie/HSTS security headers, and `test` defaults to fast in-memory backends locally while honoring PostgreSQL and Redis service containers in continuous integration.

## User Stories

1. As a maintainer, I want the Dicoding submission state preserved under Git tag `v2.0-dicoding-submission`, so that the exact autograder-compatible snapshot remains reproducible in version history.
2. As an unauthenticated visitor, I want to browse `Event` lists and details, `Event Poster` lists, and `Ticket` lists and details without logging in, so that I can discover upcoming events and admission categories before registering.
3. As an unauthenticated visitor, I want requests to retrieve or list `User`, `Registration`, or `Payment` resources to be rejected with `401 Unauthorized`, so that private participant and financial data cannot be enumerated or inspected anonymously.
4. As an authenticated `User`, I want to retrieve and update only my own `User` profile while being denied access to other `User` profiles (`403 Forbidden`), so that personal account details remain private to each participant.
5. As an `Admin` or `Superuser`, I want to list and retrieve any `User` profile, so that I can administer participant accounts across the platform.
6. As an authenticated `User`, I want `GET /api/registrations/` and `GET /api/registrations/<id>/` to return my own `Registration` records while denying access to other participants' registrations (`404 Not Found` or `403 Forbidden`), so that I can track the events I have registered for.
7. As an `Organizer`, I want `GET /api/registrations/` and `GET /api/registrations/<id>/` to allow read-only access to `Registration` records belonging to `Event`s I personally own, so that I can monitor attendee registrations for my events.
8. As an `Organizer` who also registers as a `User` for another host's `Event`, I want `GET /api/registrations/` to return the union of registrations for `Event`s I own and my personal registrations as a participant, so that my organizer and attendee activities do not shadow each other.
9. As an `Organizer`, I want attempts to modify or delete a participant's `Registration` for my `Event` (unless it is my own personal registration) to be rejected with `403 Forbidden`, so that hosts cannot tamper with attendee records.
10. As an authenticated `User`, I want `GET /api/payments/` and `GET /api/payments/<id>/` to return my own `Payment` settlements while denying access to other participants' payments, so that I can review my payment history securely.
11. As an `Organizer`, I want read-only access to `Payment` records linked to `Event`s I personally own via `GET /api/payments/` and `GET /api/payments/<id>/`, so that I can verify settlement status for my event attendees.
12. As an `Organizer` who also submits `Payment`s as a `User` for other events, I want `GET /api/payments/` to return the union of payments for my own `Event`s and my personal payments, so that I have complete visibility across both roles.
13. As an `Admin` or `Superuser`, I want unrestricted read access to all `Registration` and `Payment` records across the platform, so that I can oversee platform operations.
14. As an `Organizer` or `Admin`, I want deleting an `Event` that has no associated `Ticket`s (or deleting a `Ticket` that has no associated `Registration`s) to succeed with `204 No Content`, so that unused catalog entries can be cleaned up.
15. As an `Organizer`, `Admin`, or `Superuser`, I want any attempt to delete an `Event`, `Ticket`, `User`, or `Registration` that is referenced by existing downstream `Ticket`, `Registration`, or `Payment` records to be rejected with `409 Conflict` and a clear JSON error detail, so that historical registration and financial records are never orphaned or silently wiped out.
16. As an `Organizer` or `Admin`, I want creating or updating a `Ticket` (or decreasing an `Event`'s quota) to be rejected with `400 Bad Request` if the sum of all `Ticket` quotas for that `Event` exceeds the parent `Event` quota, so that ticket allocations never exceed venue capacity.
17. As an authenticated `User`, I want creating a `Registration` for a `Ticket` outside its active sales window (`now < sales_start` or `now > sales_end`) to be rejected with `400 Bad Request`, so that tickets cannot be claimed before sales open or after sales close.
18. As an authenticated `User`, I want creating a second `Registration` for the same `Ticket` I have already registered for to be rejected with `400 Bad Request`, so that a single account cannot hoard multiple spots in the same ticket tier or trigger duplicate reminder emails.
19. As an authenticated `User`, I want creating a `Registration` when either the `Ticket` quota or the parent `Event` quota is already full to be rejected with `400 Bad Request` under row-level transactional locking, so that concurrent requests never oversell an event or ticket tier.
20. As an authenticated `User`, I want creating or updating a `Payment` to require `amount_paid` to equal the associated `Ticket` price (including `amount_paid == 0` when the `Ticket` price is `0`), so that underpayments and overpayments are prevented at intake.
21. As an authenticated `User`, I want `Payment` status values to be validated against the canonical set (`Pending`, `Completed`, `Failed`, `Refunded`, normalized case-insensitively) and to be allowed to submit `Pending`, `Completed`, or `Failed` statuses during checkout simulation, so that payment states remain consistent.
22. As a non-admin `User` or `Organizer`, I want attempts to set a `Payment` status to `Refunded` to be rejected with `403 Forbidden`, while allowing `Admin` and `Superuser` actors to set `Refunded`, so that financial refunds require administrative authorization.
23. As an authenticated `User`, `Admin`, or `Superuser`, I want creating or updating a `Payment` to `Completed` to be rejected with `400 Bad Request` if that `Registration` already has a `Completed` payment, so that participants are never double-charged for the same registration.
24. As an authenticated `User`, `Admin`, or `Superuser`, I want deleting a `Payment` that is in `Pending` or `Failed` status to succeed with `204 No Content`, while deleting a `Payment` in `Completed` or `Refunded` status is rejected with `409 Conflict`, so that settled financial records remain immutable.
25. As a frontend client or API consumer, I want `Event Poster` upload and listing responses to include both `image` (the storage object key) and `image_url` (a time-limited presigned GET URL signed against the configured public MinIO endpoint, or `null` if signing fails), so that browsers can directly render poster images without constructing storage URLs manually.
26. As a browser-based frontend application hosted on an allowed origin, I want the API to return appropriate `Access-Control-Allow-Origin` headers based on the configured `CORS_ALLOWED_ORIGINS` whitelist, so that cross-origin browser requests succeed securely without wildcard exposure in production.
27. As a DevOps engineer, I want Django configuration split into dedicated `base`, `dev`, `prod`, and `test` modules, so that each runtime environment has explicit, isolated configuration without inspecting command-line arguments in shared settings.
28. As a DevOps engineer, I want loading the `prod` settings module with a missing or default insecure `SECRET_KEY`, `DEBUG=True`, or wildcard/empty `ALLOWED_HOSTS` to fail immediately with `ImproperlyConfigured` and to enforce HTTPS redirect, secure cookies, and HSTS headers by default, so that misconfigured production deployments cannot start silently.
29. As a developer running tests locally or in GitHub Actions CI, I want the `test` settings module to default to fast in-memory SQLite, local-memory cache, and eager Celery execution locally while honoring `USE_SQLITE_TEST=False` to run against real PostgreSQL and Redis service containers in CI, so that both fast local TDD and production-parity CI checks remain green.

## Implementation Decisions

- **Git Milestone Tagging**:
  - Tag the pre-transition commit as `v2.0-dicoding-submission` before applying ADR-0004 changes.
- **Modular Settings Architecture**:
  - Replace the single configuration module with a settings package divided into `base`, `dev`, `prod`, and `test` modules, plus a package initializer that routes dynamically via an environment variable (`DJANGO_ENV`, defaulting to `dev`) when the root settings package is imported directly (such as during container image `collectstatic` builds).
  - Resolve `BASE_DIR` consistently to the repository root across all settings modules so static asset paths, log files, and containerization checks remain unchanged.
  - In `base`: define shared installed apps (adding `corsheaders`), middleware (placing `CorsMiddleware` immediately after `WhiteNoiseMiddleware` and before `SessionMiddleware`/`CommonMiddleware` so static middleware ordering invariants remain intact), SimpleJWT, Spectacular OpenAPI, MinIO settings (including `MINIO_PUBLIC_ENDPOINT_URL` and `MINIO_PRESIGNED_EXPIRY_SECONDS` defaulting to `3600`), SMTP, and Loguru initialization.
  - In `dev`: enable `DEBUG=True`, permissive local `ALLOWED_HOSTS`, `ENABLE_SILK` (defaulting to `True`), and local `CORS_ALLOWED_ORIGINS` defaults.
  - In `prod`: force `DEBUG=False`; raise `ImproperlyConfigured` if `SECRET_KEY` is missing or equals the insecure default placeholder, or if `ALLOWED_HOSTS` is missing, empty, or contains `"*"`. Configure `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, and `SECURE_HSTS_PRELOAD` (enabled by default in `prod`, overridable via explicit environment flags for local container smoke tests). Require explicit `CORS_ALLOWED_ORIGINS` without wildcard origins.
  - In `test`: disable `ENABLE_SILK` by default, use fast MD5 password hashing, and enable `CELERY_TASK_ALWAYS_EAGER`. Default `USE_SQLITE_TEST` to `True` (in-memory SQLite + `LocMemCache`), while switching to PostgreSQL and `django-redis` whenever `USE_SQLITE_TEST` is explicitly set to `False` (as in the GitHub Actions CI workflow). Update the test runner configuration to point to the `test` settings module.
- **Scoped RBAC Permissions & Queryset Visibility**:
  - Remove the blanket unauthenticated `retrieve` bypass from the base role-ownership permission class; only endpoints that explicitly declare `"retrieve"` in `public_actions` (`Event` and `Ticket`, plus `Event Poster` views) allow unauthenticated detail access.
  - `User` access: keep `create` public (`AllowAny`) for registration and `list`/`destroy` restricted to `Admin` and `Superuser`; restrict `retrieve`, `update`, and `partial_update` to the account owner (`id == request.user.id`), `Admin`, or `Superuser`.
  - `Registration` and `Payment` access: remove `"list"` from `admin_only_actions` and remove `"retrieve"` from `public_actions`. Require authentication for all actions.
  - Scope `Registration` and `Payment` querysets dynamically based on the authenticated actor:
    - `Admin` and `Superuser` receive the full unfiltered queryset (with existing `select_related` eager loading preserved).
    - Non-admin authenticated actors receive the union (`Q(...) | Q(...)`, `.distinct()`) of records they own as a `User` (`user=request.user` / `registration__user=request.user`) and records belonging to `Event`s they own as an `Organizer` (`ticket__event__organizer=request.user` / `registration__ticket__event__organizer=request.user`).
    - On object-level checks (`retrieve`, `update`, `partial_update`, `destroy`), allow `retrieve` if the actor is either the owning `User` or the owning `Event`'s `Organizer` (or `Admin`/`Superuser`), while restricting write/mutation actions (`update`, `partial_update`, `destroy`) strictly to the owning `User` (and `Admin`/`Superuser`), preventing `Organizer`s from mutating or deleting attendees' registrations or payments.
- **Relational Audit Protection (`PROTECT`) & `409 Conflict` Handling**:
  - Change foreign key `on_delete` behavior from `CASCADE` to `PROTECT` on `Ticket.event`, `Registration.ticket`, `Registration.user`, and `Payment.registration`, and generate the corresponding schema migrations. (`EventPoster.event` and `Event.organizer` may also use `PROTECT` or keep `EventPoster` tied to `Event` lifecycle so poster cleanup does not block unused event deletion).
  - Extend the centralized DRF exception handler to catch Django's `ProtectedError` (and `IntegrityError` where applicable) and return an HTTP `409 Conflict` response with a clear `{"detail": "..."}` message logged via Loguru.
- **Quota Invariants, Sales Windows, & Atomic Registration Intake**:
  - Add a database-level `UniqueConstraint` on `Registration(ticket, user)` so each `User` can register at most once per `Ticket`, surfaced as a `400 Bad Request` validation error on duplicate attempts.
  - During `Ticket` creation and update, validate that the proposed `Ticket.quota` plus the sum of existing `Ticket` quotas for the same `Event` does not exceed `Event.quota`. Similarly, when updating an `Event`'s `quota`, validate that the new `Event.quota` is not less than the sum of its existing `Ticket` quotas (or existing registrations).
  - During `Registration` creation (and if `ticket` is ever changed on update), execute intake inside `transaction.atomic()`, locking the target `Ticket` and parent `Event` rows via `select_for_update()`:
    - Verify the current timestamp falls within `Ticket.sales_start <= now <= Ticket.sales_end`; otherwise raise `400 Bad Request`.
    - Verify the current count of `Registration`s for the `Ticket` is strictly less than `Ticket.quota`, and total `Registration`s across the `Event` is strictly less than `Event.quota`; otherwise raise `400 Bad Request`.
- **Payment Settlement Invariants & Immutability**:
  - Normalize case-insensitive `payment_status` inputs against the four canonical values: `Pending`, `Completed`, `Failed`, and `Refunded`. Reject any other status string with `400 Bad Request`.
  - If a non-admin actor attempts to set `payment_status` to `Refunded` on create or update, reject with `403 Forbidden` (or permission error surfaced as `403 Forbidden`).
  - Validate that `amount_paid` equals the associated `Ticket.price` (allowing `amount_paid == 0` when `Ticket.price == 0`, and rejecting any mismatch with `400 Bad Request`).
  - Inside `transaction.atomic()`, lock the target `Registration` row and reject creating or updating a `Payment` to `Completed` with `400 Bad Request` if another `Completed` `Payment` already exists for that `Registration`.
  - In `Payment` deletion (`destroy`), check whether the target `Payment` has `payment_status` in `("Completed", "Refunded")`; if so, reject deletion with `409 Conflict` (`{"detail": "Completed or refunded payments cannot be deleted."}`).
- **Presigned `Event Poster` URLs & Public Endpoint Signing**:
  - Introduce a helper in the event storage module that generates a time-limited presigned GET URL (`MINIO_PRESIGNED_EXPIRY_SECONDS`, default 1 hour) for a stored poster object key using a MinIO client configured with `MINIO_PUBLIC_ENDPOINT_URL` (falling back to `MINIO_ENDPOINT_URL`) and an explicit default region (`"us-east-1"`) so presigning performs local cryptographic signing without requiring a network round-trip to look up bucket region. Wrap presigning in a `try/except` block that logs warnings and returns `None` on failure.
  - Expose `image_url` alongside `image` and `event` in `EventPosterSerializer`.

## Testing Decisions

- **Principles of Good Tests**:
  - Tests must assert observable external behavior (HTTP status codes, JSON response bodies, headers, and database state observable through public interfaces) rather than internal helper implementation details.
- **Agreed Testing Seams**:
  1. **Primary Seam — Public HTTP REST API (`APIClient` across `/api/*`)**:
     - Used to verify all RBAC read/write rules, union queryset scoping for multi-role actors, `409 Conflict` responses on `ProtectedError` and settled `Payment` deletion, `SUM(Ticket.quota) <= Event.quota` validation, `Ticket` sales window enforcement, duplicate `(User, Ticket)` registration rejection, atomic `Ticket`/`Event` quota exhaustion, `Payment` exact price matching (including free tickets), canonical statuses, `Admin`-only `Refunded` transitions, duplicate `Completed` payment prevention, `Event Poster` `image_url` presigned output, and `CORS` headers.
     - Query-count assertions (`django_assert_num_queries`) continue to verify constant `O(1)` query scaling on list and detail endpoints under the new scoped querysets.
  2. **Secondary Seam — Settings Module Loader (`dicoevent.settings.{base,dev,prod,test}`)**:
     - Used to verify that importing/reloading `prod` settings raises `ImproperlyConfigured` when `SECRET_KEY` or `ALLOWED_HOSTS` are missing or insecure, that HTTPS/cookie/HSTS flags are enabled by default in `prod`, and that `test` settings switch cleanly between SQLite in-memory and PostgreSQL/Redis based on `USE_SQLITE_TEST`.
- **Prior Art in the Codebase**:
  - Existing endpoint and domain tests in `tests/` (such as `test_auth.py`, `test_users.py`, `test_events.py`, `test_event_posters.py`, `test_tickets.py`, `test_cascading_deletes.py`, `test_query_optimization.py`, `test_docker_containerization.py`, and `test_ci_workflow.py`) using `pytest-django` fixtures (`api_client`, `superuser`, `admin_user`, `organizer_user`, `regular_user`, `get_auth_header`).
  - Existing tests that explicitly assert ADR-0001 behaviors (unauthenticated detail `GET` on `User`/`Registration`/`Payment` and cascading deletion in `test_cascading_deletes.py`) will be updated to assert the new ADR-0004 contracts (`401`/`403` on unauthorized detail access and `409 Conflict` on protected deletion).

## Out of Scope

- Replacing `DualKeyModelSerializer` (`<field>` and `<field>_id` dual output) or changing `PartialUpdateMixin` (`PUT` partial update behavior), which remain intact for existing client ergonomics.
- Adding HATEOAS `_links` arrays to resource serializers.
- Integrating third-party external payment gateway webhooks (Midtrans, Xendit, Stripe) or external Sentry error monitoring (`sentry-sdk`).
- Implementing soft-delete (`deleted_at` / `is_active`) columns across domain models.

## Further Notes

- Preserving `WhiteNoiseMiddleware` immediately after `SecurityMiddleware` (with `CorsMiddleware` placed at index 2, right after `WhiteNoiseMiddleware`) ensures full compatibility with existing containerization verification tests while still intercepting preflight `OPTIONS` and cross-origin requests before `CommonMiddleware`.
