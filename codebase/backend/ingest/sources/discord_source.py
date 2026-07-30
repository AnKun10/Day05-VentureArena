import unicodedata

from ..models import RawComment, RawPost

_WANTED_CHANNELS = ("chia-se", "bai-hoc", "tai-nguyen")


def normalize_channel_name(name: str) -> str:
    s = unicodedata.normalize("NFD", name.lower()).replace("đ", "d")
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return "".join(ch for ch in s if ch.isalnum() or ch == "-")


def resolve_forum_channels(channels: list[tuple[int, str]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for cid, name in channels:
        norm = normalize_channel_name(name)
        for key in _WANTED_CHANNELS:
            if key in norm and key not in out:
                out[key] = str(cid)
    return out


def map_role(role_names: list[str]) -> str:
    joined = " ".join(role_names).lower()
    if "coach" in joined:
        return "Lab Coach"
    if "btc" in joined or "admin" in joined:
        return "BTC"
    if "mentor" in joined:
        return "Mentor"
    return "Học viên"


def thread_to_rawpost(thread_id, channel_key, title, starter_content, author_name,
                      role_names, jump_url, created_at_iso, hearts,
                      comment_tuples) -> RawPost:
    return RawPost(
        message_id=str(thread_id), channel=channel_key, title=title,
        content=starter_content, author=author_name,
        author_role=map_role(role_names), jump_url=jump_url,
        created_at=created_at_iso, hearts=hearts,
        comments=[RawComment(id=str(cid), author=a, author_role=map_role(r),
                             content=c, created_at=t)
                  for cid, a, r, c, t in comment_tuples],
    )


class DiscordSource:
    """Đọc forum channels qua discord.py: connect ngắn, fetch, rồi thoát.
    channel_ids rỗng + có guild_id → tự resolve 3 kênh theo tên.
    Cần bật MESSAGE CONTENT INTENT trong Discord Developer Portal."""

    def __init__(self, token: str, channel_ids: dict[str, str], guild_id: str = ""):
        self.token = token
        self.channel_ids = {k: v for k, v in channel_ids.items() if v}
        self.guild_id = guild_id

    def fetch(self, since: dict[str, int]) -> list[RawPost]:
        import asyncio
        import discord

        results: list[RawPost] = []
        intents = discord.Intents.default()
        intents.message_content = True
        client = discord.Client(intents=intents)

        @client.event
        async def on_ready():
            try:
                channel_ids = dict(self.channel_ids)
                if not channel_ids and self.guild_id:
                    guild = client.get_guild(int(self.guild_id)) or \
                        await client.fetch_guild(int(self.guild_id))
                    all_channels = await guild.fetch_channels()
                    forums = [(c.id, c.name) for c in all_channels
                              if isinstance(c, discord.ForumChannel)]
                    channel_ids = resolve_forum_channels(forums)
                    print(f"[discord] resolved channels: {channel_ids}")
                for key, cid in channel_ids.items():
                    channel = client.get_channel(int(cid)) or \
                        await client.fetch_channel(int(cid))
                    threads = list(channel.threads)
                    async for t in channel.archived_threads(limit=50):
                        threads.append(t)
                    for thread in threads:
                        if thread.id <= since.get(key, 0):
                            continue
                        try:
                            starter = await thread.fetch_message(thread.id)
                        except discord.NotFound:
                            continue
                        comments = []
                        async for m in thread.history(limit=50, oldest_first=True):
                            if m.id == thread.id or m.author.bot:
                                continue
                            roles = [r.name for r in getattr(m.author, "roles", [])]
                            comments.append((m.id, m.author.display_name, roles,
                                             m.content, m.created_at.isoformat()))
                        roles = [r.name for r in getattr(starter.author, "roles", [])]
                        hearts = sum(r.count for r in starter.reactions)
                        results.append(thread_to_rawpost(
                            thread.id, key, thread.name, starter.content,
                            starter.author.display_name, roles, starter.jump_url,
                            thread.created_at.isoformat(), hearts, comments))
            finally:
                await client.close()

        asyncio.run(client.start(self.token))
        return results
