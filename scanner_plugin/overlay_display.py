"""Overlay rendering helpers for EDMC-SystemStatusOverlay.

Sends per-source status lines to the EDMCModernOverlay via the legacy
``edmcoverlay.Overlay`` interface.  Each source line is a single overlay
message coloured by its scan status (red / yellow / green).
"""
from __future__ import annotations

import logging
from typing import Optional

from .api_client import SystemInfo
from .settings import PERSISTENT_TTL, PluginSettings

logger = logging.getLogger("EDMC-SystemStatusOverlay.overlay")

_PLUGIN_NAME = "EDMC-SystemStatusOverlay"
_ID_PREFIX = "sysscanner-"
_LINE_SPACING = 22  # vertical pixels between lines in the 1280x960 canvas

# Status colour constants
COLOR_NOT_FOUND = "#ff0000"
COLOR_LOGGED = "#ff9900"
COLOR_SCANNED = "#ffdd44"
COLOR_FULLY_SCANNED = "#00ff00"

# All message-ID suffixes we may send — used for blanket clearing.
_ALL_SUFFIXES = (
    "header", "edsm", "spansh",
    # Legacy IDs from older versions:
    "info", "edsm-prefix", "edsm-status", "spansh-prefix", "spansh-status",
)

# Overlay instance — lazily created.
_overlay: Optional[object] = None


def _get_overlay() -> object:
    """Return a shared ``edmcoverlay.Overlay`` instance."""
    global _overlay
    if _overlay is None:
        try:
            from EDMCOverlay.edmcoverlay import Overlay  # type: ignore[import-untyped]
            _overlay = Overlay()
        except Exception:
            try:
                from edmcoverlay import Overlay  # type: ignore[import-untyped]
                _overlay = Overlay()
            except Exception as exc:
                logger.error("Cannot import edmcoverlay.Overlay: %s", exc)
                raise
    return _overlay


def register_plugin_group() -> bool:
    """Register our overlay plugin group with EDMCModernOverlay."""
    try:
        try:
            from EDMCModernOverlay.overlay_plugin.overlay_api import (  # type: ignore[import-untyped]
                define_plugin_group,
                PluginGroupingError,
            )
        except ImportError:
            from overlay_plugin.overlay_api import (  # type: ignore[import-untyped]
                define_plugin_group,
                PluginGroupingError,
            )

        define_plugin_group(
            plugin_name=_PLUGIN_NAME,
            plugin_matching_prefixes=[_ID_PREFIX],
            plugin_group_name="Target System Info",
            plugin_group_prefixes=[_ID_PREFIX],
            plugin_group_anchor="nw",
        )
        logger.info("Registered overlay plugin group '%s'", _PLUGIN_NAME)
        return True
    except Exception as exc:
        logger.debug("Could not register overlay plugin group: %s", exc)
        return False


# ── Status helpers ────────────────────────────────────────────────────

def _determine_status(info: SystemInfo) -> str:
    """Return ``"not_found"``, ``"logged"``, ``"scanned"``, or ``"fully_scanned"``."""
    if not info.found:
        return "not_found"
    if info.body_count > 0 and info.bodies_known >= info.body_count:
        return "fully_scanned"
    if info.bodies_known > 0:
        return "scanned"
    return "logged"


def _format_status_text(
    status: str,
    bodies_known: int,
    body_count: int,
    star_class: str,
) -> str:
    """Build the status portion that appears after the dash.

    Examples: ``Not Found (M)``, ``Logged (B)``,
              ``Scanned 3/? (K)``, ``Fully Scanned 40/40 (G)``.
    """
    star = f" ({star_class})" if star_class else ""

    if status == "not_found":
        return f"Not Found{star}"
    if status == "fully_scanned":
        return f"Fully Scanned {bodies_known}/{body_count}{star}"
    if status == "scanned":
        if body_count > 0:
            return f"Scanned {bodies_known}/{body_count}{star}"
        return f"Scanned {bodies_known}/?{star}"
    return f"Logged{star}"


def _status_color(status: str) -> str:
    """Return the overlay colour for a given status."""
    if status == "not_found":
        return COLOR_NOT_FOUND
    if status == "fully_scanned":
        return COLOR_FULLY_SCANNED
    if status == "scanned":
        return COLOR_SCANNED
    return COLOR_LOGGED


# ── Public API ────────────────────────────────────────────────────────

def display_system_info(
    system_name: str,
    edsm: Optional[SystemInfo],
    spansh: Optional[SystemInfo],
    settings: PluginSettings,
    star_class: str = "",
) -> None:
    """Format and send system info to the overlay.

    Layout (both sources)::

        Target: <system_name>
        EDSM: <status>
        Spansh: <status>

    Layout (EDSM only — no provider prefix)::

        Target: <system_name>
        <status>
    """
    try:
        overlay = _get_overlay()
    except Exception:
        return

    ttl = PERSISTENT_TTL if settings.display_mode == "persistent" else settings.ttl
    text_color = settings.color
    size = settings.font_size
    x = settings.x
    y = settings.y
    line = 0
    show_both = settings.use_spansh

    # ── Header — "Target: SystemName" in settings colour ──────────────
    _send(overlay, f"{_ID_PREFIX}header", f"Target: {system_name}",
          text_color, x, y + line * _LINE_SPACING, ttl, size)
    line += 1

    # ── EDSM line — whole line in status colour ───────────────────────
    if edsm is not None:
        status = _determine_status(edsm)
        status_text = _format_status_text(
            status, edsm.bodies_known, edsm.body_count, star_class)
        color = _status_color(status)
        label = f"EDSM: {status_text}" if show_both else status_text

        _send(overlay, f"{_ID_PREFIX}edsm", label,
              color, x, y + line * _LINE_SPACING, ttl, size)
        line += 1

    # ── Spansh line (only when enabled) ───────────────────────────────
    if show_both and spansh is not None:
        status = _determine_status(spansh)
        status_text = _format_status_text(
            status, spansh.bodies_known, spansh.body_count, star_class)
        color = _status_color(status)

        _send(overlay, f"{_ID_PREFIX}spansh", f"Spansh: {status_text}",
              color, x, y + line * _LINE_SPACING, ttl, size)
        line += 1
    else:
        # Clear spansh slot when not in use
        _send(overlay, f"{_ID_PREFIX}spansh", "", "#000000", 0, 0, 0, "normal")

    # Clear legacy message IDs from older versions
    for old in ("info", "edsm-prefix", "edsm-status", "spansh-prefix", "spansh-status"):
        _send(overlay, f"{_ID_PREFIX}{old}", "", "#000000", 0, 0, 0, "normal")


def clear_overlay() -> None:
    """Remove all system-info messages from the overlay."""
    try:
        overlay = _get_overlay()
    except Exception:
        return
    for suffix in _ALL_SUFFIXES:
        _send(overlay, f"{_ID_PREFIX}{suffix}", "", "#000000", 0, 0, 0, "normal")


def _send(
    overlay: object,
    msgid: str,
    text: str,
    color: str,
    x: int,
    y: int,
    ttl: int,
    size: str,
) -> None:
    """Send a single message to the overlay, swallowing errors."""
    try:
        overlay.send_message(msgid, text, color, x, y, ttl=ttl, size=size)  # type: ignore[attr-defined]
    except Exception as exc:
        logger.debug("Overlay send_message failed: %s", exc)
