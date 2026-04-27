from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Order, Product
from app.schemas import InternalOrder
import logging

logger = logging.getLogger(__name__)


async def upsert_order(db: AsyncSession, order_data: InternalOrder) -> bool:
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
        items=[item.dict() for item in order_data.items],
    )
    db.add(new_order)
    await db.commit()
    logger.info("Orden %s insertada en Postgres", order_data.order_id)
    return True


async def validate_and_lock_stock(
    session: AsyncSession, items: list[dict]
) -> tuple[bool, list[str]]:
    logger.info(f"=== INICIANDO validación de stock para {len(items)} items ===")
    errors = []
    for item in items:
        sku = item["sku"]
        qty = item["qty"]
        logger.info(f"Validando SKU {sku} cantidad {qty}")
        stmt = select(Product).where(Product.sku == sku).with_for_update()
        result = await session.execute(stmt)
        product = result.scalar_one_or_none()
        if product is None:
            logger.warning(f"SKU {sku} NO EXISTENTE")
            errors.append(f"SKU '{sku}' no existente")
        elif product.stock < qty:
            logger.warning(f"Stock insuficiente para {sku}: {product.stock} < {qty}")
            errors.append(
                f"SKU '{sku}' stock insuficiente (disponible: {product.stock}, solicitado: {qty})"
            )
        else:
            logger.info(f"SKU {sku} OK, stock actual: {product.stock}")
    logger.info(
        f"Validación completada. Stock OK? {len(errors) == 0}. Errores: {errors}"
    )
    return len(errors) == 0, errors
