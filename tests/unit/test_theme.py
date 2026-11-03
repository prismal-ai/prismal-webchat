"""WCB-02-05 + WCB-S-02: settings -> silverpoint look (SPEC-WCB-CFG-003, UI-002)."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from prismal_webchat.components.theme import Look, look_for, themed, validate_theme
from prismal_webchat.settings import WebchatSettings


def test_default_settings_pass_contrast_check() -> None:
    validate_theme(WebchatSettings())  # fresh clone must boot (SPEC-WCB-APP-004)


def test_default_accent_is_the_contrast_safe_variant() -> None:
    assert WebchatSettings().accent_color == "#5D4BE5"


def test_light_look_uses_silverpoint_with_accent_ink() -> None:
    look = look_for(WebchatSettings(accent_color="#3A4884"), dark=False)
    assert look == Look(ground="silverpoint", substrate="cream", palette={"ink": "#3A4884"})


def test_dark_look_uses_cyanotype_without_accent() -> None:
    look = look_for(WebchatSettings(accent_color="#3A4884"), dark=True)
    assert look == Look(ground="cyanotype", substrate="prussian", palette={})


@pytest.mark.parametrize("accent", ["#6C5CE7", "#0EA5E9", "#FFEE00"])
def test_unreadable_accent_fails_fast(accent: str) -> None:
    with pytest.raises(ValueError, match="accent_color"):
        validate_theme(WebchatSettings(accent_color=accent))


@pytest.mark.parametrize("accent", ["purple", "#12345", "#GGGGGG", "rgb(0,0,0)"])
def test_accent_must_be_hex(accent: str) -> None:
    with pytest.raises(ValueError):
        WebchatSettings(accent_color=accent)


@pytest.mark.parametrize(
    ("theme", "expected"),
    [("light", '"silverpoint"'), ("dark", '"cyanotype"'), ("auto", "resolvedColorMode")],
)
def test_themed_wraps_children_in_provider(theme: str, expected: str) -> None:
    rendered = str(themed("child", settings=WebchatSettings(theme=theme)))
    assert "SilverpointProvider" in rendered
    assert expected in rendered


def test_settings_object_never_reaches_rendered_tree() -> None:
    secret = "wcb-test-token-DO-NOT-LEAK"
    s = WebchatSettings(token=SecretStr(secret), org_id="acme-org", server_url="https://h.example")
    rendered = str(themed("child", settings=s))
    for leak in (secret, "acme-org", "h.example"):
        assert leak not in rendered


def test_page_chrome_text_contrasts_with_page_background() -> None:
    from reflex_silverpoint_react import contrast_ratio

    from prismal_webchat.components.theme import PAGE_BACKGROUND, PAGE_TEXT

    for ground, background in PAGE_BACKGROUND.items():
        assert contrast_ratio(PAGE_TEXT[ground], background) >= 4.5, ground
