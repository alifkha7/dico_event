# 01: Database Query Optimization, Indexing & django-silk Profiling

**What to build:** Eliminate N+1 SQL queries across User, Event, Ticket, Registration, and Payment endpoints using eager loading (`select_related` and `prefetch_related`), add database indexes on high-frequency Event filter and ordering fields (`start_time`, `status`, `category`), integrate the `django-silk` query profiler at `/silk/` when `ENABLE_SILK=True` while bypassing `SilkyMiddleware` during standard test runs per ADR-0002, and verify constant `O(1)` query counts via automated `django_assert_num_queries` tests.

**Blocked by:** None (can start immediately)

**Status:** claimed

- [ ] `Event` model defines database indexes on `start_time`, `status`, and `category` with a corresponding schema migration.
- [ ] `User`, `Event`, `Ticket`, `Registration`, and `Payment` querysets and foreign-key lookups use `select_related` and `prefetch_related` so that listing multiple records or checking object-level RBAC ownership (`Ticket -> Event`, `Payment -> Registration`, `Registration -> Ticket -> Event`) never triggers N+1 queries.
- [ ] Automated tests using `django_assert_num_queries` prove that listing 2 vs. 10 records for `Users`, `Events`, `Tickets`, `Registrations`, and `Payments` executes the exact same constant number of SQL queries (`O(1)`).
- [ ] `django-silk` is added to project dependencies and conditionally enabled (`silk` app, `SilkyMiddleware`, and `/silk/` URL routes) when `ENABLE_SILK=True`, while defaulting to bypassed during standard `pytest` runs per ADR-0002.
- [ ] Dedicated tests verify that `/silk/` responds when `ENABLE_SILK=True` and that all existing V1 and V2 tests continue to pass without regression.
