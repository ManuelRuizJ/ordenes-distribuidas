from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    database_url: str = Field(..., validation_alias="DATABASE_URL")
    redis_url: str = Field(..., validation_alias="REDIS_URL")
    rabbitmq_url: str = Field(..., validation_alias="RABBITMQ_URL")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()