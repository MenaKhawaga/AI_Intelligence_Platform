from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base_class import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentActivity(Base):
    __tablename__ = "agent_activities"

    id: Mapped[int] = mapped_column(Integer,primary_key=True,index=True)
    user_id: Mapped[int] = mapped_column(Integer,ForeignKey("users.id"),nullable=False)
    query: Mapped[str] = mapped_column(Text,nullable=False)
    tools_used: Mapped[list] = mapped_column(JSON,default=list,nullable=False)
    success: Mapped[bool] = mapped_column(default=True,nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=_utcnow,nullable=False)