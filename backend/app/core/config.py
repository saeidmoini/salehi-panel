from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Salehi Dialer Panel"
    database_url: str = Field(..., alias="DATABASE_URL")
    secret_key: str = Field(..., alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(1440, alias="ACCESS_TOKEN_EXPIRE_MINUTES")  # default: 1 day
    algorithm: str = "HS256"
    dialer_token: str = Field(..., alias="DIALER_TOKEN")
    max_batch_size: int = Field(500, alias="MAX_BATCH_SIZE")
    default_batch_size: int = Field(100, alias="DEFAULT_BATCH_SIZE")
    timezone: str = Field("Asia/Tehran", alias="TIMEZONE")
    skip_holidays_default: bool = Field(True, alias="SKIP_HOLIDAYS")
    assignment_timeout_minutes: int = Field(60, alias="ASSIGNMENT_TIMEOUT_MINUTES")
    short_retry_seconds: int = 120
    long_retry_seconds: int = 900
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost",
            "http://127.0.0.1",
        ],
        alias="CORS_ORIGINS",
    )


def get_settings() -> Settings:
    return Settings()
