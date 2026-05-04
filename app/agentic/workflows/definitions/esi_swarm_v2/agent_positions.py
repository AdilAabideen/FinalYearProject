from __future__ import annotations

from typing import Dict, TypedDict


class Point(TypedDict):
    x: int
    y: int


AGENT_POSITIONS_MAP: Dict[str, Point] = {
    "esi1_agent": {"x": 13, "y": 40},
    "esi2_agent": {"x": 35, "y": 70},
    "esi345_agent": {"x": 60, "y": 65},
    "vitals_agent": {"x": 89, "y": 51},
    "start_v1": {"x": 10, "y": 5},
    "start_v2": {"x": 92, "y": 5},
    "end_v1": {"x": 13, "y": 88},
    "end_v2": {"x": 35, "y": 88},
    "end_v3": {"x": 60, "y": 88},
}
