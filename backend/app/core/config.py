"""HealthNet configuration — Pydantic Settings loading from environment."""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    APP_NAME: str = "HealthNet"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str = "postgresql+asyncpg://healthnet:healthnet_dev_password@localhost:5432/healthnet_db"
    DATABASE_SYNC_URL: str = "postgresql+psycopg2://healthnet:healthnet_dev_password@localhost:5432/healthnet_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    KEYCLOAK_URL: str = "http://localhost:8180"
    KEYCLOAK_REALM: str = "healthnet"
    KEYCLOAK_CLIENT_ID: str = "healthnet-backend"
    KEYCLOAK_CLIENT_SECRET: str = "healthnet-backend-secret"
    KEYCLOAK_ADMIN_USERNAME: str = "admin"
    KEYCLOAK_ADMIN_PASSWORD: str = "admin"
    KEYCLOAK_AUDIENCE: str = "healthnet-backend"
    HAPI_FHIR_BASE_URL: str = "http://localhost:8090/fhir"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    SECRET_KEY: str = "dev_secret_key_changeme"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @model_validator(mode="after")
    def require_production_secrets(self):
        if self.ENVIRONMENT.lower() == "production":
            placeholders = {
                "DATABASE_URL": self.DATABASE_URL,
                "KEYCLOAK_CLIENT_SECRET": self.KEYCLOAK_CLIENT_SECRET,
                "KEYCLOAK_ADMIN_PASSWORD": self.KEYCLOAK_ADMIN_PASSWORD,
                "SECRET_KEY": self.SECRET_KEY,
            }
            unsafe = [
                name
                for name, value in placeholders.items()
                if not value or value in {"healthnet-backend-secret", "admin", "dev_secret_key_changeme"}
            ]
            if unsafe:
                raise ValueError(f"Unsafe or missing production settings: {', '.join(unsafe)}")
        return self

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

