import asyncio
import logging
from fastapi import FastAPI
import uvicorn
import aio_pika
import json
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from app.config import settings
from app.models import Base, Product
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de base de datos local
engine = create_async_engine(settings.database_url, echo=True, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

app = FastAPI(title="Inventory Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En desarrollo puedes permitir todos los orígenes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/stock")
async def get_stock():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Product))
        products = result.scalars().all()
        # Devolver una lista con sku, nombre y stock
        return [
            {"sku": p.sku, "name": p.name, "stock": p.stock}
            for p in products
        ]

@app.get("/health")
async def health():
    return {"status": "ok"}

async def process_order(message: aio_pika.IncomingMessage):
    async with message.process():
        order_data = json.loads(message.body.decode())
        order_id = order_data['order_id']
        items = order_data['items']
        logger.info(f"Procesando orden {order_id}")
        async with AsyncSessionLocal() as session:
            async with session.begin():
                for item in items:
                    sku = item['sku']
                    qty = item['qty']
                    result = await session.execute(select(Product).where(Product.sku == sku).with_for_update())
                    product = result.scalar_one_or_none()
                    if product and product.stock >= qty:
                        product.stock -= qty
                        logger.info(f"SKU {sku}: stock restante {product.stock}")
                    else:
                        logger.error(f"Stock insuficiente para {sku}")
        logger.info(f"Orden {order_id} procesada")

async def consumer():
    while True:
        try:
            connection = await aio_pika.connect_robust(settings.rabbitmq_url)
            async with connection:
                channel = await connection.channel()
                exchange = await channel.declare_exchange("orders", aio_pika.ExchangeType.TOPIC, durable=True)
                queue = await channel.declare_queue("inventory.order.created", durable=True)
                await queue.bind(exchange, routing_key="order.created")
                await queue.consume(process_order)
                logger.info("Esperando mensajes...")
                await asyncio.Future()
        except Exception as e:
            logger.error(f"Error: {e}. Reintentando en 5s")
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)  # Crear tablas si no existen
    asyncio.create_task(consumer())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)