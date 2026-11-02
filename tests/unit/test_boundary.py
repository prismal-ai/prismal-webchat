"""WCB-00-04: SPEC-WCB-APP-002 boundary guard.

prismal_webchat/ must not import the engine (``prismal``), the host
(``prismal_server``) or any HTTP client: all upstream traffic goes through
``prismal_sdk``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.boundary import forbidden_imports

PACKAGE = Path(__file__).resolve().parents[2] / "prismal_webchat"


@pytest.mark.parametrize(
    "source",
    [
        "import prismal",
        "import prismal.agents",
        "from prismal import graph",
        "from prismal.security import layers",
        "import prismal_server",
        "from prismal_server.app import app",
        "import httpx",
        "from httpx import AsyncClient",
        "import requests",
        "import aiohttp",
        "import urllib3",
        "import urllib.request",
        "from urllib import request",
        "from http import client",
        "import http.client",
        "def f():\n    import httpx\n",  # nested imports count too
        "import importlib\nimportlib.import_module('httpx')",
        "__import__('prismal')",
    ],
)
def test_detects_forbidden_imports(source: str) -> None:
    assert forbidden_imports(source), source


@pytest.mark.parametrize(
    "source",
    [
        "import prismal_sdk",
        "from prismal_sdk import AsyncPrismalClient",
        "from prismal_sdk.agui import RunFinished",
        "import prismal_webchat.settings",
        "from urllib.parse import urlsplit",
        "import reflex as rx",
    ],
)
def test_allows_sdk_and_unrelated_imports(source: str) -> None:
    assert forbidden_imports(source) == []


def test_package_respects_boundary() -> None:
    files = sorted(PACKAGE.rglob("*.py"))
    assert files, "no sources found"
    violations = {
        str(path.relative_to(PACKAGE.parent)): found
        for path in files
        if (found := forbidden_imports(path.read_text()))
    }
    assert violations == {}
