import argparse
import time

from .agents import enrich_post
from .config import Config
from .linker import detect_kind, detect_session
from .sources import SeedSource
from .store import Store


def _fallback_summary(content: str) -> str:
    sentences = content.replace("\n", " ").split(". ")
    return (". ".join(sentences[:2]))[:200]


def run_once(store: Store, source, cfg: Config, limit: int = 20,
             force: bool = False, runner=None) -> dict:
    since = {ch: store.get_checkpoint(ch)
             for ch in ("chia-se", "bai-hoc", "tai-nguyen")}
    posts = source.fetch(since=since)
    for p in posts:
        if p.channel == "tai-nguyen":
            store.add_resource(p.message_id, detect_kind(p.title), p.title,
                               detect_session(p.title), p.author, p.jump_url,
                               p.created_at)
        else:
            store.upsert_post(p)
        store.set_checkpoint(p.channel, p.message_id)

    enriched = failed = 0
    for row in store.pending_enrichment(limit=limit, force=force):
        try:
            e, image_source, trace_id = enrich_post(row, cfg, runner=runner)
            store.save_enrichment(row["message_id"], e, image_source,
                                  prompt_version="v1", trace_id=trace_id)
            enriched += 1
        except Exception as exc:  # enrich lỗi: fallback, không dừng lượt chạy
            print(f"[enrich-fail] {row['message_id']}: {exc}")
            store.mark_enrich_failed(row["message_id"],
                                     _fallback_summary(row["content"]))
            failed += 1
    return {"fetched": len(posts), "enriched": enriched, "failed": failed}


def main():
    ap = argparse.ArgumentParser(prog="ingest")
    ap.add_argument("--source", choices=["seed", "discord"], default="seed")
    ap.add_argument("--loop", type=int, default=0, help="phút giữa các lượt; 0 = 1 lượt")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--db", default=None)
    ap.add_argument("--seed", default="ingest/seeds/posts.json")
    args = ap.parse_args()

    cfg = Config.from_env()
    store = Store(args.db or cfg.db_path)
    if args.source == "seed":
        source = SeedSource(args.seed)
    else:
        from .sources import DiscordSource  # Task 8
        source = DiscordSource(cfg.discord_token, cfg.channel_ids, cfg.guild_id)

    while True:
        stats = run_once(store, source, cfg, limit=args.limit, force=args.force)
        print(f"[ingest] {stats}")
        if not args.loop:
            break
        args.force = False  # force chỉ áp dụng lượt đầu
        time.sleep(args.loop * 60)


if __name__ == "__main__":
    main()
