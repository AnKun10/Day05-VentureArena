import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    db_path: str = "companion.db"
    enrich_model: str = "gpt-5-mini"
    openai_api_key: str = ""
    tavily_api_key: str = ""
    discord_token: str = ""
    guild_id: str = ""
    embed_model: str = "text-embedding-3-small"
    qdrant_path: str = "qdrant_data"
    channel_ids: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            db_path=os.getenv("COMPANION_DB", "companion.db"),
            enrich_model=os.getenv("ENRICH_MODEL", "gpt-5-mini"),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            tavily_api_key=os.getenv("TAVILY_API_KEY", ""),
            discord_token=os.getenv("DISCORD_TOKEN", ""),
            guild_id=os.getenv("DISCORD_GUILD_ID", ""),
            embed_model=os.getenv("EMBED_MODEL", "text-embedding-3-small"),
            qdrant_path=os.getenv("QDRANT_PATH", "qdrant_data"),
            channel_ids={
                "chia-se": os.getenv("DISCORD_CHANNEL_CHIA_SE", ""),
                "bai-hoc": os.getenv("DISCORD_CHANNEL_BAI_HOC", ""),
                "tai-nguyen": os.getenv("DISCORD_CHANNEL_TAI_NGUYEN", ""),
            },
        )
