from pathlib import Path

import yaml
from django.conf import settings


def test_dependencies_contain_gunicorn_whitenoise_and_pyyaml():
    base_dir = Path(settings.BASE_DIR)
    pipfile_path = base_dir / "Pipfile"
    requirements_path = base_dir / "requirements.txt"

    assert pipfile_path.exists(), "Pipfile must exist"
    assert requirements_path.exists(), "requirements.txt must exist"

    pipfile_content = pipfile_path.read_text(encoding="utf-8").lower()
    requirements_content = requirements_path.read_text(encoding="utf-8").lower()

    for dep in ["gunicorn", "whitenoise"]:
        assert dep in pipfile_content, f"'{dep}' must be in Pipfile"
        assert dep in requirements_content, f"'{dep}' must be in requirements.txt"

    assert "pyyaml" in pipfile_content, "'pyyaml' must be listed in Pipfile"
    assert "pyyaml" in requirements_content, "'pyyaml' must be listed in requirements.txt"


def test_whitenoise_and_static_root_configured():
    assert hasattr(settings, "STATIC_ROOT") and settings.STATIC_ROOT is not None, (
        "settings.STATIC_ROOT must be configured"
    )
    expected_static_root = Path(settings.BASE_DIR) / "staticfiles"
    assert Path(settings.STATIC_ROOT).resolve() == expected_static_root.resolve(), (
        f"STATIC_ROOT should resolve to {expected_static_root}"
    )

    middleware = list(settings.MIDDLEWARE)
    security_middleware = "django.middleware.security.SecurityMiddleware"
    whitenoise_middleware = "whitenoise.middleware.WhiteNoiseMiddleware"

    assert security_middleware in middleware, f"{security_middleware} must be in MIDDLEWARE"
    assert whitenoise_middleware in middleware, f"{whitenoise_middleware} must be in MIDDLEWARE"

    security_index = middleware.index(security_middleware)
    whitenoise_index = middleware.index(whitenoise_middleware)
    assert whitenoise_index == security_index + 1, (
        "WhiteNoiseMiddleware must be placed immediately after SecurityMiddleware"
    )


def test_dockerfile_configuration():
    base_dir = Path(settings.BASE_DIR)
    dockerfile_path = base_dir / "Dockerfile"
    assert dockerfile_path.exists(), "Dockerfile must exist at repository root"

    content = dockerfile_path.read_text(encoding="utf-8")
    assert "FROM python:3.12-slim" in content, "Dockerfile must use python:3.12-slim base image"
    assert "requirements.txt" in content, "Dockerfile must install requirements.txt"
    assert "collectstatic --noinput" in content, "Dockerfile must run collectstatic --noinput"
    assert "migrate" in content, "Dockerfile entrypoint / CMD must run migrations"
    assert "gunicorn dicoevent.wsgi:application" in content, "Dockerfile must run gunicorn dicoevent.wsgi:application"


def test_dockerignore_configuration():
    base_dir = Path(settings.BASE_DIR)
    dockerignore_path = base_dir / ".dockerignore"
    assert dockerignore_path.exists(), ".dockerignore must exist at repository root"

    content = dockerignore_path.read_text(encoding="utf-8")
    patterns = [".git", ".pytest_cache", ".scratch", "__pycache__", "*.log", ".env"]
    for pattern in patterns:
        assert pattern in content, f"Pattern '{pattern}' must be excluded in .dockerignore"


def test_docker_compose_services_and_dependencies():
    base_dir = Path(settings.BASE_DIR)
    compose_path = base_dir / "docker-compose.yml"
    assert compose_path.exists(), "docker-compose.yml must exist at repository root"

    with open(compose_path, "r", encoding="utf-8") as f:
        compose_data = yaml.safe_load(f)

    services = compose_data.get("services", {})
    expected_services = ["postgres", "redis", "minio", "mailpit", "web", "celery"]
    for s in expected_services:
        assert s in services, f"Service '{s}' must be defined in docker-compose.yml"

    # Healthchecks on postgres and redis
    assert "healthcheck" in services["postgres"], "postgres service must define a healthcheck"
    assert "healthcheck" in services["redis"], "redis service must define a healthcheck"

    # Helper to parse env vars whether list or dict
    def get_env_dict(service_cfg):
        env = service_cfg.get("environment", {})
        if isinstance(env, dict):
            return env
        elif isinstance(env, list):
            res = {}
            for item in env:
                if "=" in item:
                    k, v = item.split("=", 1)
                    res[k.strip()] = v.strip()
                else:
                    res[item.strip()] = ""
            return res
        return {}

    # Helper to parse depends_on whether list or dict
    def get_depends_on_list(service_cfg):
        deps = service_cfg.get("depends_on", [])
        if isinstance(deps, dict):
            return list(deps.keys())
        elif isinstance(deps, list):
            return deps
        return []

    # Verify 'web' service
    web = services["web"]
    build_context = web.get("build")
    assert build_context == "." or (isinstance(build_context, dict) and build_context.get("context") == "."), (
        "web service build context must be '.'"
    )
    ports = [str(p) for p in web.get("ports", [])]
    assert any("8000:8000" in p for p in ports), "web service must map port 8000:8000"

    web_env = get_env_dict(web)
    for env_var in [
        "DATABASE_HOST",
        "REDIS_HOST",
        "CELERY_BROKER_URL",
        "MINIO_ENDPOINT_URL",
        "MAIL_HOST",
        "ENABLE_SILK",
    ]:
        assert env_var in web_env, f"web service must define environment variable '{env_var}'"

    web_deps = get_depends_on_list(web)
    for dep in ["postgres", "redis", "minio", "mailpit"]:
        assert dep in web_deps, f"web service must depend on '{dep}'"

    # Verify 'celery' service
    celery = services["celery"]
    build_context_celery = celery.get("build")
    assert build_context_celery == "." or (
        isinstance(build_context_celery, dict) and build_context_celery.get("context") == "."
    ), "celery service build context must be '.'"
    cmd = celery.get("command", "")
    if isinstance(cmd, list):
        cmd = " ".join(cmd)
    assert "celery" in cmd and "worker" in cmd, "celery service command must run celery worker"

    celery_env = get_env_dict(celery)
    for env_var in [
        "DATABASE_HOST",
        "REDIS_HOST",
        "CELERY_BROKER_URL",
        "MINIO_ENDPOINT_URL",
        "MAIL_HOST",
    ]:
        assert env_var in celery_env, f"celery service must define environment variable '{env_var}'"

    celery_deps = get_depends_on_list(celery)
    for dep in ["postgres", "redis", "mailpit"]:
        assert dep in celery_deps, f"celery service must depend on '{dep}'"
