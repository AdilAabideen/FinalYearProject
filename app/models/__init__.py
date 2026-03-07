from app.models.base import Base, TimestampMixin
from app.models.medrecon import Medrecon

# Import all models here so Alembic can detect them
__all__ = ["Base", "TimestampMixin", "Medrecon"]
