import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

async def seed_products(session: AsyncSession):
    try:
        # Verificar si la tabla existe
        result = await session.execute(text("SELECT COUNT(*) FROM products"))
        count = result.scalar_one()
        if count == 0:
            await session.execute(text("""
                INSERT INTO products (sku, name, stock) VALUES
                ('001-E', 'Computer', 100),
                ('002-T', 'Fax Machine', 200),
                ('003-E', 'Laptop', 300),
                ('004-P', 'Printer', 400),
                ('005-T', 'Smartphone', 500),
                ('006-M', 'Tablet', 600),
                ('007-A', 'Monitor', 700),
                ('008-P', 'Keyboard', 800),
                ('009-P', 'Mouse', 900),
                ('010-A', 'Headphones', 1000),
                ('011-P', 'Webcam', 1100),
                ('012-S', 'External Hard Drive', 1200),
                ('013-S', 'USB Flash Drive', 1300),
                ('014-T', 'Router', 1400),
                ('015-T', 'Switch', 1500),
                ('016-T', 'Server', 1600),
                ('017-E', 'Workstation', 1700),
                ('018-A', 'Projector', 1800),
                ('019-P', 'Scanner', 1900),
                ('020-P', 'Copier', 2000),
                ('021-W', 'Smartwatch', 2100),
                ('022-W', 'Fitness Tracker', 2200),
                ('023-G', 'VR Headset', 2300),
                ('024-G', 'Gaming Console', 2400),
                ('025-A', 'Smart TV', 2500)
            """))
            await session.commit()
            logger.info("Productos iniciales cargados.")
        else:
            logger.info("Productos ya existen, se omite seed.")
    except Exception as e:
        logger.error(f"Error en seeder: {e}", exc_info=True)
        # No relanzamos la excepción para que el servicio pueda seguir iniciando