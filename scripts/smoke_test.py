"""Post-build smoke test for a built distribution (SPEC-WCB-REL-002).

The release workflow runs it against the freshly built wheel and sdist, in an
isolated environment holding only the distribution and its runtime
dependencies, from an empty directory:

    uv run --isolated --no-project --with dist/*.whl scripts/smoke_test.py [--compile]

It catches what the test suite cannot see: a module or app file left out of
the artifact, a missing console script, or an app that does not compile when
installed from site-packages. ``--compile`` runs a real ``reflex compile`` in
the directory ``prismal-webchat init`` writes (needs network for bun). It does
no I/O against a prismal-server.

It lives outside ``tests/`` so pytest never collects it.
"""

from __future__ import annotations

import importlib.metadata
import os
import pathlib
import subprocess
import sys
import tempfile

failures: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


import prismal_webchat  # noqa: E402
from prismal_webchat import cli  # noqa: E402

# Imported from the installed artifact, not from a source checkout.
location = pathlib.Path(prismal_webchat.__file__).resolve()
check("site-packages" in location.parts, f"imported from a checkout: {location}")

dist = importlib.metadata.distribution("prismal-webchat")
scripts = {ep.name: ep.value for ep in dist.entry_points if ep.group == "console_scripts"}
check(
    scripts.get("prismal-webchat") == "prismal_webchat.cli:main",
    f"console script missing or wrong: {scripts}",
)
expected = os.environ.get("EXPECTED_VERSION")
check(expected is None or dist.version == expected, f"version {dist.version} != {expected}")

requires = [r.split(";")[0].replace(" ", "") for r in dist.requires or []]
check(any(r.startswith("prismal-ai-sdk") for r in requires), f"SDK not required: {requires}")
for forbidden in ("prismal-ai>", "prismal-ai=", "prismal-server", "httpx"):
    check(not any(r.startswith(forbidden) for r in requires), f"forbidden dep: {forbidden}")

with tempfile.TemporaryDirectory() as tmp:
    app = pathlib.Path(tmp) / "app"
    done = subprocess.run(
        ["prismal-webchat", "init", str(app)], capture_output=True, text=True, check=False
    )
    check(done.returncode == 0, f"`prismal-webchat init` failed: {done.stderr}")
    for rel in cli.APP_FILES:
        path = app / rel
        check(path.is_file() and path.stat().st_size > 0, f"init did not write {rel}")
    check("app_module_import" in (app / "rxconfig.py").read_text(), "rxconfig.py is not the app's")
    check("PrismalChat" in (app / "assets/embed.js").read_text(), "embed.js is not the loader")

    if "--compile" in sys.argv:
        env = {**os.environ, "REFLEX_TELEMETRY_ENABLED": "false"}
        compiled = subprocess.run(
            [sys.executable, "-m", "reflex", "compile", "--no-rich"],
            cwd=app,
            env=env,
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
        output = compiled.stdout + compiled.stderr
        check(compiled.returncode == 0, f"reflex compile failed:\n{output}")

if failures:
    print("SMOKE TEST FAILED:", *failures, sep="\n  - ")
    raise SystemExit(1)
print(f"smoke test OK: prismal-webchat {dist.version} from {location.parent}")
