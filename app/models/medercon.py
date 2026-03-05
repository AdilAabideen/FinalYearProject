from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer
from app.models.base import Base, TimestampMixin

class Medicine(Base, TimestampMixin):
    """
    Medicine model using SQLAlchemy 2.0 style with type hints.
    """
    __tablename__ = "medercon"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    
    def __repr__(self) -> str:
        return f"<Medicine(id={self.id}, name={self.name})>"