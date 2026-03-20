from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    smtp_host: str = Field("smtp.gmail.com", validation_alias="SMTP_HOST")
    smtp_port: int = Field(587, validation_alias="SMTP_PORT")
    smtp_user: str = Field("", validation_alias="SMTP_USER")
    smtp_password: str = Field("", validation_alias="SMTP_PASSWORD")
    email_from: str = Field("", validation_alias="EMAIL_FROM")
    email_to: str = Field("", validation_alias="EMAIL_TO")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()