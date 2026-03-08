from sqlalchemy import Column, String, JSON, DateTime, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Order(Base):
    __tablename__ = "orders"

    order_id = Column(String(36), primary_key=True, index=True)
    customer = Column(String(255), nullable=False)
    items = Column(JSON, nullable=False)  # lista de items como JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())