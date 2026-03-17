import asyncio
import threading
from fastapi import FastAPI
import uvicorn
import aio_pika
import json
import logging
from app.config import settings
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simulación de almacenamiento de métricas
orders_processed = []
total_orders = 0

app = FastAPI(title="Analytics Service")

@app.get("/metrics")
async def get_metrics():
    return {
        "total_orders": total_orders,
        "orders": orders_processed[-10:]  # últimas 10 órdenes
    }

@app.get("/health")
async def health():
    return {"status": "ok", "service": "analytics"}

async def process_order(message: aio_pika.IncomingMessage):
    global total_orders
    async with message.process():
        order_data = json.loads(message.body.decode())
        order_id = order_data['order_id']
        total_orders += 1
        orders_processed.append({
            "order_id": order_id,
            "timestamp": datetime.now().isoformat(),
            "customer": order_data['customer']
        })
        logger.info(f"Métrica registrada para orden {order_id}. Total: {total_orders}")

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
    uvicorn.run(app, host="0.0.0.0", port=8003)