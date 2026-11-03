"""SPEC-WCB-NFR-005 (as modified by DELTA-2026-10, DELTA-2026-11 and DELTA-2026-11-pypi).

Version pins are deliberate: a bump must be a reviewed PR, so drift fails here.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"

EXPECTED_PINS = {
    "reflex": SpecifierSet(">=0.10,<0.11"),
    "reflex-silverpoint-react": SpecifierSet(">=0.9.1,<0.10"),
    # PyPI distribution of prismal-sdk; the import module is still prismal_sdk.
    "prismal-ai-sdk": SpecifierSet(">=0.3,<1"),
}

# Engine / host must never be dependencies; httpx only arrives via the SDK.
# The engine is published as ``prismal-ai``; ``prismal-sdk`` is the old,
# never-published SDK name.
FORBIDDEN = {"prismal", "prismal-ai", "prismal-server", "prismal-sdk", "httpx"}


def _runtime_requirements() -> dict[str, Requirement]:
    data = tomllib.loads(PYPROJECT.read_text())
    reqs = (Requirement(r) for r in data["project"]["dependencies"])
    return {r.name.lower(): r for r in reqs}


def test_runtime_pins_match_spec() -> None:
    reqs = _runtime_requirements()
    for name, spec in EXPECTED_PINS.items():
        assert name in reqs, f"missing runtime dependency {name}"
        assert reqs[name].specifier == spec, (
            f"{name} pinned {reqs[name].specifier}, spec requires {spec}"
        )


def test_no_forbidden_runtime_dependencies() -> None:
    assert FORBIDDEN.isdisjoint(_runtime_requirements())


def test_python_floor_supports_silverpoint() -> None:
    data = tomllib.loads(PYPROJECT.read_text())
    assert data["project"]["requires-python"] == ">=3.11"


def test_sdk_resolves_from_pypi_not_a_local_path() -> None:
    """CI and Docker cannot see a sibling checkout (DELTA-2026-11-pypi)."""
    data = tomllib.loads(PYPROJECT.read_text())
    sources = data.get("tool", {}).get("uv", {}).get("sources", {})
    assert "prismal-ai-sdk" not in sources
    assert "prismal-sdk" not in sources
