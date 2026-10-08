from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from nexa_api.config import get_settings

settings = get_settings()

database_url = settings.sqlalchemy_database_url

connect_args = (
    {"check_same_thread": False}
    if settings.is_sqlite
    else {}
)


engine = create_engine(
    database_url,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True,
)


if settings.is_sqlite:

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(
        dbapi_connection: Any,
        connection_record: Any,
    ) -> None:
        """Enable foreign-key enforcement for SQLite connections."""

        del connection_record

        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class inherited by all Nexa database models."""


def get_db() -> Generator[Session, None, None]:
    """Provide a database session and close it after use."""

    with SessionLocal() as session:
        yield session


def check_database_connection() -> bool:
    """Return True when Nexa can communicate with its database."""

    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT 1")
        ).scalar_one()

    return result == 1