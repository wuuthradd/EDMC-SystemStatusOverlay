"""Tests for scanner_plugin.overlay_display formatting helpers."""
from __future__ import annotations

import pytest

from scanner_plugin.api_client import SystemInfo
from scanner_plugin.overlay_display import (
    _determine_status,
    _format_status_text,
    _status_color,
    COLOR_NOT_FOUND,
    COLOR_LOGGED,
    COLOR_SCANNED,
    COLOR_FULLY_SCANNED,
)


class TestDetermineStatus:
    """Verify per-source scan status determination."""

    def test_not_found(self) -> None:
        info = SystemInfo(found=False, source="edsm")
        assert _determine_status(info) == "not_found"

    def test_fully_scanned(self) -> None:
        info = SystemInfo(found=True, body_count=40, bodies_known=40, source="edsm")
        assert _determine_status(info) == "fully_scanned"

    def test_fully_scanned_more_known(self) -> None:
        info = SystemInfo(found=True, body_count=40, bodies_known=42, source="edsm")
        assert _determine_status(info) == "fully_scanned"

    def test_partial_scan(self) -> None:
        info = SystemInfo(found=True, body_count=10, bodies_known=5, source="edsm")
        assert _determine_status(info) == "scanned"

    def test_no_body_count_but_bodies_known(self) -> None:
        info = SystemInfo(found=True, body_count=0, bodies_known=3, source="spansh")
        assert _determine_status(info) == "scanned"

    def test_found_no_bodies(self) -> None:
        info = SystemInfo(found=True, body_count=0, bodies_known=0, source="edsm")
        assert _determine_status(info) == "logged"


class TestFormatStatusText:
    """Verify the status portion that appears after the dash."""

    def test_fully_scanned(self) -> None:
        result = _format_status_text("fully_scanned", 40, 40, "G")
        assert result == "Fully Scanned 40/40 (G)"

    def test_not_found(self) -> None:
        result = _format_status_text("not_found", 0, 0, "F")
        assert result == "Not Found (F)"

    def test_scanned_partial(self) -> None:
        result = _format_status_text("scanned", 3, 10, "B")
        assert result == "Scanned 3/10 (B)"

    def test_scanned_unknown_total(self) -> None:
        result = _format_status_text("scanned", 3, 0, "B")
        assert result == "Scanned 3/? (B)"

    def test_logged_no_bodies(self) -> None:
        result = _format_status_text("logged", 0, 0, "M")
        assert result == "Logged (M)"

    def test_no_star_class(self) -> None:
        result = _format_status_text("not_found", 0, 0, "")
        assert result == "Not Found"


class TestStatusColor:
    """Verify colour mapping for each status."""

    def test_not_found(self) -> None:
        assert _status_color("not_found") == COLOR_NOT_FOUND

    def test_logged(self) -> None:
        assert _status_color("logged") == COLOR_LOGGED

    def test_scanned(self) -> None:
        assert _status_color("scanned") == COLOR_SCANNED

    def test_fully_scanned(self) -> None:
        assert _status_color("fully_scanned") == COLOR_FULLY_SCANNED
