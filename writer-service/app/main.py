from app.rabbitmq import publish_order_created
from fastapi import FastAPI, Request, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import time
import uuid
from app import models
from app.db import engine, get_db, AsyncSessionLocal
from app.redis_client import redis_client
from app.schemas import InternalOrder
from app.repositories.orders_repo import upsert_order
from app.seeder import seed_products

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Writer Service - Órdenes")


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id")
    if not request_id:
        request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        await seed_products(session)


@app.on_event("shutdown")
async def shutdown():
    await engine.dispose()
    await redis_client.close()


@app.post("/internal/orders", status_code=status.HTTP_201_CREATED)
async def internal_create_order(
    order: InternalOrder,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    request_id = request.state.request_id
    logger.info("Solicitud interna para orden %s con request_id=%s", order.order_id, request_id)

    redis_key = f"order:{order.order_id}"

    try:
        inserted = await upsert_order(db, order)

        if inserted:
            # Actualizar Redis a PERSISTED
            await redis_client.hset(redis_key, mapping={
                "status": "PERSISTED",
                "last_update": str(time.time())
            })
            await publish_order_created(order.dict())
            logger.info("Orden %s marcada como PERSISTED en Redis", order.order_id)
        else:
            # Ya existía, pero igual actualizamos last_update (opcional)
            await redis_client.hset(redis_key, "last_update", str(time.time()))
            logger.info("Orden %s ya existía, se actualizó last_update", order.order_id)

        return {"status": "ok", "order_id": order.order_id}

    except Exception as e:
        logger.error("Error persistendo orden %s: %s", order.order_id, e)
        # Marcar como fallido en Redis
        await redis_client.hset(redis_key, mapping={
            "status": "FAILED",
            "last_update": str(time.time())
        })
        raise HTTPException(status_code=500, detail="Internal server error")