# app/core/config.py
# Configurações centrais para o aplicativo Genesys API Backend.

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)
    # General
    # App
    APP_NAME: str = "genesys-backend"
    APP_VERSION: str = "0.1.0"
    TIMEZONE: str = "Europe/Lisbon"
    APP_ENV: Literal["dev", "prod"] = "dev"
    APP_PORT: int = 8000
    # Logging
    LOG_LEVEL: str = "DEBUG"
    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "genesys"
    DB_USER: str = "postgres"
    DB_PASS: str = "postgres"
    # JWT
    JWT_SECRET: str = "random-jwt"
    JWT_EXPIRE_MIN: int = 120
    JWT_REFRESH_EXPIRE_MIN: int = 43200
    # Feed
    FEED_DOWNLOAD_TIMEOUT: int = 60
    # General config
    EOL_THRESHOLD_DAYS: int = 180
    # Prestashop
    PS_GENESYS_KEY: str
    PS_AUTH_VALIDATE_HEADER: str = "X-Genesys-Key"
    PS_USER_AGENT: str = "genesys/2.0"
    PS_AUTH_TIMEOUT_S: int = 10
    PS_AUTH_VERIFY_SSL: str = "true"
    # endpoints
    PS_AUTH_VALIDATE_URL: str
    PS_CATEGORIES_URL: str
    PS_BRANDS_URL: str
    PS_IMPORT_PRODUCT_URL: str
    PS_GET_ORDERS_URL: str
    PS_GET_ORDER_URL: str
    # Sage
    SAGE_BASE_URL: str = "https://sageapi.example.com"
    SAGE_USER_AGENT: str = "genesys/2.0"
    SAGE_ACCESS_CLIENT: str = "sage_access_client"
    SAGE_ACCESS_SECRET: str = "sage_access_secret"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASS}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


settings = Settings()
