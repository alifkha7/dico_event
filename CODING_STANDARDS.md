# Coding Standards

Reviewed by the **Standards** axis during `/code-review`. Mechanical formatting and import rules live in [`pyproject.toml`](pyproject.toml) (`ruff`); domain vocabulary lives in [`GLOSSARY.md`](GLOSSARY.md); architectural trade-offs live in [`docs/adr/`](docs/adr/).

## 1. Domain Invariants in Schema & Docstrings

OpenAPI annotations (`@extend_schema`), serializer help text, and docstrings must state the exact domain terms and numerical invariants defined in [`GLOSSARY.md`](GLOSSARY.md) and [`docs/adr/`](docs/adr/) (such as `500 KB` for **Event Poster** size limits, `3 hours` for JWT access token lifetime, and `2 hours` for pre-event reminder scheduling).

## 2. Model-Agnostic Shared Helpers

Shared serializer, view, and query utilities (such as `_resolve_foreign_key`) must stay model-agnostic. Pass eager-loading hints (`select_related`, `prefetch_related`) or base querysets as parameters from the caller rather than branching on specific model classes (`if model_class is ...`) inside the helper.

## 3. Behavioral Query Assertions over ORM Internals

Database optimization tests must verify observable SQL execution behavior—such as constant `O(1)` query counts via `django_assert_num_queries`—rather than asserting against private Django `queryset.query` compiler dictionary structures.
