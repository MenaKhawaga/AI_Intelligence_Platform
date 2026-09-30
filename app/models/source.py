from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base_class import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer,primary_key=True,index=True)
    name: Mapped[str] = mapped_column(String(150),nullable=False,unique=True)
    source_type: Mapped[str] = mapped_column(String(50),nullable=False)
    url: Mapped[str] = mapped_column(String(1000),nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean,default=True,nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=_utcnow,nullable=False)