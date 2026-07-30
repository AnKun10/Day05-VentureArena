import sqlite3

from companion_discord.digest import unanswered_for_classes


def test_ta_digest_only_includes_questions_for_the_tas_classes(tmp_path):
    database = tmp_path / "companion.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE unanswered_questions (question TEXT, class_name TEXT, created_at TEXT)")
        connection.executemany(
            "INSERT INTO unanswered_questions VALUES (?, ?, ?)",
            [("Lab 3 học gì?", "Lab-D305", "2026-07-30"), ("LT có record không?", "LT", "2026-07-30")],
        )

    assert unanswered_for_classes(database, ["Lab-D305"]) == ["Lab 3 học gì?"]
