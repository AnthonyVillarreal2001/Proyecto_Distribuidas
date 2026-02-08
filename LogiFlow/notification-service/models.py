from shared.database import Base
from sqlalchemy import Column, Integer, String, JSON, DateTime, func
import sys

sys.path.append('..')


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False)
    routing_key = Column(String, nullable=True)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
