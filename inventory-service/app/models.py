from sqlalchemy import Column, String, Integer, CheckConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Product(Base):
    __tablename__ = "products"
    __table_args__ = (CheckConstraint("stock >= 0", name="ck_products_stock_non_negative"),)
    sku = Column(String(40), primary_key=True)
    name = Column(String(100), nullable=False)
    stock = Column(Integer, nullable=False, default=0)