import subprocess
import sys
import tomllib
from pathlib import Path

from django.conf import settings


def test_ruff_listed_in_pipfile_and_requirements():
    base_dir = Path(settings.BASE_DIR)
    pipfile_path = base_dir / "Pipfile"
    requirements_path = base_dir / "requirements.txt"

    assert pipfile_path.exists(), "Pipfile must exist"
    assert requirements_path.exists(), "requirements.txt must exist"

    pipfile_content = pipfile_path.read_text(encoding="utf-8").lower()
    requirements_content = requirements_path.read_text(encoding="utf-8").lower()

    assert "ruff" in pipfile_content, "ruff must be listed in Pipfile"
    assert "ruff" in requirements_content, "ruff must be listed in requirements.txt"


def test_pyproject_toml_configuration():
    base_dir = Path(settings.BASE_DIR)
    pyproject_path = base_dir / "pyproject.toml"

    assert pyproject_path.exists(), "pyproject.toml must exist at project root"

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    assert "tool" in config and "ruff" in config["tool"], "[tool.ruff] section must be present in pyproject.toml"
    ruff_conf = config["tool"]["ruff"]

    assert ruff_conf.get("target-version") == "py312"
    assert ruff_conf.get("line-length") == 120

    extend_exclude = ruff_conf.get("extend-exclude", [])
    for expected in ["migrations", ".scratch", ".pytest_cache"]:
        assert any(expected in item for item in extend_exclude), f"{expected} must be in extend-exclude"

    assert "lint" in ruff_conf, "[tool.ruff.lint] section must be present"
    lint_conf = ruff_conf["lint"]
    select = lint_conf.get("select", [])
    for rule in ["E", "F", "I", "W"]:
        assert rule in select, f"Rule {rule} must be in select"


def test_ruff_check_passes():
    base_dir = Path(settings.BASE_DIR)
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "."],
        cwd=str(base_dir),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"ruff check failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"


def test_ruff_format_check_passes():
    base_dir = Path(settings.BASE_DIR)
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--check", "."],
        cwd=str(base_dir),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"ruff format --check failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
