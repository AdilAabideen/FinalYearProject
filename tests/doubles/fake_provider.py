from __future__ import annotations

from collections import deque
from typing import Any


class FakeBoundModel:
    def __init__(self, scripted: list[Any]) -> None:
        self._scripted = deque(scripted)

    async def ainvoke(self, _messages):
        if not self._scripted:
            raise AssertionError("FakeBoundModel exhausted")
        item = self._scripted.popleft()
        if isinstance(item, Exception):
            raise item
        return item


class FakeChatModel:
    def __init__(self, scripted: list[Any]) -> None:
        self._scripted = deque(scripted)
        self.bound_tools = None
        self.bound_tool_choice = None

    def bind_tools(self, tools, tool_choice="any"):
        self.bound_tools = list(tools)
        self.bound_tool_choice = tool_choice
        return self

    async def ainvoke(self, _messages):
        if not self._scripted:
            raise AssertionError("FakeChatModel exhausted")
        item = self._scripted.popleft()
        if isinstance(item, Exception):
            raise item
        return item
