from __future__ import annotations

from typing import Dict, TypedDict


class Point(TypedDict):
    x: int
    y: int


AGENT_POSITIONS_MAP: Dict[str, Point] = {
    "esi1_agent": {"x": 10, "y": 47},
    "esi2_agent": {"x": 30, "y": 77},
    "esi345_agent": {"x": 60, "y": 65},
    "vitals_agent": {"x": 92, "y": 71},
    "doctor_agent": {"x": 75, "y": 19},
    "start_v1": {"x": 10, "y": 5},
    "start_v2": {"x": 92, "y": 5},
    "end": {"x": 75, "y": 88},
}
