from pydantic import BaseModel, Field
from typing import List, Optional
import uuid


class Item(BaseModel):
    sku: str
    qty: int


class OrderRequest(BaseModel):
    items: List[Item]


class OrderResponse(BaseModel):
    order_id: str
    status: str


class OrderStatusResponse(BaseModel):
    order_id: str
    status: str
    reason: Optional[str] = None


def generate_order_id() -> str:
    return str(uuid.uuid4())