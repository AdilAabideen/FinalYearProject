from __future__ import annotations

import pytest


def quarantine(reason: str):
    return pytest.mark.xfail(reason=reason, strict=True)
