"""TA digest queries over the Companion handoff queue."""

from pathlib import Path
import sqlite3


def unanswered_for_classes(database: str | Path, classes: list[str]) -> list[str]:
    if not classes:
        return []
    placeholders = ", ".join("?" for _ in classes)
    try:
        with sqlite3.connect(database) as connection:
            return [row[0] for row in connection.execute(
                f"SELECT question FROM unanswered_questions WHERE class_name IN ({placeholders}) ORDER BY created_at", classes
            )]
    except sqlite3.OperationalError:
        return []
