from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    redis_url: str = Field(..., validation_alias="REDIS_URL")
    writer_service_url: str = Field(..., validation_alias="WRITER_SERVICE_URL")
    writer_timeout_seconds: float = Field(1.0, validation_alias="WRITER_TIMEOUT_SECONDS")
    writer_max_retries: int = Field(1, validation_alias="WRITER_MAX_RETRIES")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()