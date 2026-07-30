# Companion Discord Bot

The source Cohort server is read only through the existing authenticated Edge/CDP browser-session collector. It uses configured Discord channel URLs only; it does not use a Bot API, user token, self-bot, or channel discovery.

The Discord Bot API is destination-only: it creates, deletes, and replays managed resources in `DESTINATION_GUILD_ID` after an approved dry-run.

## Clone workflow

1. Keep the logged-in Edge session running at the configured local CDP URL.
2. Fill the two exact `sources` URLs in root `config.yaml`. Do not substitute a similarly named channel.
3. Run the browser collector. It preserves existing JSON files, checkpoints each target, and atomically refreshes `data/discord_crawl/manifest.json`.

```powershell
uv run --no-project --with-requirements requirements.txt python codebase/bot/run_crawl.py --config config.yaml
```

4. Inspect `data/discord_crawl/manifest.json`, then set only `DISCORD_TOKEN` and `DESTINATION_GUILD_ID` in `codebase/bot/.env`.
   To reuse pre-existing destination channels, configure their exact IDs under `discord_bot.destination_channel_mappings`; the rebuild validates guild/type/send permission and never falls back to a name match.
5. Check the destination-only plan. This does not change Discord.

```powershell
uv run --no-project --with-requirements codebase/bot/requirements.txt python codebase/bot/run_rebuild.py --dry-run --config config.yaml
```

6. Only after approving that plan, run apply with both destination confirmations:

```powershell
uv run --no-project --with-requirements codebase/bot/requirements.txt python codebase/bot/run_rebuild.py --config config.yaml --apply `
  --destination-guild-id <DESTINATION_GUILD_ID> `
  --confirm-destination-guild-id <DESTINATION_GUILD_ID>
```

`managed_categories`, `managed_channels`, and Bot-created IDs are the default deletion scope. `preserve_channels` and Discord system channels are never planned for deletion. `--replace-all-destination-channels` additionally requires `--confirm-replace-all`.

The state file maps `categories`, `channels`, `threads`, and `messages` incrementally, so resumed applies skip completed work. All replayed messages use disabled mentions. Attachment files are not downloaded or uploaded; their filename and original URL are replayed.

`replay.visual_fidelity: true` keeps source plaintext and URLs without injecting author/timestamp metadata. Discord performs native URL unfurls when available; custom embeds are sent only for source embeds that are independent of a plaintext URL.

Discord creates new message IDs and timestamps, original authors cannot be impersonated, Community-dependent channel types may fall back to text channels, and older attachment URLs may expire.
