"""Settings management for EDMC-SystemStatusOverlay.

Uses EDMC ``config.get_str`` / ``config.get_int`` / ``config.set`` with
namespaced keys so we never collide with other plugins.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger("EDMC-SystemStatusOverlay.settings")

# ── Config key namespace ──────────────────────────────────────────────
_PREFIX = "systemscanner"

KEY_ENABLED = f"{_PREFIX}_enabled"
KEY_COLOR = f"{_PREFIX}_color"
KEY_FONT_SIZE = f"{_PREFIX}_font_size"
KEY_X = f"{_PREFIX}_x"
KEY_Y = f"{_PREFIX}_y"
KEY_TTL = f"{_PREFIX}_ttl"
KEY_DISPLAY_MODE = f"{_PREFIX}_display_mode"
KEY_USE_SPANSH = f"{_PREFIX}_use_spansh"
KEY_SHOW_GALAXY_MAP = f"{_PREFIX}_show_galaxy_map"
KEY_SHOW_SYSTEM_MAP = f"{_PREFIX}_show_system_map"
KEY_SHOW_COCKPIT = f"{_PREFIX}_show_cockpit"
KEY_SHOW_PANELS = f"{_PREFIX}_show_panels"

# ── Defaults ──────────────────────────────────────────────────────────
DEFAULT_ENABLED = 1
DEFAULT_COLOR = "#ff8c00"
DEFAULT_FONT_SIZE = "normal"
DEFAULT_X = 20
DEFAULT_Y = 80
DEFAULT_TTL = 15
DEFAULT_DISPLAY_MODE = "persistent"
DEFAULT_USE_SPANSH = 0
DEFAULT_SHOW_GALAXY_MAP = 1
DEFAULT_SHOW_SYSTEM_MAP = 0
DEFAULT_SHOW_COCKPIT = 1
DEFAULT_SHOW_PANELS = 0

FONT_SIZE_CHOICES = ("small", "normal", "large")
DISPLAY_MODE_CHOICES = ("persistent", "ttl")

# Persistent TTL: ~27 hours, effectively infinite (same approach as Canonn).
PERSISTENT_TTL = 99999


@dataclass
class PluginSettings:
    """Runtime snapshot of the plugin's settings."""

    enabled: bool = True
    color: str = DEFAULT_COLOR
    font_size: str = DEFAULT_FONT_SIZE
    x: int = DEFAULT_X
    y: int = DEFAULT_Y
    ttl: int = DEFAULT_TTL
    display_mode: str = DEFAULT_DISPLAY_MODE
    use_spansh: bool = False
    show_galaxy_map: bool = True
    show_system_map: bool = False
    show_cockpit: bool = True
    show_panels: bool = False


def load_settings(config: Any) -> PluginSettings:
    """Read settings from the EDMC config store."""
    enabled = _get_int(config, KEY_ENABLED, DEFAULT_ENABLED)
    color = _get_str(config, KEY_COLOR, DEFAULT_COLOR)
    font_size = _get_str(config, KEY_FONT_SIZE, DEFAULT_FONT_SIZE)
    if font_size not in FONT_SIZE_CHOICES:
        font_size = DEFAULT_FONT_SIZE
    x = _get_int(config, KEY_X, DEFAULT_X)
    y = _get_int(config, KEY_Y, DEFAULT_Y)
    ttl = _get_int(config, KEY_TTL, DEFAULT_TTL)
    display_mode = _get_str(config, KEY_DISPLAY_MODE, DEFAULT_DISPLAY_MODE)
    if display_mode not in DISPLAY_MODE_CHOICES:
        display_mode = DEFAULT_DISPLAY_MODE
    use_spansh = _get_int(config, KEY_USE_SPANSH, DEFAULT_USE_SPANSH)
    show_galaxy_map = _get_int(config, KEY_SHOW_GALAXY_MAP, DEFAULT_SHOW_GALAXY_MAP)
    show_system_map = _get_int(config, KEY_SHOW_SYSTEM_MAP, DEFAULT_SHOW_SYSTEM_MAP)
    show_cockpit = _get_int(config, KEY_SHOW_COCKPIT, DEFAULT_SHOW_COCKPIT)
    show_panels = _get_int(config, KEY_SHOW_PANELS, DEFAULT_SHOW_PANELS)

    # At least one visibility option must be enabled.
    if not (show_galaxy_map or show_system_map or show_cockpit):
        show_galaxy_map = 1

    return PluginSettings(
        enabled=bool(enabled),
        color=color if color else DEFAULT_COLOR,
        font_size=font_size,
        x=max(0, min(x, 1280)),
        y=max(0, min(y, 960)),
        ttl=max(5, min(ttl, 30)),
        display_mode=display_mode,
        use_spansh=bool(use_spansh),
        show_galaxy_map=bool(show_galaxy_map),
        show_system_map=bool(show_system_map),
        show_cockpit=bool(show_cockpit),
        show_panels=bool(show_panels),
    )


def save_settings(config: Any, settings: PluginSettings) -> None:
    """Persist settings to the EDMC config store."""
    config.set(KEY_ENABLED, int(settings.enabled))
    config.set(KEY_COLOR, settings.color)
    config.set(KEY_FONT_SIZE, settings.font_size)
    config.set(KEY_X, settings.x)
    config.set(KEY_Y, settings.y)
    config.set(KEY_TTL, settings.ttl)
    config.set(KEY_DISPLAY_MODE, settings.display_mode)
    config.set(KEY_USE_SPANSH, int(settings.use_spansh))
    config.set(KEY_SHOW_GALAXY_MAP, int(settings.show_galaxy_map))
    config.set(KEY_SHOW_SYSTEM_MAP, int(settings.show_system_map))
    config.set(KEY_SHOW_COCKPIT, int(settings.show_cockpit))
    config.set(KEY_SHOW_PANELS, int(settings.show_panels))


# ── Helpers ───────────────────────────────────────────────────────────

def _get_int(config: Any, key: str, default: int) -> int:
    """Read an integer from the EDMC config, falling back to *default*."""
    try:
        getter = getattr(config, "get_int", None)
        if callable(getter):
            val = getter(key, default=default)
            return int(val) if val is not None else default
        # Legacy fallback
        val = config.get(key)
        return int(val) if val is not None else default
    except (TypeError, ValueError):
        return default


def _get_str(config: Any, key: str, default: str) -> str:
    """Read a string from the EDMC config, falling back to *default*."""
    try:
        getter = getattr(config, "get_str", None)
        if callable(getter):
            val = getter(key, default=default)
            return str(val) if val else default
        val = config.get(key)
        return str(val) if val else default
    except (TypeError, ValueError):
        return default
