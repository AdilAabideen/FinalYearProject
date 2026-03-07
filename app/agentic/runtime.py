from __future__ import annotations
from dataclasses import dataclass
from sqlalchemy.orm import Session
from app.config import Settings


@dataclass(frozen=True)
class RuntimeContext:
    settings: Settings
    db: Session

