from sqlalchemy import Column, String, DateTime, func
from app.db import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True)
    order_id = Column(String(36), nullable=False)
    recipient = Column(String(255), nullable=False)
    status = Column(String(20))   # 'success' o 'failure'
    reason = Column(String(255), nullable=True)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())