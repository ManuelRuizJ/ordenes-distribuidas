import asyncio
import threading
import uuid
import logging
from fastapi import FastAPI
import uvicorn
import aio_pika
import json
import aiosmtplib
from email.message import EmailMessage
from app.config import settings
from app.db import (
    AsyncSessionLocal_main,
    AsyncSessionLocal_notifications,
    engine_notifications,
    Base,
)
from sqlalchemy import select
from app.models import Product, Notification

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Notification Service")

# Historial en memoria (opcional)
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


def generate_html(
    title: str, customer: str, items: list, is_error: bool = False, reason: str = None
) -> str:
    header_color = "#e53935" if is_error else "#2e7d32"
    bg_color = "#f8f9fa"

    items_html = ""
    if items:
        items_html = """
        <div style="margin-top: 25px;">
            <h3 style="color: #333; font-size: 18px; border-bottom: 2px solid #eee; padding-bottom: 8px;">Resumen de la Orden</h3>
            <table style="width:100%; border-collapse: collapse; margin-top: 10px; font-size: 16px;">
                <thead>
                    <tr style="background-color: #f2f2f2; text-align: left;">
                        <th style="padding: 12px; border: 1px solid #ddd;">Producto</th>
                        <th style="padding: 12px; border: 1px solid #ddd; text-align: center;">Cant.</th>
                    </tr>
                </thead>
                <tbody>
        """
        for item in items:
            items_html += f"""
                <tr>
                    <td style="padding: 12px; border: 1px solid #ddd; color: #555;">
                        <strong style="color: #000;">{item["name"]}</strong><br>
                        <span style="font-size: 13px; color: #888;">SKU: {item["sku"]}</span>
                    </td>
                    <td style="padding: 12px; border: 1px solid #ddd; text-align: center; font-weight: bold;">{item["qty"]}</td>
                </tr>
            """
        items_html += "</tbody></table></div>"

    reason_html = ""
    if reason:
        reason_html = f"""
        <div style="margin-top: 20px; padding: 15px; background-color: #fff3f3; border-left: 5px solid #e53935;">
            <p style="margin: 0; color: #b71c1c; font-size: 16px;"><strong>Motivo del rechazo:</strong> {reason}</p>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: {bg_color}; margin: 0; padding: 40px 20px; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
            <div style="background-color: {header_color}; color: white; padding: 30px 20px; text-align: center;">
                <h1 style="margin: 0; font-size: 28px; letter-spacing: 1px;">{title}</h1>
            </div>
            <div style="padding: 30px; color: #333;">
                <p style="font-size: 20px; margin-bottom: 20px;">Hola, <strong>{customer}</strong></p>
                <p style="font-size: 16px; color: #666;">
                    {"Lamentamos informarle que su pedido no pudo ser procesado." if is_error else "¡Buenas noticias! Hemos recibido su pedido correctamente y está siendo procesado."}
                </p>
                {reason_html}
                {items_html}
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; text-align: center;">
                    <p style="font-size: 18px; font-weight: bold; color: {header_color};">Gracias por confiar en nosotros.</p>
                </div>
            </div>
            <div style="background-color: #f4f4f4; padding: 20px; text-align: center; font-size: 13px; color: #999;">
                <p style="margin: 0;">Este es un correo automático, por favor no responda a este mensaje.</p>
                <p style="margin: 5px 0 0;">© 2024 Notification Service</p>
            </div>
        </div>
    </body>
    </html>
    """


async def send_order_confirmation(order_data: dict):
    skus = [item["sku"] for item in order_data["items"]]
    product_names = await get_product_names(skus)

    items_with_names = []
    for item in order_data["items"]:
        items_with_names.append(
            {
                "sku": item["sku"],
                "name": product_names.get(item["sku"], item["sku"]),
                "qty": item["qty"],
            }
        )

    html_body = generate_html(
        title="¡Orden recibida!",
        customer=order_data["customer"],
        items=items_with_names,
        is_error=False,
    )
    items_text = ", ".join(
        [f"{item['name']} (x{item['qty']})" for item in items_with_names]
    )
    plain_body = f"ID: {order_data['order_id']}\nCliente: {order_data['customer']}\nArtículos: {items_text}"

    await send_email(
        plain_body=plain_body,
        html_body=html_body,
        subject=f"Orden confirmada: {order_data['order_id']}",
        order_id=order_data["order_id"],
        recipient=settings.email_to,
        is_error=False,
    )


async def send_order_rejection(order_data: dict):
    reason = order_data.get("reason", "Motivo no especificado")
    skus = [item["sku"] for item in order_data["items"]]
    product_names = await get_product_names(skus)

    items_with_names = []
    for item in order_data["items"]:
        items_with_names.append(
            {
                "sku": item["sku"],
                "name": product_names.get(item["sku"], item["sku"]),
                "qty": item["qty"],
            }
        )

    html_body = generate_html(
        title="Orden no procesada",
        customer=order_data["customer"],
        items=items_with_names,
        is_error=True,
        reason=reason,
    )
    items_text = ", ".join(
        [f"{item['name']} (x{item['qty']})" for item in items_with_names]
    )
    plain_body = f"ID: {order_data['order_id']}\nCliente: {order_data['customer']}\nArtículos: {items_text}\nMotivo del rechazo: {reason}"

    await send_email(
        plain_body=plain_body,
        html_body=html_body,
        subject=f"Orden rechazada: {order_data['order_id']}",
        order_id=order_data["order_id"],
        recipient=settings.email_to,
        is_error=True,
        reason=reason,
    )


async def send_email(
    plain_body: str,
    html_body: str,
    subject: str,
    order_id: str,
    recipient: str,
    is_error: bool = False,
    reason: str = None,
):
    # Guardar en la base de notificaciones ANTES de enviar (o después, según prefieras)
    async with AsyncSessionLocal_notifications() as session:
        notification = Notification(
            id=str(uuid.uuid4()),
            order_id=order_id,
            recipient=recipient,
            status="failure" if is_error else "success",
            reason=reason,
        )
        session.add(notification)
        await session.commit()

    if not all(
        [
            settings.smtp_host,
            settings.smtp_user,
            settings.smtp_password,
            settings.email_from,
            settings.email_to,
        ]
    ):
        logger.warning("Configuración de correo incompleta, no se enviará email")
        return

    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = settings.email_to
    message["Subject"] = subject
    message.set_content(plain_body)
    message.add_alternative(html_body, subtype="html")

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=False,
            start_tls=True,
        )
        logger.info(f"Correo enviado: {subject}")
        # Guardar también en memoria (opcional)
        notifications_sent.append(
            {
                "subject": subject,
                "to": settings.email_to,
                "timestamp": asyncio.get_event_loop().time(),
            }
        )
    except Exception as e:
        logger.error(f"Error enviando correo: {e}")


async def process_order(message: aio_pika.IncomingMessage):
    async with message.process():
        routing_key = message.routing_key
        order_data = json.loads(message.body.decode())
        if routing_key == "order.created":
            logger.info(f"Procesando confirmación para orden {order_data['order_id']}")
            await send_order_confirmation(order_data)
        elif routing_key == "order.error":
            logger.info(
                f"Procesando rechazo para orden {order_data['order_id']}: {order_data.get('reason')}"
            )
            await send_order_rejection(order_data)
        else:
            logger.warning(f"Routing key desconocido: {routing_key}")


async def rabbitmq_consumer():
    while True:
        try:
            connection = await aio_pika.connect_robust(settings.rabbitmq_url)
            async with connection:
                channel = await connection.channel()
                exchange = await channel.declare_exchange(
                    "orders", aio_pika.ExchangeType.TOPIC, durable=True
                )
                queue = await channel.declare_queue(
                    "notification.order.events", durable=True
                )
                await queue.bind(exchange, routing_key="order.created")
                await queue.bind(exchange, routing_key="order.error")
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
    # Crear tablas en la base de notificaciones
    async with engine_notifications.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    thread = threading.Thread(target=start_consumer, daemon=True)
    thread.start()
    logger.info("Consumidor de RabbitMQ iniciado en segundo plano")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)
