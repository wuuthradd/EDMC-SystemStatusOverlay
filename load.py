"""EDMC-SystemStatusOverlay — Target System Info Overlay Plugin for EDMC.

Queries EDSM and Spansh databases when the player targets a new system and
displays body count and scan status on the Modern Overlay.

All subpackage imports are deferred to function bodies because EDMC loads
``load.py`` before the plugin directory is guaranteed to be on sys.path.
"""
from __future__ import annotations

import logging
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Any, Dict, Optional, Tuple

# ── Plugin metadata ───────────────────────────────────────────────────
PLUGIN_NAME = "EDMC-SystemStatusOverlay"
PLUGIN_VERSION = "1.0.0"

# ── Logging ───────────────────────────────────────────────────────────
logger = logging.getLogger(PLUGIN_NAME)

# ── Runtime state ─────────────────────────────────────────────────────
_plugin_dir: Optional[Path] = None
_config: Optional[Any] = None
_settings: Optional[Any] = None  # scanner_plugin.settings.PluginSettings
_lock = threading.Lock()
_overlay_group_registered = False

# ── Target tracking & rate limiting ──────────────────────────────────
_current_target: Optional[str] = None
_current_target_star_class: str = ""
_last_query_time: float = 0.0
_RATE_LIMIT_SECONDS: float = 2.0
_pending_timer: Optional[threading.Timer] = None

# ── Screen state & cached display data ───────────────────────────────
# Possible screens: "galaxy_map", "system_map", "cockpit"
_current_screen: str = "cockpit"
_overlay_visible: bool = False
# Cached data from last successful query (for re-display on screen change)
_cached_display: Optional[Tuple[str, Any, Any, str]] = None  # (name, edsm, spansh, star_class)

# GuiFocus values from Status.json (Frontier documentation)
_GUIFOCUS_COCKPIT = 0
_GUIFOCUS_INTERNAL_PANEL = 1
_GUIFOCUS_EXTERNAL_PANEL = 2
_GUIFOCUS_COMMS_PANEL = 3
_GUIFOCUS_ROLE_PANEL = 4
_GUIFOCUS_STATION_SERVICES = 5
_GUIFOCUS_GALAXY_MAP = 6
_GUIFOCUS_SYSTEM_MAP = 7
_GUIFOCUS_ORRERY = 8
_GUIFOCUS_FSS = 9
_GUIFOCUS_SAA = 10

_PANEL_FOCUSES = frozenset({
    _GUIFOCUS_INTERNAL_PANEL, _GUIFOCUS_EXTERNAL_PANEL,
    _GUIFOCUS_COMMS_PANEL, _GUIFOCUS_ROLE_PANEL,
    _GUIFOCUS_STATION_SERVICES,
})


def _guifocus_to_screen(gui_focus: int) -> str:
    """Map a GuiFocus value from Status.json to a screen identifier.

    FSS (9) and SAA (10) are mapped to their own identifiers so the
    overlay is hidden on those screens by default.
    """
    if gui_focus == _GUIFOCUS_GALAXY_MAP:
        return "galaxy_map"
    if gui_focus in (_GUIFOCUS_SYSTEM_MAP, _GUIFOCUS_ORRERY):
        return "system_map"
    if gui_focus in (_GUIFOCUS_FSS, _GUIFOCUS_SAA):
        return "fss"
    if gui_focus in _PANEL_FOCUSES:
        return "panels"
    return "cockpit"


def _is_screen_allowed(screen: str) -> bool:
    """Check if the overlay should be visible on the given screen."""
    if screen == "fss":
        return False
    if _settings is None:
        return screen not in ("fss", "panels")
    if screen == "galaxy_map":
        return _settings.show_galaxy_map
    if screen == "system_map":
        return _settings.show_system_map
    if screen == "cockpit":
        return _settings.show_cockpit
    if screen == "panels":
        return _settings.show_panels
    return False


def _ensure_path(plugin_dir: Path) -> None:
    """Make sure the plugin directory is on sys.path so scanner_plugin imports work."""
    d = str(plugin_dir)
    if d not in sys.path:
        sys.path.insert(0, d)


# =====================================================================
# EDMC Plugin Hooks
# =====================================================================

def plugin_start3(plugin_dir: str) -> str:
    """EDMC entry point — initialise the plugin."""
    global _plugin_dir, _config, _settings

    _plugin_dir = Path(plugin_dir)
    _ensure_path(_plugin_dir)

    from scanner_plugin.settings import load_settings, PluginSettings

    try:
        from config import config as edmc_config  # type: ignore[import-untyped]
        _config = edmc_config
    except ImportError:
        logger.warning("EDMC config module not available — using defaults")
        _config = None

    _settings = load_settings(_config) if _config else PluginSettings()

    _try_register_overlay_group()

    logger.info("%s v%s started", PLUGIN_NAME, PLUGIN_VERSION)
    return PLUGIN_NAME


def plugin_stop() -> None:
    """EDMC shutdown hook — clean up resources."""
    global _pending_timer
    with _lock:
        if _pending_timer is not None:
            _pending_timer.cancel()
            _pending_timer = None
    try:
        from scanner_plugin.overlay_display import clear_overlay
        clear_overlay()
    except Exception:
        pass
    logger.info("%s stopped", PLUGIN_NAME)


def plugin_app(parent: Any) -> None:
    """No main-window widget for this plugin."""
    return None


# ── Preferences UI state ──────────────────────────────────────────────
_pref_enabled: Optional[tk.IntVar] = None
_pref_color: Optional[tk.StringVar] = None
_pref_font: Optional[tk.StringVar] = None
_pref_x: Optional[tk.IntVar] = None
_pref_y: Optional[tk.IntVar] = None
_pref_ttl: Optional[tk.IntVar] = None
_pref_display_mode: Optional[tk.StringVar] = None
_pref_use_spansh: Optional[tk.IntVar] = None
_pref_show_galaxy_map: Optional[tk.IntVar] = None
_pref_show_system_map: Optional[tk.IntVar] = None
_pref_show_cockpit: Optional[tk.IntVar] = None
_pref_show_panels: Optional[tk.IntVar] = None
_ttl_spinbox: Optional[tk.Spinbox] = None
_ttl_label: Optional[Any] = None


def plugin_prefs(parent: Any, cmdr: str, is_beta: bool) -> Any:
    """Build the settings tab in EDMC Preferences."""
    global _pref_enabled, _pref_color, _pref_font, _pref_x, _pref_y
    global _pref_ttl, _pref_display_mode, _pref_use_spansh
    global _pref_show_galaxy_map, _pref_show_system_map, _pref_show_cockpit
    global _pref_show_panels, _ttl_spinbox, _ttl_label

    from scanner_plugin.settings import (
        DEFAULT_COLOR, DEFAULT_DISPLAY_MODE, DEFAULT_FONT_SIZE,
        DEFAULT_TTL, DEFAULT_X, DEFAULT_Y, FONT_SIZE_CHOICES,
        PluginSettings,
    )

    # Use current settings or dataclass defaults.
    s = _settings if _settings is not None else PluginSettings()

    try:
        import myNotebook as nb  # type: ignore[import-untyped]
        Label = nb.Label
        Frame = nb.Frame
        Checkbutton = nb.Checkbutton
    except ImportError:
        Label = tk.Label  # type: ignore[misc]
        Frame = tk.Frame  # type: ignore[misc]
        Checkbutton = tk.Checkbutton  # type: ignore[misc]

    frame = Frame(parent)
    frame.columnconfigure(1, weight=1)
    row = 0

    # Title
    Label(frame, text=f"{PLUGIN_NAME} v{PLUGIN_VERSION}").grid(
        row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(5, 10)
    )
    row += 1

    # Enabled
    _pref_enabled = tk.IntVar(value=int(s.enabled))
    Checkbutton(frame, text="Enable overlay", variable=_pref_enabled).grid(
        row=row, column=0, columnspan=2, sticky=tk.W, padx=5
    )
    row += 1

    # Use Spansh
    _pref_use_spansh = tk.IntVar(value=int(s.use_spansh))
    spansh_frame = tk.Frame(frame)
    Checkbutton(spansh_frame, text="Also query Spansh", variable=_pref_use_spansh).pack(
        side=tk.LEFT
    )
    Label(spansh_frame, text="(EDSM only by default)").pack(side=tk.LEFT, padx=(5, 0))
    spansh_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5)
    row += 1

    # ── Show overlay on ───────────────────────────────────────────────
    Label(frame, text="Show overlay on:").grid(
        row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(10, 2)
    )
    row += 1

    _pref_show_galaxy_map = tk.IntVar(value=int(s.show_galaxy_map))
    Checkbutton(frame, text="Galaxy Map", variable=_pref_show_galaxy_map,
                command=_enforce_at_least_one_screen).grid(
        row=row, column=0, columnspan=2, sticky=tk.W, padx=20
    )
    row += 1

    _pref_show_system_map = tk.IntVar(value=int(s.show_system_map))
    Checkbutton(frame, text="System Map", variable=_pref_show_system_map,
                command=_enforce_at_least_one_screen).grid(
        row=row, column=0, columnspan=2, sticky=tk.W, padx=20
    )
    row += 1

    _pref_show_cockpit = tk.IntVar(value=int(s.show_cockpit))
    Checkbutton(frame, text="Cockpit", variable=_pref_show_cockpit,
                command=_enforce_at_least_one_screen).grid(
        row=row, column=0, columnspan=2, sticky=tk.W, padx=20
    )
    row += 1

    _pref_show_panels = tk.IntVar(value=int(s.show_panels))
    Checkbutton(frame, text="Panels (internal, external, comms, role, station)",
                variable=_pref_show_panels).grid(
        row=row, column=0, columnspan=2, sticky=tk.W, padx=20
    )
    row += 1

    # ── Color picker ──────────────────────────────────────────────────
    Label(frame, text="Text color:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
    _pref_color = tk.StringVar(value=s.color)
    color_frame = tk.Frame(frame)
    color_swatch = tk.Label(color_frame, bg=s.color, width=3, relief="sunken")
    color_swatch.pack(side=tk.LEFT, padx=(0, 5))

    def _pick_color() -> None:
        from tkinter.colorchooser import askcolor
        result = askcolor(color=_pref_color.get(), title="Choose text color")
        if result[1] is not None:
            _pref_color.set(result[1])
            color_swatch.configure(bg=result[1])

    tk.Button(color_frame, text="Pick Color...", command=_pick_color).pack(side=tk.LEFT)
    color_frame.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
    row += 1

    # Font size
    Label(frame, text="Font size:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
    _pref_font = tk.StringVar(value=s.font_size)
    ttk.Combobox(
        frame, textvariable=_pref_font,
        values=list(FONT_SIZE_CHOICES), state="readonly", width=8
    ).grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
    row += 1

    # Position X
    Label(frame, text="Position X:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
    _pref_x = tk.IntVar(value=s.x)
    tk.Spinbox(frame, from_=0, to=1280, textvariable=_pref_x, width=6).grid(
        row=row, column=1, sticky=tk.W, padx=5, pady=2
    )
    row += 1

    # Position Y
    Label(frame, text="Position Y:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
    _pref_y = tk.IntVar(value=s.y)
    tk.Spinbox(frame, from_=0, to=960, textvariable=_pref_y, width=6).grid(
        row=row, column=1, sticky=tk.W, padx=5, pady=2
    )
    row += 1

    # ── Display mode ──────────────────────────────────────────────────
    Label(frame, text="Display mode:").grid(
        row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(10, 2)
    )
    row += 1

    _pref_display_mode = tk.StringVar(value=s.display_mode)

    tk.Radiobutton(
        frame, text="Persistent (until system reached)",
        variable=_pref_display_mode, value="persistent",
        command=_toggle_ttl_state,
    ).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=20)
    row += 1

    tk.Radiobutton(
        frame, text="Timed (TTL)",
        variable=_pref_display_mode, value="ttl",
        command=_toggle_ttl_state,
    ).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=20)
    row += 1

    # TTL spinbox (range 5-30, disabled when persistent)
    _ttl_label = Label(frame, text="Display time (s):")
    _ttl_label.grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
    _pref_ttl = tk.IntVar(value=s.ttl)
    _ttl_spinbox = tk.Spinbox(frame, from_=5, to=30, textvariable=_pref_ttl, width=6)
    _ttl_spinbox.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
    row += 1

    _toggle_ttl_state()

    return frame


def _toggle_ttl_state() -> None:
    """Enable/disable TTL spinbox based on display mode selection."""
    if _pref_display_mode is None or _ttl_spinbox is None:
        return
    state = "normal" if _pref_display_mode.get() == "ttl" else "disabled"
    _ttl_spinbox.configure(state=state)


def _enforce_at_least_one_screen() -> None:
    """If all screen checkboxes are unchecked, re-check Galaxy Map."""
    if (_pref_show_galaxy_map is None or _pref_show_system_map is None
            or _pref_show_cockpit is None):
        return
    if not (_pref_show_galaxy_map.get() or _pref_show_system_map.get()
            or _pref_show_cockpit.get()):
        _pref_show_galaxy_map.set(1)


def prefs_changed(cmdr: str, is_beta: bool) -> None:
    """Called when the user clicks OK/Apply in EDMC Preferences."""
    global _settings
    if _config is None:
        return

    try:
        from scanner_plugin.settings import (
            DEFAULT_COLOR, DEFAULT_DISPLAY_MODE, DEFAULT_FONT_SIZE,
            DEFAULT_TTL, DEFAULT_X, DEFAULT_Y,
            PluginSettings, save_settings,
        )

        show_gm = bool(_pref_show_galaxy_map.get()) if _pref_show_galaxy_map else True
        show_sm = bool(_pref_show_system_map.get()) if _pref_show_system_map else False
        show_cp = bool(_pref_show_cockpit.get()) if _pref_show_cockpit else True

        # Safety: at least one must be on.
        if not (show_gm or show_sm or show_cp):
            show_gm = True

        new_settings = PluginSettings(
            enabled=bool(_pref_enabled.get()) if _pref_enabled else True,
            color=_pref_color.get() if _pref_color else DEFAULT_COLOR,
            font_size=_pref_font.get() if _pref_font else DEFAULT_FONT_SIZE,
            x=_pref_x.get() if _pref_x else DEFAULT_X,
            y=_pref_y.get() if _pref_y else DEFAULT_Y,
            ttl=_pref_ttl.get() if _pref_ttl else DEFAULT_TTL,
            display_mode=_pref_display_mode.get() if _pref_display_mode else DEFAULT_DISPLAY_MODE,
            use_spansh=bool(_pref_use_spansh.get()) if _pref_use_spansh else False,
            show_galaxy_map=show_gm,
            show_system_map=show_sm,
            show_cockpit=show_cp,
            show_panels=bool(_pref_show_panels.get()) if _pref_show_panels else False,
        )
        save_settings(_config, new_settings)
        _settings = new_settings
        logger.debug("Settings saved: %s", _settings)
    except Exception as exc:
        logger.error("Failed to save settings: %s", exc, exc_info=exc)


def journal_entry(
    cmdr: str,
    is_beta: bool,
    system: str,
    station: str,
    entry: Dict[str, Any],
    state: Dict[str, Any],
) -> Optional[str]:
    """EDMC journal hook — listen for target and navigation events."""
    event = entry.get("event")

    if event == "FSDTarget":
        _handle_fsd_target(entry)
    elif event == "FSDJump":
        _handle_fsd_jump(entry)
    elif event == "NavRouteClear":
        _handle_clear_target()

    return None


def dashboard_entry(cmdr: str, is_beta: bool, entry: Dict[str, Any]) -> None:
    """EDMC dashboard hook — called frequently with Status.json data.

    Uses GuiFocus for instant screen detection (~10-20Hz polling) and
    checks StatusFlags for target deselection.
    """
    gui_focus = int(entry.get("GuiFocus", 0))
    new_screen = _guifocus_to_screen(gui_focus)
    _handle_screen_change(new_screen)


# =====================================================================
# Internal helpers
# =====================================================================

def _handle_fsd_target(entry: Dict[str, Any]) -> None:
    """Process an FSDTarget event: schedule an API query with rate limiting."""
    global _current_target, _current_target_star_class, _last_query_time, _pending_timer

    if _settings is not None and not _settings.enabled:
        return

    target_name = entry.get("Name", "")
    system_address = entry.get("SystemAddress")
    star_class = entry.get("StarClass", "")

    if not target_name:
        return

    with _lock:
        _current_target = target_name
        _current_target_star_class = star_class

        # Cancel any pending debounced query
        if _pending_timer is not None:
            _pending_timer.cancel()
            _pending_timer = None

        now = time.monotonic()
        elapsed = now - _last_query_time

        if elapsed >= _RATE_LIMIT_SECONDS:
            _last_query_time = now
            _dispatch_query(target_name, system_address, star_class)
        else:
            delay = _RATE_LIMIT_SECONDS - elapsed
            _pending_timer = threading.Timer(
                delay,
                _debounced_dispatch,
                args=(target_name, system_address, star_class),
            )
            _pending_timer.daemon = True
            _pending_timer.start()


def _debounced_dispatch(target_name: str, system_address: Optional[int], star_class: str) -> None:
    """Called by the rate-limit timer after the delay expires."""
    global _last_query_time, _pending_timer
    with _lock:
        _pending_timer = None
        if _current_target != target_name:
            return
        _last_query_time = time.monotonic()
    _dispatch_query(target_name, system_address, star_class)


def _dispatch_query(target_name: str, system_address: Optional[int], star_class: str) -> None:
    """Spawn a worker thread for the API queries."""
    thread = threading.Thread(
        target=_query_and_display,
        args=(target_name, system_address, star_class),
        name=f"{PLUGIN_NAME}-query",
        daemon=True,
    )
    thread.start()


def _handle_fsd_jump(entry: Dict[str, Any]) -> None:
    """Process an FSDJump event: clear overlay if we arrived at the target."""
    global _current_target, _current_target_star_class, _cached_display

    jumped_system = entry.get("StarSystem", "")
    should_clear = False
    with _lock:
        if _current_target and jumped_system == _current_target:
            _current_target = None
            _current_target_star_class = ""
            _cached_display = None
            should_clear = True

    if should_clear:
        try:
            from scanner_plugin.overlay_display import clear_overlay
            clear_overlay()
        except Exception as exc:
            logger.debug("Failed to clear overlay on FSDJump: %s", exc)


def _handle_clear_target() -> None:
    """Clear the overlay when the navigation route is cleared."""
    global _current_target, _current_target_star_class, _cached_display
    with _lock:
        _current_target = None
        _current_target_star_class = ""
        _cached_display = None
    try:
        from scanner_plugin.overlay_display import clear_overlay
        clear_overlay()
    except Exception as exc:
        logger.debug("Failed to clear overlay on NavRouteClear: %s", exc)


def _handle_screen_change(new_screen: str) -> None:
    """Show or hide the overlay based on which screen the player is on."""
    global _current_screen, _overlay_visible

    if new_screen == _current_screen:
        return

    _current_screen = new_screen
    allowed = _is_screen_allowed(new_screen)

    if allowed:
        # Transitioning to an allowed screen — re-display cached data
        if _cached_display is not None and _current_target is not None:
            name, edsm, spansh, star_class = _cached_display
            try:
                from scanner_plugin.overlay_display import display_system_info
                from scanner_plugin.settings import PluginSettings
                settings = _settings if _settings is not None else PluginSettings()
                display_system_info(name, edsm, spansh, settings, star_class)
                _overlay_visible = True
            except Exception as exc:
                logger.debug("Failed to re-display overlay on screen change: %s", exc)
    else:
        # Transitioning to a disallowed screen — hide overlay
        if _overlay_visible:
            try:
                from scanner_plugin.overlay_display import clear_overlay
                clear_overlay()
                _overlay_visible = False
            except Exception as exc:
                logger.debug("Failed to hide overlay on screen change: %s", exc)


def _try_register_overlay_group() -> None:
    """Attempt to register our overlay plugin group with Modern Overlay."""
    global _overlay_group_registered
    if _overlay_group_registered:
        return
    try:
        from scanner_plugin.overlay_display import register_plugin_group
        _overlay_group_registered = register_plugin_group()
    except Exception as exc:
        logger.debug("Overlay group registration deferred: %s", exc)


def _query_and_display(system_name: str, system_address: Optional[int], star_class: str = "") -> None:
    """Worker thread: query both APIs and push results to the overlay."""
    global _cached_display, _overlay_visible

    from scanner_plugin.api_client import SystemInfo, query_edsm, query_spansh
    from scanner_plugin.overlay_display import display_system_info
    from scanner_plugin.settings import PluginSettings

    settings = _settings if _settings is not None else PluginSettings()

    _try_register_overlay_group()

    edsm_info: Optional[SystemInfo] = None
    spansh_info: Optional[SystemInfo] = None

    try:
        edsm_info = query_edsm(system_name)
    except Exception as exc:
        logger.debug("EDSM query failed: %s", exc)
        edsm_info = SystemInfo(found=False, name=system_name, source="edsm", error=str(exc))

    if settings.use_spansh and system_address is not None:
        try:
            spansh_info = query_spansh(system_address)
        except Exception as exc:
            logger.debug("Spansh query failed: %s", exc)
            spansh_info = SystemInfo(found=False, source="spansh", error=str(exc))

    # Stale result guard
    with _lock:
        if _current_target != system_name:
            return
        _cached_display = (system_name, edsm_info, spansh_info, star_class)

    # Only display if current screen is allowed
    if not _is_screen_allowed(_current_screen):
        _overlay_visible = False
        return

    try:
        display_system_info(system_name, edsm_info, spansh_info, settings, star_class)
        _overlay_visible = True
    except Exception as exc:
        logger.debug("Overlay display failed: %s", exc)
