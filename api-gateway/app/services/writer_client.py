import httpx
import asyncio
import logging
from app.config import settings

logger = logging.getLogger(__name__)


async def forward_order_to_writer(order_data: dict, request_id: str) -> bool:
    """
    Envía la orden al writer-service con timeout y reintentos.
    Retorna True si el writer respondió 2xx, False en caso contrario.
    """
    url = f"{settings.writer_service_url}/internal/orders"
    headers = {"X-Request-Id": request_id, "Content-Type": "application/json"}
    timeout = httpx.Timeout(settings.writer_timeout_seconds)

    for attempt in range(settings.writer_max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=order_data, headers=headers)
                resp.raise_for_status()
                logger.info("Orden enviada a writer (intento %d): %s", attempt + 1, resp.status_code)
                return True
        except Exception as e:
            logger.warning("Error al enviar a writer (intento %d): %s", attempt + 1, e)
            if attempt < settings.writer_max_retries:
                # Esperar un poco antes de reintentar
                await asyncio.sleep(0.2)
            else:
                logger.error("Writer no disponible después de %d intentos", settings.writer_max_retries + 1)
                return False
    return False