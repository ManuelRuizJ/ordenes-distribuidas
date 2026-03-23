import asyncio
import json
import logging
from collections import Counter
from fastapi import FastAPI
import uvicorn
import aio_pika
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Analytics Service")

# Estadísticas en memoria
total_orders = 0
product_counter = Counter()      # {sku: cantidad_total_vendida}
customer_counter = Counter()     # {customer: número_de_órdenes}

@app.get("/analytics")
async def get_analytics():
    """Devuelve métricas agregadas"""
    top_products = product_counter.most_common(5)
    top_customer = customer_counter.most_common(1)
    return {
        "total_orders": total_orders,
        "top_products": [{"sku": sku, "total_qty": qty} for sku, qty in top_products],
        "top_customer": {"name": top_customer[0][0], "orders": top_customer[0][1]} if top_customer else None
    }

@app.get("/health")
async def health():
    return {"status": "ok"}

async def process_order(message: aio_pika.IncomingMessage):
    global total_orders, product_counter, customer_counter
    async with message.process():
        order_data = json.loads(message.body.decode())
        logger.info(f"Procesando analytics para orden {order_data['order_id']}")
        logger.info(f"Cliente recibido: '{order_data['customer']}'")  # <-- NUEVO LOG
        
        # Actualizar métricas
        total_orders += 1
        customer_counter[order_data['customer']] += 1
        for item in order_data['items']:
            product_counter[item['sku']] += item['qty']
        
        logger.info(f"Total órdenes: {total_orders}")
        logger.info(f"Contador de clientes: {dict(customer_counter)}")  # <-- NUEVO LOG

async def rabbitmq_consumer():
    while True:
        try:
            connection = await aio_pika.connect_robust(settings.rabbitmq_url)
            async with connection:
                channel = await connection.channel()
                exchange = await channel.declare_exchange("orders", aio_pika.ExchangeType.TOPIC, durable=True)
                queue = await channel.declare_queue("analytics.order.created", durable=True)
                await queue.bind(exchange, routing_key="order.created")
                await queue.consume(process_order)
                logger.info("Esperando mensajes...")
                await asyncio.Future()
        except Exception as e:
            logger.error(f"Error: {e}. Reintentando en 5s")
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup():
    asyncio.create_task(rabbitmq_consumer())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)