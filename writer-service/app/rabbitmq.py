import json
import aio_pika
from app.config import settings

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