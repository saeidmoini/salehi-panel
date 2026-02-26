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
    default_batch_size: int = Field(100, alias="DEFAULT_BATCH_SIZE")
    max_batch_size: int = Field(40, alias="MAX_BATCH_SIZE")
    timezone: str = Field("Asia/Tehran", alias="TIMEZONE")
    skip_holidays_default: bool = Field(True, alias="SKIP_HOLIDAYS")
    assignment_timeout_minutes: int = Field(1440, alias="ASSIGNMENT_TIMEOUT_MINUTES")
    call_cooldown_days: int = Field(3, alias="CALL_COOLDOWN_DAYS")
    # Legacy single-profile bank config (kept as fallback)
    bank_sms_sender: str = Field("30008528", alias="BANK_SMS_SENDER")
    manager_alert_numbers: str = Field("", alias="MANAGER_ALERT_NUMBERS")
    melipayamak_advanced_url: str = Field(
        "https://console.melipayamak.com/api/send/advanced",
        alias="MELIPAYAMAK_ADVANCED_URL",
    )
    melipayamak_from: str = Field("9982003047", alias="MELIPAYAMAK_FROM")
    melipayamak_api_key: str = Field("", alias="MELIPAYAMAK_API_KEY")
    # Multi-profile bank config (preferred)
    salehi_bank_name: str = Field("Salehi Bank", alias="SALEHI_BANK_NAME")
    # Supports one or many sender numbers separated by comma.
    salehi_bank_sms_sender: str = Field("", alias="SALEHI_BANK_SMS_SENDER")
    salehi_manager_alert_numbers: str = Field("", alias="SALEHI_MANAGER_ALERT_NUMBERS")
    salehi_melipayamak_from: str = Field("", alias="SALEHI_MELIPAYAMAK_FROM")
    salehi_melipayamak_api_key: str = Field("", alias="SALEHI_MELIPAYAMAK_API_KEY")
    salehi_sms_parser: str = Field("default", alias="SALEHI_SMS_PARSER")
    default_bank_name: str = Field("Default Bank", alias="DEFAULT_BANK_NAME")
    # Supports one or many sender numbers separated by comma.
    default_bank_sms_sender: str = Field("", alias="DEFAULT_BANK_SMS_SENDER")
    default_manager_alert_numbers: str = Field("", alias="DEFAULT_MANAGER_ALERT_NUMBERS")
    default_melipayamak_from: str = Field("", alias="DEFAULT_MELIPAYAMAK_FROM")
    default_melipayamak_api_key: str = Field("", alias="DEFAULT_MELIPAYAMAK_API_KEY")
    default_sms_parser: str = Field("default", alias="DEFAULT_SMS_PARSER")
    google_sheet_webhook_url: str = Field("", alias="GOOGLE_SHEET_WEBHOOK_URL")
    google_sheet_webhook_token: str = Field("", alias="GOOGLE_SHEET_WEBHOOK_TOKEN")
    google_sheet_webhook_timeout_seconds: int = Field(10, alias="GOOGLE_SHEET_WEBHOOK_TIMEOUT_SECONDS")
    short_retry_seconds: int = 300
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
