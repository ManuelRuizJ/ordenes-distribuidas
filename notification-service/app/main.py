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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración SMTP desde variables de entorno
SMTP_HOST = settings.smtp_host
SMTP_PORT = settings.smtp_port
SMTP_USER = settings.smtp_user
SMTP_PASSWORD = settings.smtp_password
EMAIL_FROM = settings.email_from
EMAIL_TO = settings.email_to

app = FastAPI(title="Notification Service")

# Historial de notificaciones (opcional)
notifications_sent = []

@app.get("/notifications")
async def get_notifications():
    return {"total": len(notifications_sent), "recent": notifications_sent[-10:]}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "notification"}

async def send_email(order_data: dict):
    """Envía un correo con los detalles de la orden."""
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO]):
        logger.warning("Configuración de correo incompleta, no se enviará email")
        return
    message = EmailMessage()
    message["From"] = EMAIL_FROM
    message["To"] = EMAIL_TO
    message["Subject"] = f"Nueva orden recibida: {order_data['order_id']}"
    body = f"""
    Se ha creado una nueva orden:
    ID: {order_data['order_id']}
    Cliente: {order_data['customer']}
    Artículos:
    {', '.join([f"{item['sku']} (x{item['qty']})" for item in order_data['items']])}
    """
    message.set_content(body)
    try:
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            use_tls=False,
            start_tls=True
        )
        logger.info(f"Correo enviado para orden {order_data['order_id']}")
        # Guardar en historial
        notifications_sent.append({
            "order_id": order_data['order_id'],
            "to": EMAIL_TO,
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