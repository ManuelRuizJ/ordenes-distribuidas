from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.config import settings
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Engine para la base principal (lectura de productos)
engine_main = create_async_engine(
    settings.database_url,
    echo=True,
    pool_pre_ping=True
)

# Engine para la base de notificaciones (escritura/lectura propia)
engine_notifications = create_async_engine(
    settings.notifications_db_url,
    echo=True,
    pool_pre_ping=True
)

AsyncSessionLocal_main = async_sessionmaker(engine_main, expire_on_commit=False)
AsyncSessionLocal_notifications = async_sessionmaker(engine_notifications, expire_on_commit=False)