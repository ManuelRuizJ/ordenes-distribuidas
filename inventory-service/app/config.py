from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    rabbitmq_url: str
    database_url: str  # <-- nueva

    class Config:
        env_file = ".env"


settings = Settings()
