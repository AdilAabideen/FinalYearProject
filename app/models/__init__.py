from app.models.base import Base, TimestampMixin
from app.models.medercon import Medicine

# Import all models here so Alembic can detect them
__all__ = ["Base", "TimestampMixin", "Medicine"]
