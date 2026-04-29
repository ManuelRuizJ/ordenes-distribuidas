from fastapi import FastAPI, Request, Response, status, Depends
import logging
import uuid
import time
import httpx
from app.redis_client import redis_client
from app.schemas import (
    OrderRequest,
    OrderResponse,
    OrderStatusResponse,
    generate_order_id,
)
from app.services.writer_client import forward_order_to_writer
from app.auth_deps import get_current_user_id, require_admin, get_username_from_token

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
async def create_order(
    order: OrderRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    username: str = Depends(get_username_from_token),
):
    request_id = request.state.request_id
    order_id = generate_order_id()
    now = time.time()

    redis_key = f"order:{order_id}"
    await redis_client.hset(
        redis_key, mapping={"status": "RECEIVED", "last_update": str(now)}
    )
    await redis_client.expire(redis_key, 86400)

    payload = {
        "order_id": order_id,
        "customer": username,  # ← ahora del token
        "items": [item.dict() for item in order.items],
    }

    async def notify_writer():
        success = await forward_order_to_writer(payload, request_id)
        if not success:
            await redis_client.hset(redis_key, "status", "FAILED")
            await redis_client.hset(redis_key, "last_update", str(time.time()))
            logger.error(f"Orden {order_id} marcada como FAILED")

    import asyncio

    asyncio.create_task(notify_writer())

    return OrderResponse(order_id=order_id, status="RECEIVED")


@app.get("/orders/{order_id}", response_model=OrderStatusResponse)
async def get_order_status(order_id: str):
    redis_key = f"order:{order_id}"
    data = await redis_client.hgetall(redis_key)
    logger.info(f"Redis data for {order_id}: {data}")  # <-- línea añadida
    if not data:
        return Response(status_code=404, content="Order not found")
    response_data = {
        "order_id": order_id,
        "status": data.get("status", "UNKNOWN"),
        "last_update": data.get("last_update"),
    }
    if "error_reason" in data:
        response_data["reason"] = data["error_reason"]
    return response_data


# --- Endpoints protegidos para admin ---
@app.get("/stock")
async def get_stock(_: str = Depends(require_admin)):
    async with httpx.AsyncClient() as client:
        resp = await client.get("http://inventory-service:8002/stock")
        return resp.json()


@app.get("/notifications")
async def get_notifications(_: str = Depends(require_admin)):
    async with httpx.AsyncClient() as client:
        resp = await client.get("http://notification-service:8004/notifications")
        return resp.json()


@app.get("/analytics")
async def get_analytics(_: str = Depends(require_admin)):
    async with httpx.AsyncClient() as client:
        resp = await client.get("http://analytics-service:8003/analytics")
        return resp.json()


@app.on_event("shutdown")
async def shutdown():
    await redis_client.close()


""" async def get_current_user_role(token: str = Header(..., alias="Authorization")) -> tuple[str, str]:
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
    ... """
