"""Read configured Discord channels and retain only source metadata."""

import json
from pathlib import Path
import sqlite3


def _connection(database: str | Path):
    Path(database).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database)
    connection.execute(
        """CREATE TABLE IF NOT EXISTS posts (
        message_id TEXT NOT NULL, channel_id TEXT NOT NULL, source_group TEXT NOT NULL,
        author_id TEXT, author_name TEXT, author_roles TEXT NOT NULL, content TEXT NOT NULL,
        attachments TEXT NOT NULL, jump_url TEXT NOT NULL, created_at TEXT NOT NULL,
        PRIMARY KEY (channel_id, message_id))"""
    )
    return connection


def save_posts(database: str | Path, posts: list[dict]) -> None:
    with _connection(database) as connection:
        connection.executemany(
            """INSERT OR IGNORE INTO posts VALUES
            (:message_id, :channel_id, :source_group, :author_id, :author_name, :author_roles,
             :content, :attachments, :jump_url, :created_at)""",
            [{**post, "author_roles": json.dumps(post["author_roles"]), "attachments": json.dumps(post["attachments"])} for post in posts],
        )


def latest_posts(database: str | Path, source_group: str, limit: int) -> list[dict]:
    try:
        with _connection(database) as connection:
            rows = connection.execute(
                "SELECT * FROM posts WHERE source_group = ? ORDER BY created_at DESC LIMIT ?", (source_group, limit)
            ).fetchall()
    except sqlite3.OperationalError:
        return []
    columns = ("message_id", "channel_id", "source_group", "author_id", "author_name", "author_roles", "content", "attachments", "jump_url", "created_at")
    return [{**dict(zip(columns, row)), "author_roles": json.loads(row[5]), "attachments": json.loads(row[7])} for row in rows]


def message_post(message, source_group: str) -> dict:
    author = message.author
    return {
        "message_id": str(message.id),
        "channel_id": str(message.channel.id),
        "source_group": source_group,
        "author_id": str(author.id),
        "author_name": getattr(author, "display_name", str(author)),
        "author_roles": [role.name for role in getattr(author, "roles", []) if role.name != "@everyone"],
        "content": message.content,
        "attachments": [{"name": attachment.filename, "url": attachment.url} for attachment in message.attachments],
        "jump_url": message.jump_url,
        "created_at": message.created_at.isoformat(),
    }


async def ingest_history(channel, source_group: str, limit: int) -> list[dict]:
    return [message_post(message, source_group) async for message in channel.history(limit=limit, oldest_first=True)]
