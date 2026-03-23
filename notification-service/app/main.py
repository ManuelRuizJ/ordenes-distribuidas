import asyncio
import threading
from fastapi import FastAPI
import uvicorn
import aio_pika
import json
import logging
import aiosmtplib
from email.message import EmailMessage
from app.config import settings
from app.db import AsyncSessionLocal_main
from sqlalchemy import select
from app.models import Product

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Notification Service")

# Historial de notificaciones (opcional)
notifications_sent = []

@app.get("/notifications")
async def get_notifications():
    return {"total": len(notifications_sent), "recent": notifications_sent[-10:]}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "notification"}

async def get_product_names(skus: list[str]) -> dict[str, str]:
    if not skus:
        return {}
    async with AsyncSessionLocal_main() as session:
        result = await session.execute(
            select(Product.sku, Product.name).where(Product.sku.in_(skus))
        )
        rows = result.all()
    return {sku: name for sku, name in rows}

async def send_email(order_data: dict):
    """Envía un correo con los detalles de la orden."""
    if not all([settings.smtp_host, settings.smtp_user, settings.smtp_password, settings.email_from, settings.email_to]):
        logger.warning("Configuración de correo incompleta, no se enviará email")
        return

    skus = [item['sku'] for item in order_data['items']]
    product_names = await get_product_names(skus)

    items_html = ""
    for item in order_data['items']:
        sku = item['sku']
        qty = item['qty']
        name = product_names.get(sku, sku)
        items_html += f"<li>{name} (SKU: {sku}) - Cantidad: {qty}</li>"

    html_body = f"""
    <html>
        <body>
            <h2>Nueva orden recibida</h2>
            <p><strong>ID de orden:</strong> {order_data['order_id']}</p>
            <p><strong>Cliente:</strong> {order_data['customer']}</p>
            <p><strong>Artículos:</strong></p>
            <ul>
                {items_html}
            </ul>
            <p>Gracias por su compra.</p>
        </body>
    </html>
    """

    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = settings.email_to
    message["Subject"] = f"Nueva orden: {order_data['order_id']}"
    items_text = ', '.join([f"{item['sku']} (x{item['qty']})" for item in order_data['items']])
    message.set_content(f"ID: {order_data['order_id']}\nCliente: {order_data['customer']}\nArtículos: {items_text}")
    message.add_alternative(html_body, subtype="html")

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=False,
            start_tls=True
        )
        logger.info(f"Correo enviado para orden {order_data['order_id']}")
        notifications_sent.append({
            "order_id": order_data['order_id'],
            "to": settings.email_to,
            "timestamp": asyncio.get_event_loop().time()
        })
    except Exception as e:
        logger.error(f"Error enviando correo: {e}")

async def process_order(message: aio_pika.IncomingMessage):
    async with message.process():
        order_data = json.loads(message.body.decode())
        logger.info(f"Procesando notificación para orden: {order_data['order_id']}")
        await send_email(order_data)

async def rabbitmq_consumer():
    while True:
        try:
            connection = await aio_pika.connect_robust(settings.rabbitmq_url)
            async with connection:
                channel = await connection.channel()
                exchange = await channel.declare_exchange("orders", aio_pika.ExchangeType.TOPIC, durable=True)
                queue = await channel.declare_queue("notification.order.created", durable=True)
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
    thread = threading.Thread(target=start_consumer, daemon=True)
    thread.start()
    logger.info("Consumidor de RabbitMQ iniciado en segundo plano")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)