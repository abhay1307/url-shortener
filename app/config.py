from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://urluser:urlpassword@localhost:5432/urldb"
    redis_url: str = "redis://localhost:6379"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    base_url: str = "http://localhost:8000"

    class Config:
        env_file = ".env"


settings = Settings()
