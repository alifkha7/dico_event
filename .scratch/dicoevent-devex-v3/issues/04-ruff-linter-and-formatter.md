# 04: Unified Linting & Formatting with Ruff (pyproject.toml)

**What to build:** Add `Ruff` to project development dependencies, configure linting (`E`, `F`, `I`, `W` rules) and formatting (`line-length = 120`, excluding database migrations) in `pyproject.toml`, format and clean all Python modules across the repository so `ruff check .` and `ruff format --check .` pass with zero errors, and enforce this gate in an automated test.

**Blocked by:** 03: Full-Stack Docker Containerization (Dockerfile, Gunicorn, WhiteNoise & Compose)

**Status:** claimed

- [ ] `ruff` is added to project dependencies and configured in `pyproject.toml` with `target-version = "py312"`, `line-length = 120`, rule selectors `["E", "F", "I", "W"]`, and exclusions for auto-generated migrations and scratch/cache directories.
- [ ] All Python source and test files across the repository are formatted and cleaned so `ruff check .` and `ruff format --check .` exit with code `0`.
- [ ] An automated test executes `ruff check .` and `ruff format --check .` and asserts zero warnings/errors while all existing tests pass.
