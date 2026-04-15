from fastapi import FastAPI
from app.routers import auth
from app.db import engine, Base
from app.redis_client import redis_client
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Auth Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.on_event("shutdown")
async def shutdown():
    await redis_client.close()
    await engine.dispose()