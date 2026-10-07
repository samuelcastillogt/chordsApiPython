import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_pyproject_and_requirements_list_the_same_runtime_dependencies():
    """Vercel installs from pyproject.toml, Docker and CI from requirements.txt: they must agree."""
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["dependencies"]
    requirements = [
        line.strip() for line in (ROOT / "requirements.txt").read_text().splitlines() if line.strip() and not line.startswith("#")
    ]

    assert sorted(pyproject) == sorted(requirements)


def test_vercel_entrypoint_points_to_the_app():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["vercel"]

    assert config["entrypoint"] == "app.main:app"
