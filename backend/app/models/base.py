"""Base ORM models."""

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer
from datetime import datetime
from typing import Optional

class Base(DeclarativeBase):
    """
    Base class for all models using SQLAlchemy 2.0 style.
    Provides common fields like id, created_at, updated_at.
    """
    pass

class TimestampMixin:
    """Mixin to add timestamp fields to models"""
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )