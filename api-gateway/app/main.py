from fastapi import FastAPI, Request, Response, status, Depends, Header, HTTPException
import logging
import uuid
import time
from app.redis_client import redis_client
from app.schemas import OrderRequest, OrderResponse, OrderStatusResponse, generate_order_id
from app.services.writer_client import forward_order_to_writer
from app.auth_deps import get_current_user_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="API Gateway - Órdenes")


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id")
    if not request_id:
        request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


@app.post("/orders", status_code=status.HTTP_202_ACCEPTED, response_model=OrderResponse)
async def create_order(order: OrderRequest, request: Request, user_id: str = Depends(get_current_user_id)):
    request_id = request.state.request_id
    order_id = generate_order_id()
    now = time.time()

    # Guardar estado inicial en Redis
    redis_key = f"order:{order_id}"
    await redis_client.hset(redis_key, mapping={
        "status": "RECEIVED",
        "last_update": str(now)
    })
    await redis_client.expire(redis_key, 86400)  # TTL 24h

    # Preparar payload para writer
    payload = {
        "order_id": order_id,
        "customer": order.customer,
        "items": [item.dict() for item in order.items]
    }

    # Enviar a writer en background sin bloquear la respuesta
    async def notify_writer():
        success = await forward_order_to_writer(payload, request_id)
        if not success:
            # Marcar como fallido en Redis
            await redis_client.hset(redis_key, "status", "FAILED")
            await redis_client.hset(redis_key, "last_update", str(time.time()))
            logger.error(f"Orden {order_id} marcada como FAILED por fallo en writer")

    import asyncio
    asyncio.create_task(notify_writer())

    return OrderResponse(order_id=order_id, status="RECEIVED")


@app.get("/orders/{order_id}", response_model=OrderStatusResponse)
async def get_order_status(order_id: str):
    redis_key = f"order:{order_id}"
    data = await redis_client.hgetall(redis_key)
    logger.info(f"Redis data for {order_id}: {data}")   # <-- línea añadida
    if not data:
        return Response(status_code=404, content="Order not found")
    response_data = {
        "order_id": order_id,
        "status": data.get("status", "UNKNOWN"),
        "last_update": data.get("last_update")
    }
    if "error_reason" in data:
        response_data["reason"] = data["error_reason"]
    return response_data


@app.on_event("shutdown")
async def shutdown():
    await redis_client.close()

async def get_current_user_role(token: str = Header(..., alias="Authorization")) -> tuple[str, str]:
    # ... validar token y extraer payload
    user_id = payload.get("sub")
    role = payload.get("role", "user")
    return user_id, role

async def require_admin(token: str = Header(..., alias="Authorization")):
    user_id, role = await get_current_user_role(token)
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    return user_id

@app.delete("/orders/{order_id}")
async def delete_order(order_id: str, admin_id: str = Depends(require_admin)):
    # lógica para eliminar orden (solo admin)
    ...