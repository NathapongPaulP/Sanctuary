from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        extra="ignore",  # .env also has POSTGRES_* which aren't fields here
    )

    DATABASE_URL: str
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]


settings = Settings()


BANGKOK = ZoneInfo("Asia/Bangkok")
TERM_1_START = (5, 14)  # (month, day)
TERM_2_START = (11, 1)


def current_year_and_term() -> tuple[int, int]:
    """Academic year (พ.ศ.) and term, worked out fresh on every call."""
    today = datetime.now(BANGKOK).date()

    # Gregorian year this academic year started in
    year = today.year if today >= date(today.year, *TERM_1_START) else today.year - 1

    term = 1 if today < date(year, *TERM_2_START) else 2
    return year + 543, term
