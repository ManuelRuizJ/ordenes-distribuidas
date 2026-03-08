from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Order
from app.schemas import InternalOrder
import logging

logger = logging.getLogger(__name__)


async def upsert_order(db: AsyncSession, order_data: InternalOrder) -> bool:
    """
    Inserta la orden si no existe. Retorna True si se insertó, False si ya existía.
    """
    # Verificar existencia por order_id
    stmt = select(Order).where(Order.order_id == order_data.order_id)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        logger.info("Orden %s ya existe, no se inserta", order_data.order_id)
        return False  # ya existía

    # Crear nueva orden
    new_order = Order(
        order_id=order_data.order_id,
        customer=order_data.customer,
        items=[item.dict() for item in order_data.items]
    )
    db.add(new_order)
    await db.commit()
    logger.info("Orden %s insertada en Postgres", order_data.order_id)
    return True