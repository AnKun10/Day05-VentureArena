import os
from ingest.config import Config


def test_from_env_defaults(monkeypatch):
    for k in ["COMPANION_DB", "ENRICH_MODEL", "OPENAI_API_KEY", "TAVILY_API_KEY",
              "DISCORD_TOKEN", "DISCORD_CHANNEL_CHIA_SE", "DISCORD_CHANNEL_BAI_HOC",
              "DISCORD_CHANNEL_TAI_NGUYEN"]:
        monkeypatch.delenv(k, raising=False)
    cfg = Config.from_env()
    assert cfg.db_path == "companion.db"
    assert cfg.enrich_model == "gpt-5-mini"
    assert cfg.channel_ids == {"chia-se": "", "bai-hoc": "", "tai-nguyen": ""}


def test_from_env_reads_values(monkeypatch):
    monkeypatch.setenv("COMPANION_DB", "x.db")
    monkeypatch.setenv("ENRICH_MODEL", "gpt-5")
    monkeypatch.setenv("DISCORD_CHANNEL_CHIA_SE", "111")
    monkeypatch.setenv("DISCORD_GUILD_ID", "999")
    cfg = Config.from_env()
    assert cfg.db_path == "x.db"
    assert cfg.enrich_model == "gpt-5"
    assert cfg.channel_ids["chia-se"] == "111"
    assert cfg.guild_id == "999"


def test_recsys_config_defaults(monkeypatch):
    monkeypatch.delenv("EMBED_MODEL", raising=False)
    monkeypatch.delenv("QDRANT_PATH", raising=False)
    cfg = Config.from_env()
    assert cfg.embed_model == "text-embedding-3-small"
    assert cfg.qdrant_path == "qdrant_data"


def test_recsys_config_reads_env(monkeypatch):
    monkeypatch.setenv("EMBED_MODEL", "text-embedding-3-large")
    monkeypatch.setenv("QDRANT_PATH", "x_data")
    cfg = Config.from_env()
    assert cfg.embed_model == "text-embedding-3-large"
    assert cfg.qdrant_path == "x_data"
