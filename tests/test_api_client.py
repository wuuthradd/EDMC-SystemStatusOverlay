"""Tests for scanner_plugin.api_client module."""
from __future__ import annotations

import requests
import pytest
import requests_mock as rm

from scanner_plugin.api_client import SystemInfo, query_edsm, query_spansh


# ── EDSM Tests ────────────────────────────────────────────────────────


class TestQueryEDSM:
    """Test suite for the query_edsm function."""

    def test_found_system(self, requests_mock: rm.Mocker) -> None:
        """A known system returns body and value data."""
        requests_mock.get(
            "https://www.edsm.net/api-system-v1/bodies",
            json={
                "id": 27,
                "name": "Sol",
                "bodyCount": 40,
                "bodies": [{"name": f"Body {i}"} for i in range(40)],
            },
        )
        requests_mock.get(
            "https://www.edsm.net/api-system-v1/estimated-value",
            json={
                "estimatedValue": 605861,
                "estimatedValueMapped": 2213988,
                "valuableBodies": [
                    {"bodyName": "Earth", "valueMax": 607028},
                ],
            },
        )

        result = query_edsm("Sol")

        assert result.found is True
        assert result.name == "Sol"
        assert result.body_count == 40
        assert result.bodies_known == 40
        assert result.estimated_value == 605861
        assert result.estimated_value_mapped == 2213988
        assert result.source == "edsm"
        assert len(result.valuable_bodies) == 1

    def test_unknown_system(self, requests_mock: rm.Mocker) -> None:
        """An unknown system returns found=False."""
        requests_mock.get(
            "https://www.edsm.net/api-system-v1/bodies",
            json={},
        )

        result = query_edsm("Totally Fake System 12345")

        assert result.found is False
        assert result.source == "edsm"

    def test_network_error(self, requests_mock: rm.Mocker) -> None:
        """A network timeout returns found=False with an error string."""
        requests_mock.get(
            "https://www.edsm.net/api-system-v1/bodies",
            exc=requests.exceptions.ConnectTimeout,
        )

        result = query_edsm("Sol", timeout=1.0)

        assert result.found is False
        assert result.error is not None

    def test_bodies_found_but_value_fails(self, requests_mock: rm.Mocker) -> None:
        """Even if the value endpoint fails, bodies data is kept."""
        requests_mock.get(
            "https://www.edsm.net/api-system-v1/bodies",
            json={
                "name": "Sol",
                "bodyCount": 5,
                "bodies": [{"name": f"Body {i}"} for i in range(5)],
            },
        )
        requests_mock.get(
            "https://www.edsm.net/api-system-v1/estimated-value",
            status_code=500,
        )

        result = query_edsm("Sol")

        assert result.found is True
        assert result.body_count == 5
        assert result.estimated_value == 0

    def test_malformed_json(self, requests_mock: rm.Mocker) -> None:
        """Malformed JSON returns found=False."""
        requests_mock.get(
            "https://www.edsm.net/api-system-v1/bodies",
            text="not json at all",
        )

        result = query_edsm("Sol")

        assert result.found is False


# ── Spansh Tests ──────────────────────────────────────────────────────


class TestQuerySpansh:
    """Test suite for the query_spansh function."""

    SYSTEM_ADDRESS = 10477373803  # Sol

    def test_found_system(self, requests_mock: rm.Mocker) -> None:
        """A known system returns body and value data."""
        requests_mock.get(
            f"https://spansh.co.uk/api/system/{self.SYSTEM_ADDRESS}",
            json={
                "record": {
                    "name": "Sol",
                    "body_count": 40,
                    "bodies": [{"name": f"Body {i}"} for i in range(40)],
                    "estimated_scan_value": 605861,
                    "estimated_mapping_value": 2213988,
                },
            },
        )

        result = query_spansh(self.SYSTEM_ADDRESS)

        assert result.found is True
        assert result.name == "Sol"
        assert result.body_count == 40
        assert result.bodies_known == 40
        assert result.estimated_value == 605861
        assert result.estimated_value_mapped == 2213988
        assert result.source == "spansh"

    def test_unknown_system(self, requests_mock: rm.Mocker) -> None:
        """An unknown system id64 returns found=False."""
        requests_mock.get(
            f"https://spansh.co.uk/api/system/{self.SYSTEM_ADDRESS}",
            status_code=404,
        )

        result = query_spansh(self.SYSTEM_ADDRESS)

        assert result.found is False

    def test_network_error(self, requests_mock: rm.Mocker) -> None:
        """A network error returns found=False with error."""
        requests_mock.get(
            f"https://spansh.co.uk/api/system/{self.SYSTEM_ADDRESS}",
            exc=requests.exceptions.ConnectionError,
        )

        result = query_spansh(self.SYSTEM_ADDRESS)

        assert result.found is False
        assert result.error is not None

    def test_missing_record_key(self, requests_mock: rm.Mocker) -> None:
        """JSON without 'record' key returns found=False."""
        requests_mock.get(
            f"https://spansh.co.uk/api/system/{self.SYSTEM_ADDRESS}",
            json={"error": "not found"},
        )

        result = query_spansh(self.SYSTEM_ADDRESS)

        assert result.found is False

    def test_no_bodies_array(self, requests_mock: rm.Mocker) -> None:
        """Record exists but without a bodies array still sets body_count."""
        requests_mock.get(
            f"https://spansh.co.uk/api/system/{self.SYSTEM_ADDRESS}",
            json={
                "record": {
                    "name": "Sol",
                    "body_count": 40,
                    "estimated_scan_value": 100,
                },
            },
        )

        result = query_spansh(self.SYSTEM_ADDRESS)

        assert result.found is True
        assert result.body_count == 40
        assert result.bodies_known == 0
