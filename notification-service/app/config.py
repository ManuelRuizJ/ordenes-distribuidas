from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    rabbitmq_url: str
    database_url: str
    notifications_db_url: str = Field(
        ..., validation_alias="NOTIFICATIONS_DATABASE_URL"
    )
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    email_from: str
    email_to: str

    class Config:
        env_file = ".env"


settings = Settings()
