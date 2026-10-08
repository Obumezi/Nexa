from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for the Nexa API."""

    model_config = SettingsConfigDict(
        env_prefix="NEXA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Nexa Core API"
    environment: str = "development"
    api_version: str = "0.1.0"

    api_host: str = "127.0.0.1"
    api_port: int = 8000
    web_origin: str = "http://localhost:5173"

    # Local development defaults to SQLite.
    #
    # Production can override this with:
    # NEXA_DATABASE_URL=postgresql+psycopg://...
    database_url: str = "sqlite:///./nexa.db"

    openai_api_key: str | None = None
    openai_model: str = "gpt-6-astra"

    @property
    def is_production(self) -> bool:
        """Return whether Nexa is running in production."""

        return self.environment.casefold() == "production"

    @property
    def is_sqlite(self) -> bool:
        """Return whether Nexa is using SQLite."""

        return self.database_url.startswith("sqlite")

    @property
    def sqlalchemy_database_url(self) -> str:
        """Return a SQLAlchemy-compatible database URL."""

        url = self.database_url.strip()

        if url.startswith("postgres://"):
            return url.replace(
                "postgres://",
                "postgresql+psycopg://",
                1,
            )

        if url.startswith("postgresql://"):
            return url.replace(
                "postgresql://",
                "postgresql+psycopg://",
                1,
            )

        return url


@lru_cache
def get_settings() -> Settings:
    """Return the cached Nexa configuration."""

    return Settings()