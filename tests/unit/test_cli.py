"""SPEC-WCB-REL-002: the `prismal-webchat` console script (PyPI distribution).

`init` materializes a Reflex working directory (rxconfig.py, assets/embed.js,
reflex.lock/) from the installed package; `run` does that and execs
`reflex run` there. No network, no frontend compile.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from prismal_webchat import cli

ROOT = Path(__file__).resolve().parents[2]
APP_FILES = ["rxconfig.py", "assets/embed.js", "reflex.lock/package.json", "reflex.lock/bun.lock"]


def test_init_writes_the_app_files_matching_the_repo(tmp_path: Path) -> None:
    assert cli.main(["init", str(tmp_path / "app")]) == 0
    for rel in APP_FILES:
        assert (tmp_path / "app" / rel).read_bytes() == (ROOT / rel).read_bytes(), rel


def test_init_refreshes_stale_files(tmp_path: Path) -> None:
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "embed.js").write_text("stale")
    cli.main(["init", str(tmp_path)])
    fresh = (ROOT / "assets/embed.js").read_bytes()
    assert (tmp_path / "assets" / "embed.js").read_bytes() == fresh


def test_run_defaults_to_prod_single_port(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, list[str], Path]] = []
    monkeypatch.setattr(cli, "_exec", lambda argv, cwd: calls.append((argv[0], argv, cwd)))
    monkeypatch.delenv("PORT", raising=False)
    assert cli.main(["run", "--app-dir", str(tmp_path)]) == 0
    (_, argv, cwd) = calls[0]
    assert cwd == tmp_path
    assert argv[1:] == [
        "-m",
        "reflex",
        "run",
        "--env",
        "prod",
        "--single-port",
        "--frontend-port",
        "8001",
        "--backend-port",
        "8001",
        "--backend-host",
        "0.0.0.0",
    ]
    assert (tmp_path / "rxconfig.py").is_file()


def test_run_port_from_flag_or_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[list[str]] = []
    monkeypatch.setattr(cli, "_exec", lambda argv, cwd: seen.append(argv))
    monkeypatch.setenv("PORT", "9100")
    cli.main(["run", "--app-dir", str(tmp_path)])
    cli.main(["run", "--app-dir", str(tmp_path), "--port", "9200", "--host", "127.0.0.1"])
    assert seen[0][seen[0].index("--frontend-port") + 1] == "9100"
    assert seen[1][seen[1].index("--backend-port") + 1] == "9200"
    assert seen[1][-1] == "127.0.0.1"


def test_run_dev_keeps_rxconfig_ports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[list[str]] = []
    monkeypatch.setattr(cli, "_exec", lambda argv, cwd: seen.append(argv))
    cli.main(["run", "--app-dir", str(tmp_path), "--env", "dev"])
    assert seen[0][1:] == ["-m", "reflex", "run", "--env", "dev"]


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.startswith("prismal-webchat ")


def test_no_secret_or_settings_in_argv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The token stays in the environment; it is never put on a command line."""
    seen: list[list[str]] = []
    monkeypatch.setattr(cli, "_exec", lambda argv, cwd: seen.append(argv))
    monkeypatch.setenv("PRISMAL_WEBCHAT_TOKEN", "cli-token-SENTINEL-9e1a")
    cli.main(["run", "--app-dir", str(tmp_path)])
    assert "cli-token-SENTINEL-9e1a" not in " ".join(seen[0])
