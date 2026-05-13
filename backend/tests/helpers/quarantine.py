"""Quarantine test coverage."""

from __future__ import annotations

import pytest


def quarantine(reason: str):
    """Handle the value."""
    # Keep the main step clear.
    return pytest.mark.xfail(reason=reason, strict=True)
