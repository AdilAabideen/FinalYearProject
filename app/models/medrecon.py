from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Medrecon(Base):
    """
    Medrecon table (MIMIC-IV ED medrecon.csv).
    """

    __tablename__ = "medrecon"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(Integer, nullable=False)
    stay_id: Mapped[int] = mapped_column(Integer, nullable=False)
    charttime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    gsn: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ndc: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    etc_rn: Mapped[int] = mapped_column(Integer, nullable=False)
    etccode: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    etcdescription: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
