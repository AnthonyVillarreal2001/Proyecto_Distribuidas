from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")
    # Database
    database_url: str = "postgresql+psycopg2://postgres:postgres@postgres:5432/logiflow_db"

    # JWT
    secret_key: str = "your-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    jwt_issuer: str = "logiflow-auth"

    # Service Ports
    auth_service_port: int = 5001
    pedido_service_port: int = 5002
    fleet_service_port: int = 5003
    billing_service_port: int = 5004
    api_gateway_port: int = 5000

    # Service URLs
    auth_service_url: str = "http://localhost:5001"
    pedido_service_url: str = "http://localhost:5002"
    fleet_service_url: str = "http://localhost:5003"
    billing_service_url: str = "http://localhost:5004"
    ws_service_port: int = 5005
    ws_service_url: str = "http://localhost:5005"

    # Messaging (RabbitMQ)
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"

    # CORS
    cors_origins: list = ["http://localhost:3000", "http://localhost:5000"]

    # Rate Limiting
    rate_limit_per_minute: int = 100

    # Logging
    log_level: str = "INFO"


@lru_cache()
def get_settings() -> Settings:
    """Singleton pattern for settings"""
    return Settings()
