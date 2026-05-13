"""Fake Emitters test coverage."""

from __future__ import annotations


class Collector:
    def __init__(self) -> None:
        """Handle the value."""
        # Keep the main step clear.
        self.items: list[dict] = []

    def __call__(self, payload: dict) -> None:
        """Handle the value."""
        # Keep the main step clear.
        self.items.append(payload)
