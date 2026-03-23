import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

async def seed_products(session: AsyncSession):
    try:
        # Verificar si ya hay productos
        result = await session.execute(text("SELECT COUNT(*) FROM products"))
        count = result.scalar_one()
        if count == 0:
            await session.execute(text("""
                INSERT INTO products (sku, name, stock) VALUES
                ('LAP001', 'Laptop', 10),
                ('SMR002', 'Smartphone', 15),
                ('MNT003', 'Monitor', 8),
                ('TEC004', 'Teclado', 20),
                ('MOU005', 'Mouse', 25),
                ('AUD006', 'Auriculares', 12),
                ('TAB007', 'Tablet', 6),
                ('IMP008', 'Impresora', 5)
            """))
            await session.commit()
            logger.info("✅ Productos en español cargados correctamente.")
        else:
            logger.info("ℹ️ Los productos ya existen, no se insertaron de nuevo.")
    except Exception as e:
        logger.error(f"❌ Error en seeder: {e}", exc_info=True)