from __future__ import annotations


class Collector:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def __call__(self, payload: dict) -> None:
        self.items.append(payload)
