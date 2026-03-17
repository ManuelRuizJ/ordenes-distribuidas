import asyncio
import aio_pika
import json
import logging
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def process_order(message: aio_pika.IncomingMessage):
    async with message.process():
        order_data = json.loads(message.body.decode())
        # Personaliza este mensaje según el servicio
        logger.info(f"Descontando stock para orden: {order_data['order_id']}")
        # Aquí iría la lógica real (inventario, métrica, notificación)

async def main():
    # Bucle infinito con reintentos
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
                await asyncio.Future()  # Mantiene vivo
        except (aio_pika.exceptions.AMQPConnectionError, ConnectionError) as e:
            logger.error(f"Error de conexión: {e}. Reintentando en 5 segundos...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.exception(f"Error inesperado: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())