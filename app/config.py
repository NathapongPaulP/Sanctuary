from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        extra="ignore",  # .env also has POSTGRES_* which aren't fields here
    )

    DATABASE_URL: str


settings = Settings()
