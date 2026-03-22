"""Pure data module for querying EDSM and Spansh APIs."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger("EDMC-SystemStatusOverlay.api")

_EDSM_BODIES_URL = "https://www.edsm.net/api-system-v1/bodies"
_EDSM_VALUE_URL = "https://www.edsm.net/api-system-v1/estimated-value"
_SPANSH_SYSTEM_URL = "https://spansh.co.uk/api/system"

_DEFAULT_TIMEOUT = 10.0
from . import __version__ as _version

_USER_AGENT = f"EDMC-SystemStatusOverlay/{_version}"
_HEADERS = {"User-Agent": _USER_AGENT}


@dataclass
class SystemInfo:
    """Result of a system lookup against an external database."""

    found: bool
    name: str = ""
    body_count: int = 0
    bodies_known: int = 0
    estimated_value: int = 0
    estimated_value_mapped: int = 0
    source: str = ""
    valuable_bodies: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None


def query_edsm(system_name: str, *, timeout: float = _DEFAULT_TIMEOUT) -> SystemInfo:
    """Query EDSM for body and value data.

    Returns SystemInfo with ``found=False`` on any error or when the system is
    not in the EDSM database.
    """
    headers = _HEADERS
    info = SystemInfo(found=False, name=system_name, source="edsm")

    # --- Bodies endpoint ---
    try:
        resp = requests.get(
            _EDSM_BODIES_URL,
            params={"systemName": system_name},
            headers=headers,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.debug("EDSM bodies request failed for %s: %s", system_name, exc)
        info.error = str(exc)
        return info
    except (ValueError, KeyError) as exc:
        logger.debug("EDSM bodies JSON error for %s: %s", system_name, exc)
        info.error = str(exc)
        return info

    # EDSM returns an empty dict or a dict without 'bodies' if system is unknown.
    bodies = data.get("bodies")
    if not isinstance(bodies, list):
        return info

    info.found = True
    info.bodies_known = len(bodies)
    # EDSM doesn't always return bodyCount; fall back to len(bodies).
    info.body_count = data.get("bodyCount", len(bodies)) or len(bodies)

    # --- Estimated value endpoint ---
    try:
        resp = requests.get(
            _EDSM_VALUE_URL,
            params={"systemName": system_name},
            headers=headers,
            timeout=timeout,
        )
        resp.raise_for_status()
        val_data = resp.json()
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.debug("EDSM value request failed for %s: %s", system_name, exc)
        # We still have body data, so keep found=True.
        return info

    info.estimated_value = _safe_int(val_data.get("estimatedValue"))
    info.estimated_value_mapped = _safe_int(val_data.get("estimatedValueMapped"))

    valuable = val_data.get("valuableBodies")
    if isinstance(valuable, list):
        info.valuable_bodies = valuable

    return info


def query_spansh(system_address: int, *, timeout: float = _DEFAULT_TIMEOUT) -> SystemInfo:
    """Query Spansh for system data using the 64-bit system address (id64).

    Returns SystemInfo with ``found=False`` on any error or when the system is
    not in the Spansh database.
    """
    headers = _HEADERS
    info = SystemInfo(found=False, source="spansh")

    url = f"{_SPANSH_SYSTEM_URL}/{system_address}"
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        # Spansh returns 404 for unknown systems — treat as "not found", not error.
        if resp.status_code == 404:
            return info
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.debug("Spansh request failed for id64=%d: %s", system_address, exc)
        info.error = str(exc)
        return info
    except (ValueError, KeyError) as exc:
        logger.debug("Spansh JSON error for id64=%d: %s", system_address, exc)
        info.error = str(exc)
        return info

    record = data.get("record")
    if not isinstance(record, dict):
        return info

    info.found = True
    info.name = record.get("name", "")
    info.body_count = _safe_int(record.get("body_count"))

    bodies = record.get("bodies")
    if isinstance(bodies, list):
        info.bodies_known = len(bodies)

    info.estimated_value = _safe_int(record.get("estimated_scan_value"))
    info.estimated_value_mapped = _safe_int(record.get("estimated_mapping_value"))

    return info


def _safe_int(value: Any) -> int:
    """Coerce a value to int, returning 0 on failure."""
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
