""" from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    database_url: str = Field(..., validation_alias="DATABASE_URL")
    redis_url: str = Field(..., validation_alias="REDIS_URL")
    rabbitmq_url: str = Field(..., validation_alias="RABBITMQ_URL")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings() """



from pydantic_settings import BaseSettings
from pydantic import field_validator, Field

class Settings(BaseSettings):
    database_url: str = Field(..., validation_alias="DATABASE_URL")
    redis_url: str = Field(..., validation_alias="REDIS_URL")
    rabbitmq_url: str = Field(..., validation_alias="RABBITMQ_URL")
    
    @field_validator("database_url", mode="before")
    @classmethod
    def fix_postgres_protocol(cls, v: str) -> str:
        if v and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
