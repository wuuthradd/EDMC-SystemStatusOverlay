"""Package marker for EDMC-SystemStatusOverlay plugin."""
from __future__ import annotations

try:
    from .version import __version__  # type: ignore  # noqa: F401
except ImportError:  # pragma: no cover - fallback for direct execution
    from version import __version__  # type: ignore  # noqa: F401

__all__ = ["__version__"]
