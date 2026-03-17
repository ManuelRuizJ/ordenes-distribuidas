import asyncio
import threading
from fastapi import FastAPI
import uvicorn
import aio_pika
import json
import logging
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simulación de stock en memoria
stock = {
    "A1": 100,
    "B2": 50,
    "C3": 75
}

app = FastAPI(title="Inventory Service")

@app.get("/stock")
async def get_stock():
    return stock

@app.get("/health")
async def health():
    return {"status": "ok", "service": "inventory"}

# --- Consumidor de RabbitMQ ---
async def process_order(message: aio_pika.IncomingMessage):
    async with message.process():
        order_data = json.loads(message.body.decode())
        order_id = order_data['order_id']
        items = order_data['items']
        logger.info(f"Procesando orden {order_id} para descontar stock")
        
        for item in items:
            sku = item['sku']
            qty = item['qty']
            if sku in stock and stock[sku] >= qty:
                stock[sku] -= qty
                logger.info(f"  ✅ SKU {sku}: nuevo stock = {stock[sku]}")
            else:
                logger.warning(f"  ❌ SKU {sku}: stock insuficiente (disponible: {stock.get(sku, 0)})")

async def rabbitmq_consumer():
    while True:
        try:
            connection = await aio_pika.connect_robust(settings.rabbitmq_url)
            async with connection:
                channel = await connection.channel()
                exchange = await channel.declare_exchange("orders", aio_pika.ExchangeType.FANOUT)
                queue = await channel.declare_queue(exclusive=True)
                await queue.bind(exchange)
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
    thread = threading.Thread(target=start_consumer, daemon=True)
    thread.start()
    logger.info("Consumidor de RabbitMQ iniciado en segundo plano")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)