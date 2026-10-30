import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "../../../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # WhatsApp Cloud API
    WHATSAPP_PHONE_NUMBER_ID: str = Field(default="")
    WHATSAPP_ACCESS_TOKEN: str = Field(default="")
    WHATSAPP_VERIFY_TOKEN: str = Field(default="munim_verify_2026")
    WHATSAPP_API_VERSION: str = Field(default="v19.0")

    # Owner details
    OWNER_WHATSAPP_NUMBER: str = Field(default="")

    # Google Sheets
    GOOGLE_SERVICE_ACCOUNT_JSON: str = Field(default="./backend/data/service_account.json")
    GOOGLE_SHEET_ID: str = Field(default="")

    # AI (Gemini & Groq)
    GEMINI_API_KEY: str = Field(default="")
    GEMINI_MODEL: str = Field(default="gemini-3.5-flash")
    GROQ_API_KEY: str = Field(default="")

    # App settings
    APP_ENV: str = Field(default="development")
    APP_SECRET_KEY: str = Field(default="munim-ai-hackathon-secret-2026")
    LOG_LEVEL: str = Field(default="INFO")
    DATABASE_URL: str = Field(default="sqlite:///./backend/data/munim.db")
    DRY_RUN: bool = Field(default=False)

settings = Settings()

