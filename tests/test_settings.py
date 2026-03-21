"""Tests for scanner_plugin.settings module."""
from __future__ import annotations

import pytest

from scanner_plugin.settings import (
    DEFAULT_COLOR,
    DEFAULT_DISPLAY_MODE,
    DEFAULT_FONT_SIZE,
    DEFAULT_TTL,
    DEFAULT_X,
    DEFAULT_Y,
    KEY_COLOR,
    KEY_DISPLAY_MODE,
    KEY_ENABLED,
    KEY_FONT_SIZE,
    KEY_SHOW_COCKPIT,
    KEY_SHOW_GALAXY_MAP,
    KEY_SHOW_SYSTEM_MAP,
    KEY_TTL,
    KEY_SHOW_PANELS,
    KEY_USE_SPANSH,
    KEY_X,
    KEY_Y,
    PluginSettings,
    load_settings,
    save_settings,
)


class _FakeConfig:
    """Minimal stub for EDMC's config object."""

    def __init__(self) -> None:
        self._store: dict[str, object] = {}

    def get_int(self, key: str, *, default: int = 0) -> int:
        val = self._store.get(key)
        return int(val) if val is not None else default

    def get_str(self, key: str, *, default: str = "") -> str:
        val = self._store.get(key)
        return str(val) if val is not None else default

    def set(self, key: str, value: object) -> None:
        self._store[key] = value


class TestLoadSettings:
    def test_defaults(self) -> None:
        cfg = _FakeConfig()
        s = load_settings(cfg)
        assert s.enabled is True
        assert s.color == DEFAULT_COLOR
        assert s.font_size == DEFAULT_FONT_SIZE
        assert s.x == DEFAULT_X
        assert s.y == DEFAULT_Y
        assert s.ttl == DEFAULT_TTL
        assert s.display_mode == DEFAULT_DISPLAY_MODE
        assert s.use_spansh is False
        assert s.show_galaxy_map is True
        assert s.show_system_map is False
        assert s.show_cockpit is True
        assert s.show_panels is False

    def test_custom_values(self) -> None:
        cfg = _FakeConfig()
        cfg._store[KEY_ENABLED] = 0
        cfg._store[KEY_COLOR] = "#00ff00"
        cfg._store[KEY_FONT_SIZE] = "large"
        cfg._store[KEY_X] = 500
        cfg._store[KEY_Y] = 300
        cfg._store[KEY_TTL] = 20
        cfg._store[KEY_DISPLAY_MODE] = "ttl"
        cfg._store[KEY_USE_SPANSH] = 1
        cfg._store[KEY_SHOW_GALAXY_MAP] = 0
        cfg._store[KEY_SHOW_SYSTEM_MAP] = 1
        cfg._store[KEY_SHOW_COCKPIT] = 1
        cfg._store[KEY_SHOW_PANELS] = 1

        s = load_settings(cfg)
        assert s.enabled is False
        assert s.color == "#00ff00"
        assert s.font_size == "large"
        assert s.x == 500
        assert s.y == 300
        assert s.ttl == 20
        assert s.display_mode == "ttl"
        assert s.use_spansh is True
        assert s.show_galaxy_map is False
        assert s.show_system_map is True
        assert s.show_cockpit is True
        assert s.show_panels is True

    def test_invalid_font_size_falls_back(self) -> None:
        cfg = _FakeConfig()
        cfg._store[KEY_FONT_SIZE] = "huge"
        s = load_settings(cfg)
        assert s.font_size == DEFAULT_FONT_SIZE

    def test_invalid_display_mode_falls_back(self) -> None:
        cfg = _FakeConfig()
        cfg._store[KEY_DISPLAY_MODE] = "bogus"
        s = load_settings(cfg)
        assert s.display_mode == DEFAULT_DISPLAY_MODE

    def test_clamping_x(self) -> None:
        cfg = _FakeConfig()
        cfg._store[KEY_X] = 9999
        s = load_settings(cfg)
        assert s.x == 1280

    def test_clamping_y(self) -> None:
        cfg = _FakeConfig()
        cfg._store[KEY_Y] = -10
        s = load_settings(cfg)
        assert s.y == 0

    def test_clamping_ttl_low(self) -> None:
        cfg = _FakeConfig()
        cfg._store[KEY_TTL] = 0
        s = load_settings(cfg)
        assert s.ttl == 5

    def test_clamping_ttl_high(self) -> None:
        cfg = _FakeConfig()
        cfg._store[KEY_TTL] = 100
        s = load_settings(cfg)
        assert s.ttl == 30

    def test_all_screens_off_forces_galaxy_map(self) -> None:
        cfg = _FakeConfig()
        cfg._store[KEY_SHOW_GALAXY_MAP] = 0
        cfg._store[KEY_SHOW_SYSTEM_MAP] = 0
        cfg._store[KEY_SHOW_COCKPIT] = 0
        s = load_settings(cfg)
        assert s.show_galaxy_map is True


class TestSaveSettings:
    def test_roundtrip(self) -> None:
        cfg = _FakeConfig()
        original = PluginSettings(
            enabled=False, color="#aabbcc", font_size="small",
            x=42, y=99, ttl=10, display_mode="ttl", use_spansh=True,
            show_galaxy_map=False, show_system_map=True, show_cockpit=True,
            show_panels=True,
        )
        save_settings(cfg, original)
        loaded = load_settings(cfg)
        assert loaded.enabled == original.enabled
        assert loaded.color == original.color
        assert loaded.font_size == original.font_size
        assert loaded.x == original.x
        assert loaded.y == original.y
        assert loaded.ttl == original.ttl
        assert loaded.display_mode == original.display_mode
        assert loaded.use_spansh == original.use_spansh
        assert loaded.show_galaxy_map == original.show_galaxy_map
        assert loaded.show_system_map == original.show_system_map
        assert loaded.show_cockpit == original.show_cockpit
        assert loaded.show_panels == original.show_panels
