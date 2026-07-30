# Companion Discord Bot

The bot uses the official Discord Bot API to ingest the explicit channel IDs in `sources.yaml` into local SQLite storage and expose the Companion slash commands.

```powershell
Copy-Item .env.example .env
Copy-Item sources.example.yaml sources.yaml
uv run --no-project --with-requirements requirements.txt python run_bot.py
uv run --no-project --with-requirements requirements.txt python run_ingest.py
```

Set `DISCORD_TOKEN`, `DISCORD_GUILD_ID`, `COMPANION_API_URL`, and the permitted channel IDs before running. The bot does not create, delete, or replay Discord channels or messages.
