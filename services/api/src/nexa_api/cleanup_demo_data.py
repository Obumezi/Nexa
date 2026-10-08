"""Clean duplicate and temporary demo task data from Nexa."""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

DATABASE_PATH = Path("nexa.db")


def create_backup() -> Path:
    """Create a timestamped backup before changing the demo database."""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup_path = Path(
        f"nexa.before_demo_cleanup_{timestamp}.db"
    )

    shutil.copy2(
        DATABASE_PATH,
        backup_path,
    )

    return backup_path


def find_task_table(
    connection: sqlite3.Connection,
) -> str:
    """Locate the household task table."""

    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()

    table_names = [
        row[0]
        for row in rows
    ]

    expected_names = [
        "household_tasks",
        "household_task",
        "tasks",
    ]

    for name in expected_names:
        if name in table_names:
            return name

    raise RuntimeError(
        "Could not locate the household task table. "
        f"Available tables: {table_names}"
    )


def show_tasks(
    connection: sqlite3.Connection,
    table_name: str,
    heading: str,
) -> None:
    """Print current tasks."""

    rows = connection.execute(
        f"""
        SELECT rowid, id, title, status
        FROM {table_name}
        ORDER BY rowid
        """
    ).fetchall()

    print(f"\n{heading}")
    print("-" * len(heading))

    if not rows:
        print("No tasks found.")
        return

    for row in rows:
        rowid, task_id, title, status = row

        print(
            f"{rowid}: "
            f"{title!r} "
            f"[{status}] "
            f"({task_id})"
        )


def delete_test_tasks(
    connection: sqlite3.Connection,
    table_name: str,
) -> None:
    """Remove known temporary smoke-test records."""

    test_titles = [
    "E2E verification task",
    "MCP integration smoke test",
    "Live E2E safety test",
    "Live E2E confirmation test",
    "string",
]

    for title in test_titles:
        cursor = connection.execute(
            f"""
            DELETE FROM {table_name}
            WHERE title = ?
            """,
            (title,),
        )

        print(
            f"Removed {cursor.rowcount} "
            f"task(s) named {title!r}."
        )


def deduplicate_title(
    connection: sqlite3.Connection,
    table_name: str,
    title: str,
) -> None:
    """Keep the oldest copy of a task title and remove duplicates."""

    rows = connection.execute(
        f"""
        SELECT rowid, id
        FROM {table_name}
        WHERE title = ?
        ORDER BY rowid
        """,
        (title,),
    ).fetchall()

    if len(rows) <= 1:
        print(
            f"No duplicate cleanup needed for {title!r}."
        )
        return

    keep_rowid = rows[0][0]

    cursor = connection.execute(
        f"""
        DELETE FROM {table_name}
        WHERE title = ?
        AND rowid != ?
        """,
        (
            title,
            keep_rowid,
        ),
    )

    print(
        f"Removed {cursor.rowcount} duplicate(s) "
        f"for {title!r}."
    )


def main() -> None:
    """Clean the local Nexa demo database."""

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH.resolve()}"
        )

    backup_path = create_backup()

    print(
        f"Backup created: {backup_path.resolve()}"
    )

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    try:
        table_name = find_task_table(
            connection
        )

        print(
            f"Using task table: {table_name}"
        )

        show_tasks(
            connection,
            table_name,
            "Before cleanup",
        )

        delete_test_tasks(
            connection,
            table_name,
        )

        deduplicate_title(
            connection,
            table_name,
            "Wash the car",
        )

        deduplicate_title(
            connection,
            table_name,
            "Review unexpected delivery",
        )

        connection.commit()

        show_tasks(
            connection,
            table_name,
            "After cleanup",
        )

        print(
            "\nDemo task cleanup completed successfully."
        )

    except Exception:
        connection.rollback()

        print(
            "\nCleanup failed. "
            "No database changes were committed."
        )

        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()