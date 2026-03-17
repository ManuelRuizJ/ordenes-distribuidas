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

# Historial de notificaciones
notifications_sent = []

app = FastAPI(title="Notification Service")

@app.get("/notifications")
async def get_notifications():
    return {
        "total": len(notifications_sent),
        "recent": notifications_sent[-10:]
    }

@app.get("/health")
async def health():
    return {"status": "ok", "service": "notification"}

async def process_order(message: aio_pika.IncomingMessage):
    async with message.process():
        order_data = json.loads(message.body.decode())
        order_id = order_data['order_id']
        customer = order_data['customer']
        
        # Simular envío de email
        notification = {
            "order_id": order_id,
            "customer": customer,
            "email": f"{customer.lower().replace(' ', '.')}@example.com",
            "message": f"Tu orden {order_id} ha sido recibida y está en proceso.",
            "timestamp": datetime.now().isoformat()
        }
        notifications_sent.append(notification)
        logger.info(f"Notificación enviada a {customer} para orden {order_id}")

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
    uvicorn.run(app, host="0.0.0.0", port=8004)