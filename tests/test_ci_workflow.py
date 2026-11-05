from pathlib import Path

import yaml
from django.conf import settings


def _load_ci_workflow():
    base_dir = Path(settings.BASE_DIR)
    workflow_path = base_dir / ".github" / "workflows" / "ci.yml"
    assert workflow_path.exists(), f"CI workflow file must exist at {workflow_path}"
    with open(workflow_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "CI workflow YAML must parse into a dictionary"
    return data


def test_ci_workflow_file_exists_and_parses():
    data = _load_ci_workflow()
    assert "jobs" in data, "CI workflow must define 'jobs'"


def test_ci_workflow_triggers():
    data = _load_ci_workflow()
    # In YAML 1.1, unquoted 'on:' parses as boolean True; in YAML 1.2 or quoted, as 'on'
    triggers = data.get(True) or data.get("on")
    assert triggers is not None, "Workflow must define triggers ('on' / True)"

    if isinstance(triggers, list):
        trigger_keys = triggers
    elif isinstance(triggers, dict):
        trigger_keys = list(triggers.keys())
    else:
        trigger_keys = [triggers]

    assert "push" in trigger_keys, "CI workflow must be triggered on 'push'"
    assert "pull_request" in trigger_keys, "CI workflow must be triggered on 'pull_request'"


def test_ci_workflow_services():
    data = _load_ci_workflow()
    jobs = data.get("jobs", {})
    assert len(jobs) > 0, "CI workflow must define at least one job"

    # Get the test / CI job
    job = jobs.get("test") or jobs.get("ci") or next(iter(jobs.values()))
    services = job.get("services", {})
    assert "postgres" in services, "CI job must define a 'postgres' service container"
    assert "redis" in services, "CI job must define a 'redis' service container"

    # Verify postgres service
    pg = services["postgres"]
    assert pg.get("image") == "postgres:15-alpine", "PostgreSQL service must use image 'postgres:15-alpine'"
    pg_ports = [str(p) for p in pg.get("ports", [])]
    assert any("5432" in p for p in pg_ports), "PostgreSQL service must expose/map port 5432"
    assert "options" in pg, "PostgreSQL service must define health-check options"
    assert "--health-cmd" in pg["options"], "PostgreSQL service options must include --health-cmd"

    # Verify redis service
    redis = services["redis"]
    assert redis.get("image") == "redis:7-alpine", "Redis service must use image 'redis:7-alpine'"
    redis_ports = [str(p) for p in redis.get("ports", [])]
    assert any("6379" in p for p in redis_ports), "Redis service must expose/map port 6379"
    assert "options" in redis, "Redis service must define health-check options"
    assert "--health-cmd" in redis["options"], "Redis service options must include --health-cmd"


def test_ci_workflow_environment_variables():
    data = _load_ci_workflow()
    jobs = data.get("jobs", {})
    job = jobs.get("test") or jobs.get("ci") or next(iter(jobs.values()))

    # Env can be at workflow level or job level
    env = {}
    if isinstance(data.get("env"), dict):
        env.update(data["env"])
    if isinstance(job.get("env"), dict):
        env.update(job["env"])

    required_vars = [
        "DATABASE_NAME",
        "DATABASE_USER",
        "DATABASE_PASSWORD",
        "DATABASE_HOST",
        "DATABASE_PORT",
        "REDIS_HOST",
        "REDIS_PORT",
        "CELERY_BROKER_URL",
        "USE_SQLITE_TEST",
    ]
    for var in required_vars:
        assert var in env, f"CI workflow environment must configure '{var}'"

    assert str(env["USE_SQLITE_TEST"]).lower() == "false", "USE_SQLITE_TEST must be set to 'False' in CI environment"


def test_ci_workflow_steps():
    data = _load_ci_workflow()
    jobs = data.get("jobs", {})
    job = jobs.get("test") or jobs.get("ci") or next(iter(jobs.values()))

    steps = job.get("steps", [])
    assert len(steps) > 0, "CI job must define execution steps"

    # 1. actions/checkout
    has_checkout = any("actions/checkout" in str(step.get("uses", "")) for step in steps)
    assert has_checkout, "CI workflow steps must include actions/checkout"

    # 2. actions/setup-python with Python 3.12
    setup_python_step = next((step for step in steps if "actions/setup-python" in str(step.get("uses", ""))), None)
    assert setup_python_step is not None, "CI workflow steps must include actions/setup-python"
    python_version = str(setup_python_step.get("with", {}).get("python-version", ""))
    assert "3.12" in python_version, f"Python version in setup-python must be 3.12, got: {python_version}"

    # Extract all run commands across steps
    run_commands = [str(step.get("run", "")) for step in steps if "run" in step]
    all_runs = "\n".join(run_commands)

    # 3. Dependency installation from requirements.txt
    assert "requirements.txt" in all_runs, "CI workflow must install dependencies from requirements.txt"

    # 4. ruff check .
    assert any("ruff check ." in cmd for cmd in run_commands), "CI workflow must run 'ruff check .'"

    # 5. ruff format --check .
    assert any("ruff format --check ." in cmd for cmd in run_commands), "CI workflow must run 'ruff format --check .'"

    # 6. python manage.py migrate
    assert any("python manage.py migrate" in cmd for cmd in run_commands), (
        "CI workflow must run 'python manage.py migrate'"
    )

    # 7. pytest
    assert any("pytest" in cmd for cmd in run_commands), "CI workflow must run 'pytest'"
