"""WCB-00-02 / WCB-S-01: the Reflex app boots with the silverpoint UI kit.

Offline: inspects the app object and the page component tree; no frontend
compile (SPEC-WCB-NFR-001).
"""

from __future__ import annotations

import reflex as rx
from reflex_silverpoint_react import SilverpointProvider


def test_rxconfig_points_at_architecture_module() -> None:
    import rxconfig

    assert rxconfig.config.app_name == "prismal_webchat"
    assert rxconfig.config.app_module_import == "prismal_webchat.webchat"


def test_app_registers_index_route() -> None:
    from prismal_webchat.webchat import app

    assert isinstance(app, rx.App)
    assert "index" in app._unevaluated_pages


def test_index_page_is_wrapped_in_silverpoint_provider() -> None:
    from prismal_webchat.webchat import index

    assert isinstance(index(), SilverpointProvider)


def test_backend_port_does_not_collide_with_prismal_server_default() -> None:
    # SPEC-WCB-APP-004: a fresh clone talks to a local prismal-server on :8000,
    # so the webchat's own Reflex backend must listen elsewhere.
    import rxconfig

    assert rxconfig.config.backend_port == 8001
    assert rxconfig.config.frontend_port == 3000
