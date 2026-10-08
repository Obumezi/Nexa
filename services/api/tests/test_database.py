from sqlalchemy import text

from nexa_api.database import (
    SessionLocal,
    check_database_connection,
    engine,
)


def test_database_connection() -> None:
    """Nexa should successfully connect to SQLite."""

    assert check_database_connection() is True


def test_database_session() -> None:
    """A Nexa database session should execute a basic query."""

    with SessionLocal() as session:
        result = session.execute(text("SELECT 1")).scalar_one()

    assert result == 1


def test_sqlite_foreign_keys_are_enabled() -> None:
    """SQLite should enforce relationships between Nexa records."""

    with engine.connect() as connection:
        result = connection.execute(
            text("PRAGMA foreign_keys")
        ).scalar_one()

    assert result == 1