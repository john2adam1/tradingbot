from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    GEMINI_API_KEY: str
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID: str = ""

    # Gemini model configuration
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # FastAPI
    HOST: str = "0.0.0.0"
    PORT: int = 8000


settings = Settings()
