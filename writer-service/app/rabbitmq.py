from asyncio.log import logger
import json
import aio_pika
from app.config import settings
import time

async def get_rabbitmq_connection():
    return await aio_pika.connect_robust(settings.rabbitmq_url)

async def publish_order_created(order_data: dict):
    connection = await get_rabbitmq_connection()
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange("orders", aio_pika.ExchangeType.TOPIC, durable=True)
        message = aio_pika.Message(
            body=json.dumps(order_data).encode(),
            content_type="application/json"
        )
        await exchange.publish(message, routing_key="order.created")

async def publish_order_error(order_data: dict, reason: str):
    connection = await get_rabbitmq_connection()
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange("orders", aio_pika.ExchangeType.TOPIC, durable=True)
        payload = {
            "order_id": order_data['order_id'],
            "customer": order_data['customer'],
            "items": order_data['items'],
            "reason": reason,
            "timestamp": time.time()
        }
        message = aio_pika.Message(
            body=json.dumps(payload).encode(),
            content_type="application/json"
        )
        await exchange.publish(message, routing_key="order.error")
