from sqlalchemy import Column, String, Integer, CheckConstraint, JSON, DateTime, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Order(Base):
    __tablename__ = "orders"
    order_id = Column(String(36), primary_key=True, index=True)
    customer = Column(String(255), nullable=False)
    items = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("stock >= 0", name="ck_products_stock_non_negative"),
    )
    sku = Column(String(40), primary_key=True)
    name = Column(String(100), nullable=False)
    stock = Column(Integer, nullable=False, default=0)
