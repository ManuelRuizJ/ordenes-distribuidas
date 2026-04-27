from sqlalchemy import Column, String, Integer, CheckConstraint, DateTime, func
from app.db import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("stock >= 0", name="ck_products_stock_non_negative"),
    )
    sku = Column(String(40), primary_key=True)
    name = Column(String(100), nullable=False)
    stock = Column(Integer, nullable=False, default=0)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(String(36), primary_key=True)
    order_id = Column(String(36), nullable=False)
    recipient = Column(String(255), nullable=False)
    status = Column(String(20))
    reason = Column(String(255), nullable=True)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
