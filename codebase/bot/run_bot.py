import os

from companion_discord.bot import create_bot


token = os.environ.get("DISCORD_TOKEN")
if not token:
    raise SystemExit("Set DISCORD_TOKEN in codebase/bot/.env first.")
create_bot().run(token)
