import asyncio
import threading
import time
import logging
from fastapi import FastAPI
import uvicorn
import aio_pika
import json
from sqlalchemy import select, update
from app.config import settings
from app.db import AsyncSessionLocal
from app.models import Product

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Inventory Service")

# (Opcional) Endpoint para consultar stock
@app.get("/stock")
async def get_stock():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Product))
        products = result.scalars().all()
        return {p.sku: p.stock for p in products}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "inventory"}

async def process_order(message: aio_pika.IncomingMessage):
    async with message.process():
        order_data = json.loads(message.body.decode())
        order_id = order_data['order_id']
        items = order_data['items']
        logger.info(f"Procesando inventario para orden {order_id}")

        async with AsyncSessionLocal() as session:
            async with session.begin():
                for item in items:
                    sku = item['sku']
                    qty = item['qty']
                    # Obtener producto con lock
                    result = await session.execute(
                        select(Product).where(Product.sku == sku).with_for_update()
                    )
                    product = result.scalar_one_or_none()
                    if product is None:
                        logger.error(f"SKU {sku} no encontrado")
                        # Podrías publicar un evento de error aquí
                        continue
                    if product.stock < qty:
                        logger.error(f"Stock insuficiente para SKU {sku}: disponible {product.stock}, requerido {qty}")
                        continue
                    product.stock -= qty
                    logger.info(f"SKU {sku}: nuevo stock = {product.stock}")

        # Aquí podrías publicar un evento de procesamiento exitoso (opcional)
        logger.info(f"Inventario actualizado para orden {order_id}")

async def rabbitmq_consumer():
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
        except (aio_pika.exceptions.AMQPConnectionError, ConnectionError) as e:
            logger.error(f"Error de conexión: {e}. Reintentando en 5 segundos...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.exception(f"Error inesperado: {e}")
            await asyncio.sleep(5)

def start_consumer():
    asyncio.run(rabbitmq_consumer())

@app.on_event("startup")
async def startup_event():
    # Iniciar consumidor en segundo plano
    thread = threading.Thread(target=start_consumer, daemon=True)
    thread.start()
    logger.info("Consumidor de RabbitMQ iniciado")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)