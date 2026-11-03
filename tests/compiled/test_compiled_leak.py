"""WCB-04-01 (compiled part, opt-in: ``uv run pytest -m compile``).

Compiles the real app with sentinel settings and scans the generated frontend
(SPEC-WCB-AUT-002, EMB-004): the token, tenant and upstream URL must be
absent; a harmless presentation sentinel must be present (positive control,
proving the scan sees what the build was fed).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.compile

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / ".web"
SKIP_DIRS = {"node_modules", ".git", "backend"}

SECRETS = {
    "PRISMAL_WEBCHAT_TOKEN": "wcb-compiled-token-SENTINEL-7f3a",
    "PRISMAL_WEBCHAT_ORG_ID": "wcb-compiled-org-SENTINEL-91c2",
    "PRISMAL_WEBCHAT_SERVER_URL": "https://upstream-sentinel-55d1.example",
}
VISIBLE = {"PRISMAL_WEBCHAT_WELCOME_MESSAGE": "wcb-welcome-SENTINEL-4b8e"}


def _text_files(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        if path.is_file() and not SKIP_DIRS.intersection(path.relative_to(root).parts):
            files.append(path)
    return files


@pytest.fixture(scope="module")
def compiled() -> list[Path]:
    env = {**os.environ, **SECRETS, **VISIBLE}
    result = subprocess.run(
        ["uv", "run", "reflex", "compile", "--no-rich"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    files = _text_files(WEB)
    assert files, "compile produced no frontend files"
    return files


def _hits(files: list[Path], needle: str) -> list[str]:
    raw = needle.encode()
    return [str(f.relative_to(WEB)) for f in files if raw in f.read_bytes()]


def test_positive_control_welcome_is_compiled(compiled: list[Path]) -> None:
    assert _hits(compiled, VISIBLE["PRISMAL_WEBCHAT_WELCOME_MESSAGE"])


@pytest.mark.parametrize("var", sorted(SECRETS))
def test_backend_only_settings_absent_from_frontend(compiled: list[Path], var: str) -> None:
    needle = SECRETS[var].removeprefix("https://")
    assert _hits(compiled, needle) == [], var
