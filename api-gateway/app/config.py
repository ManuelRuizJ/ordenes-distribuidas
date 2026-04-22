from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    redis_url: str = Field(..., validation_alias="REDIS_URL")
    writer_service_url: str = Field(..., validation_alias="WRITER_SERVICE_URL")
    writer_timeout_seconds: float = Field(1.0, validation_alias="WRITER_TIMEOUT_SECONDS")
    writer_max_retries: int = Field(1, validation_alias="WRITER_MAX_RETRIES")
    jwt_secret_key: str = Field(..., validation_alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", validation_alias="JWT_ALGORITHM")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()