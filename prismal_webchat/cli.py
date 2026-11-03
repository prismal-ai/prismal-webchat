"""`prismal-webchat` console script (SPEC-WCB-REL-002).

Reflex runs an app from a working directory that holds ``rxconfig.py``,
``assets/`` and the frontend lockfile, not from an installed package. The
wheel ships those files inside the package; ``init`` copies them into a
directory and ``run`` does the same, then execs ``reflex run`` there.

Settings stay in the environment (``PRISMAL_WEBCHAT_*``): nothing secret is
ever put on a command line.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import os
import sys
from collections.abc import Sequence
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path

#: Files a Reflex working directory needs, relative to it.
APP_FILES = ("rxconfig.py", "assets/embed.js", "reflex.lock/package.json", "reflex.lock/bun.lock")
DEFAULT_PORT = 8001
DIST = "prismal-webchat"


def _source(rel: str) -> Traversable:
    """The packaged copy (wheel: ``prismal_webchat/_app``) or the checkout's."""
    packaged = files("prismal_webchat").joinpath("_app", *rel.split("/"))
    if packaged.is_file():
        return packaged
    return Path(__file__).resolve().parents[1].joinpath(rel)


def init_app_dir(app_dir: Path) -> Path:
    """Write (or refresh) the app files into *app_dir*; returns it."""
    for rel in APP_FILES:
        target = app_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_source(rel).read_bytes())
    return app_dir


def _exec(argv: list[str], cwd: Path) -> None:  # pragma: no cover - replaces the process
    os.chdir(cwd)
    os.execv(argv[0], argv)


def _version() -> str:
    try:
        return importlib.metadata.version(DIST)
    except importlib.metadata.PackageNotFoundError:  # pragma: no cover - checkout only
        return "unknown"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=DIST, description="Embeddable prismal web chat.")
    parser.add_argument("--version", action="version", version=f"{DIST} {_version()}")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="write rxconfig.py, assets/ and reflex.lock/ into DIR")
    init.add_argument("app_dir", nargs="?", default=".", type=Path)

    run = sub.add_parser("run", help="init the app dir, then `reflex run` in it")
    run.add_argument("--app-dir", default=".", type=Path)
    run.add_argument("--env", choices=["prod", "dev"], default="prod")
    run.add_argument(
        "--port", type=int, default=None, help=f"prod port (default $PORT or {DEFAULT_PORT})"
    )
    run.add_argument("--host", default="0.0.0.0", help="prod bind address")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    app_dir = init_app_dir(args.app_dir.resolve())
    if args.command == "init":
        print(f"prismal-webchat app files written to {app_dir}")
        return 0

    cmd = [sys.executable, "-m", "reflex", "run", "--env", args.env]
    if args.env == "prod":
        # Prod is one process on one port (docs/deploy.md); dev keeps the
        # rxconfig ports (frontend :3000, backend :8001).
        port = str(args.port or os.environ.get("PORT") or DEFAULT_PORT)
        cmd += ["--single-port", "--frontend-port", port, "--backend-port", port]
        cmd += ["--backend-host", args.host]
    _exec(cmd, app_dir)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
