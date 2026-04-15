from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # JWT
    jwt_secret_key: str = Field(..., validation_alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(30, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(7, validation_alias="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Database
    database_url: str = Field(..., validation_alias="AUTH_DATABASE_URL")  # base de usuarios
    
    # Redis (para blacklist)
    redis_url: str = Field(..., validation_alias="REDIS_URL")
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()