from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"

    class Config:
        env_file = ".env"

settings = Settings()