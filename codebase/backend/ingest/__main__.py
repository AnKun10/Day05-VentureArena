import argparse
import time

from .agents import enrich_post, extract_schedule
from .config import Config
from .linker import detect_kind, detect_session
from .sources import SeedSource
from .store import Store


def _fallback_summary(content: str) -> str:
    sentences = content.replace("\n", " ").split(". ")
    return (". ".join(sentences[:2]))[:200]


def run_once(store: Store, source, cfg: Config, limit: int = 20,
             force: bool = False, runner=None, vectors=None, embed_fn=None,
             schedule_runner=None) -> dict:
    # CHÚ Ý: since hiện KHÔNG có key cho các kênh thong-bao — đó là lý do retry
    # bài extract lỗi vẫn hoạt động hôm nay (checkpoint thong-bao được lưu
    # nhưng không được dùng để lọc fetch). Nếu sau này thêm key thong-bao vào
    # since để tránh refetch thừa, PHẢI giữ nguyên cơ chế "không advance
    # checkpoint khi extract lỗi trong kênh đó" bên dưới, nếu không bài lỗi sẽ
    # không bao giờ được thử lại (checkpoint đã vượt qua message_id của nó).
    since = {ch: store.get_checkpoint(ch)
             for ch in ("chia-se", "bai-hoc", "tai-nguyen")}
    posts = source.fetch(since=since)
    schedule_events = 0
    failed_channels: set[str] = set()  # kênh thong-bao có ít nhất 1 lần extract lỗi trong lượt này
    for p in posts:
        if p.channel == "tai-nguyen":
            store.add_resource(p.message_id, detect_kind(p.title), p.title,
                               detect_session(p.title), p.author, p.jump_url,
                               p.created_at)
            store.set_checkpoint(p.channel, p.message_id)
        elif p.channel.startswith("thong-bao"):
            if not store.is_schedule_extracted(p.message_id):
                try:
                    post = {"message_id": p.message_id, "title": p.title,
                            "content": p.content, "channel": p.channel,
                            "created_at": p.created_at, "jump_url": p.jump_url}
                    extraction, trace_id = extract_schedule(post, cfg, runner=schedule_runner)
                    schedule_events += store.save_schedule_extraction(
                        p.message_id, [e.model_dump() for e in extraction.events], trace_id)
                except Exception as exc:  # extract lỗi: không mark, thử lại lượt sau
                    print(f"[schedule-fail] {p.message_id}: {exc}")
                    failed_channels.add(p.channel)
            # kênh này đã lỗi ở lượt này (bài này hoặc bài trước đó cùng kênh)
            # → không advance checkpoint, giữ nguyên khả năng thử lại lượt sau.
            if p.channel not in failed_channels:
                store.set_checkpoint(p.channel, p.message_id)
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

    embedded = 0
    if vectors is not None:
        from recsys import embed_texts as _default_embed, news_text
        embed = embed_fn or _default_embed
        rows = store.pending_embedding(force=force)
        if rows:
            try:
                vecs = embed([news_text(r) for r in rows], cfg)
                for r, vec in zip(rows, vecs):
                    vectors.upsert_news(r["message_id"], vec, {
                        "tags": r["tags"], "created_at": r["created_at"],
                        "hearts": r["hearts"], "comment_count": r["comment_count"]})
                    store.set_embedded(r["message_id"])
                    embedded += 1
            except Exception as exc:  # embed lỗi: không set_embedded, thử lại lượt sau
                print(f"[embed-fail] {exc}")
        for m in store.embedded_news_meta():
            vectors.update_news_payload(m["message_id"], m["hearts"], m["comment_count"])

    return {"fetched": len(posts), "enriched": enriched, "failed": failed,
            "embedded": embedded, "schedule_events": schedule_events}


def main():
    ap = argparse.ArgumentParser(prog="ingest")
    ap.add_argument("--source", choices=["seed", "discord", "manifest"], default="seed")
    ap.add_argument("--loop", type=int, default=0, help="phút giữa các lượt; 0 = 1 lượt")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--db", default=None)
    ap.add_argument("--seed", default="ingest/seeds/posts.json")
    ap.add_argument("--manifest",
                    default="../../data/discord_crawl_dataset_snapshot_2026-07-31/discord_crawl/manifest.json")
    args = ap.parse_args()

    cfg = Config.from_env()
    store = Store(args.db or cfg.db_path)
    try:
        from recsys import VectorStore
        vectors = VectorStore(cfg.qdrant_path)
    except Exception as exc:
        print(f"[recsys] qdrant busy/unavailable: {exc} (bỏ qua embed)")
        vectors = None
    if args.source == "seed":
        source = SeedSource(args.seed)
    elif args.source == "manifest":
        from .sources import ManifestSource
        source = ManifestSource(args.manifest)
    else:
        from .sources import DiscordSource  # Task 8
        source = DiscordSource(cfg.discord_token, cfg.channel_ids, cfg.guild_id)

    while True:
        stats = run_once(store, source, cfg, limit=args.limit, force=args.force,
                         vectors=vectors)
        print(f"[ingest] {stats}")
        if not args.loop:
            break
        args.force = False  # force chỉ áp dụng lượt đầu
        time.sleep(args.loop * 60)


if __name__ == "__main__":
    main()
