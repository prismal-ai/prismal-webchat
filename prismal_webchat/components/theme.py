"""Settings -> silverpoint look (WCB-02-05, WCB-S-02; SPEC-WCB-CFG-003, UI-002).

Only derived, non-secret values (ground, substrate, accent ink) reach the
component tree; the settings object itself never does.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

import reflex as rx
from reflex_silverpoint_react import PALETTES, check_palette, silverpoint_provider

from prismal_webchat.settings import WebchatSettings

#: Page background behind the panel, per ground.
PAGE_BACKGROUND = {"silverpoint": "#EDE7DA", "cyanotype": "#1F3A5F"}
#: Text colour for page chrome outside silverpoint components (header).
PAGE_TEXT = {"silverpoint": "#3F4348", "cyanotype": "#FFFFFF"}


@dataclass(frozen=True)
class Look:
    ground: str
    substrate: str
    palette: dict[str, str] = field(default_factory=dict)


def look_for(settings: WebchatSettings, *, dark: bool) -> Look:
    if dark:
        # Cyanotype is a white line on Prussian blue: tone, not colour, so the
        # accent is not applied there (it would be unreadable).
        return Look(ground="cyanotype", substrate="prussian")
    return Look(ground="silverpoint", substrate="cream", palette={"ink": settings.accent_color})


def validate_theme(settings: WebchatSettings) -> None:
    """Fail fast at startup on an accent silverpoint cannot render legibly."""
    base = dataclasses.asdict(PALETTES["silverpoint"])
    merged = {k: v for k, v in base.items() if v} | look_for(settings, dark=False).palette
    problems = check_palette(merged)
    if problems:
        raise ValueError(
            f"PRISMAL_WEBCHAT_ACCENT_COLOR / accent_color {settings.accent_color} fails "
            f"silverpoint contrast: {'; '.join(problems)}"
        )


def themed(*children: rx.Component | str, settings: WebchatSettings) -> rx.Component:
    light, dark = look_for(settings, dark=False), look_for(settings, dark=True)
    if settings.theme == "auto":
        # Follows prefers-color-scheme on the client.
        ground = rx.color_mode_cond(light.ground, dark.ground)
        substrate = rx.color_mode_cond(light.substrate, dark.substrate)
        palette = rx.color_mode_cond(light.palette, dark.palette)
        background = rx.color_mode_cond(PAGE_BACKGROUND[light.ground], PAGE_BACKGROUND[dark.ground])
        color = rx.color_mode_cond(PAGE_TEXT[light.ground], PAGE_TEXT[dark.ground])
    else:
        look = dark if settings.theme == "dark" else light
        ground, substrate, palette = look.ground, look.substrate, look.palette
        background = PAGE_BACKGROUND[look.ground]
        color = PAGE_TEXT[look.ground]
    return silverpoint_provider(
        rx.box(*children, background=background, color=color, min_height="100dvh", width="100%"),
        ground=ground,
        substrate=substrate,
        palette=palette,
    )
