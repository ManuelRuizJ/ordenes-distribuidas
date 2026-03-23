from typing import Optional   # <-- añade esta línea
from pydantic import BaseModel
from typing import List

class Item(BaseModel):
    sku: str
    qty: int

class InternalOrder(BaseModel):
    order_id: str
    customer: str
    items: List[Item]

class OrderStatusResponse(BaseModel):
    order_id: str
    status: str
    last_update: Optional[str] = None
    reason: Optional[str] = None