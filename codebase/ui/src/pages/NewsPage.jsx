import { useEffect, useMemo, useRef, useState } from "react";
import { Bookmark, ExternalLink, Flame, Heart, Inbox, Loader2, MessageSquare, Newspaper, Search, Sparkles } from "lucide-react";
import { NEWS, NEWS_TAGS, ROLE_COLORS, isHot, tagOf, thumb } from "../data/mock.js";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import NewsModal, { Avatar, TagBadge, TAG_ICONS } from "../components/NewsModal.jsx";

const CHANNEL_LABELS = { "chia-se": "#chia-sẻ", "bai-hoc": "#bài-học", "tai-nguyen": "#tài-nguyên" };

const relTime = (iso) => {
  if (!iso) return "";
  const mins = Math.max(0, (Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 60) return `${Math.round(mins)} phút trước`;
  if (mins < 1440) return `${Math.round(mins / 60)} giờ trước`;
  return `${Math.round(mins / 1440)} ngày trước`;
};

// Chuẩn hoá bài từ API (/api/news, /api/recommendations) về shape UI dùng chung với mock
const fromApi = (n) => {
  const tags = n.tags?.length ? n.tags : ["other"];
  return {
    ...n,
    id: n.message_id,
    aiSummary: n.summary || "",
    tags,
    image: n.image_url || thumb(tagOf(tags[0])?.color ?? "#64748b", "📰"),
    author: n.author || "(ẩn danh)",
    role: n.author_role || "Học viên",
    channel: CHANNEL_LABELS[n.channel] ?? n.channel,
    commentCount: n.comment_count ?? 0,
    time: relTime(n.created_at),
    url: n.jump_url || "#",
  };
};

export default function NewsPage({ users, currentUser, onSelectUser, refreshUsers }) {
  const [tag, setTag] = useState("all");
  const [selected, setSelected] = useState(null);
  const [bookmarks, setBookmarks] = useState(() => new Set());

  // Trạng thái phần "Dành cho bạn" (nối backend recommendations)
  const [recs, setRecs] = useState(null);
  // Daily AI News (undefined=đang tải, []=chưa có, [...]=danh sách)
  const [aiNews, setAiNews] = useState(undefined);
  const aiSeq = useRef(0);
  const [searchQ, setSearchQ] = useState("");
  const [searchResults, setSearchResults] = useState(null);
  const [bioDraft, setBioDraft] = useState("");
  const [bioOpen, setBioOpen] = useState(false);
  const recSeq = useRef(0);

  const toggleBookmark = (id) =>
    setBookmarks((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  // Feed bản tin từ backend (data thật đã ingest+enrich); lỗi → null (offline, dùng mock)
  const [apiNews, setApiNews] = useState(null);

  // Mount: nạp bản tin thật. Lỗi (backend chưa chạy) → chế độ offline với mock.
  useEffect(() => {
    api
      .news()
      .then((list) => setApiNews(list.map(fromApi)))
      .catch(() => setApiNews(null));
  }, []);

  // Mở modal chi tiết: online lấy content + comments thật; offline dùng object mock sẵn có
  const openDetail = (item) => {
    if (apiNews === null || item.message_id == null) {
      setSelected(item);
      return;
    }
    api
      .newsDetail(item.message_id)
      .then((d) =>
        setSelected({
          ...fromApi(d),
          content: d.content || "",
          comments: (d.comments || []).map((c) => ({
            author: c.author || "(ẩn danh)",
            role: c.author_role || "Học viên",
            time: relTime(c.created_at),
            text: c.content,
          })),
        })
      )
      .catch(() =>
        setSelected({ ...item, content: item.content || item.aiSummary || "", comments: item.comments || [] })
      );
  };

  const fetchRecs = (uid) => {
    if (uid == null) return;
    const seq = ++recSeq.current;
    api
      .recommendations(uid, 6)
      .then((list) => {
        if (seq === recSeq.current) setRecs(list);
      })
      .catch(() => {
        if (seq === recSeq.current) setRecs(null);
      });
  };

  // Đổi user → nạp lại gợi ý
  useEffect(() => {
    if (currentUser != null) fetchRecs(currentUser);
  }, [currentUser]);

  // Đổi user → nạp Daily AI News (lần đầu trong ngày có thể mất ~15-25s ở backend)
  useEffect(() => {
    if (currentUser == null) return;
    const seq = ++aiSeq.current;
    setAiNews(undefined);
    api
      .aiNews(currentUser)
      .then((res) => {
        if (seq === aiSeq.current) setAiNews(res.items || []);
      })
      .catch(() => {
        if (seq === aiSeq.current) setAiNews([]);
      });
  }, [currentUser]);

  const currentUserObj = users?.find((u) => u.user_id === currentUser) ?? null;

  const openBio = () => {
    setBioDraft(currentUserObj?.bio ?? "");
    setBioOpen(true);
  };

  const saveBio = () => {
    if (currentUser == null) return;
    api
      .setBio(currentUser, bioDraft)
      .then(() => {
        setBioOpen(false);
        fetchRecs(currentUser);
        refreshUsers?.();
      })
      .catch(() => {});
  };

  const handleRecBookmark = (messageId) => {
    if (currentUser == null) return;
    api
      .setBookmark(currentUser, messageId, true)
      .then(() => {
        setBookmarks((prev) => new Set(prev).add(messageId));
        fetchRecs(currentUser);
      })
      .catch(() => {});
  };

  // Bookmark trên feed: online + có user → sync API rồi refetch gợi ý; offline → local
  const handleFeedBookmark = (id) => {
    const on = !bookmarks.has(id);
    toggleBookmark(id);
    if (apiNews !== null && currentUser != null) {
      api
        .setBookmark(currentUser, id, on)
        .then(() => fetchRecs(currentUser))
        .catch(() => {});
    }
  };

  // Đổi user → đồng bộ lại danh sách bookmark từ server
  useEffect(() => {
    if (currentUser == null || apiNews === null) return;
    api
      .bookmarks(currentUser)
      .then((ids) => setBookmarks(new Set(ids)))
      .catch(() => {});
  }, [currentUser, apiNews]);

  const sourceNews = apiNews ?? NEWS;
  const hot = useMemo(
    () =>
      [...sourceNews]
        .sort(
          (a, b) =>
            b.hearts + (b.commentCount ?? b.comments.length) -
            (a.hearts + (a.commentCount ?? a.comments.length))
        )
        .slice(0, 3),
    [sourceNews]
  );
  const feed = useMemo(
    () => sourceNews.filter((n) => tag === "all" || n.tags.includes(tag)),
    [sourceNews, tag]
  );

  // Tìm kiếm cộng đồng: hybrid (lexical + semantic) RRF ở backend theo heading +
  // tóm tắt (KHÔNG dùng comment). Debounce 350ms; lỗi/offline → lọc client.
  useEffect(() => {
    const q = searchQ.trim();
    if (!q) {
      setSearchResults(null);
      return;
    }
    const t = setTimeout(() => {
      api
        .newsSearch(q, 20)
        .then((list) => setSearchResults(list.map(fromApi)))
        .catch(() =>
          setSearchResults(
            sourceNews.filter((n) =>
              `${n.title} ${n.aiSummary || ""}`.toLowerCase().includes(q.toLowerCase())
            )
          )
        );
    }, 350);
    return () => clearTimeout(t);
  }, [searchQ, sourceNews]);

  const displayFeed = searchResults ?? feed;

  const renderHotCards = () => (
    <div className="grid gap-2.5 sm:grid-cols-3">
      {hot.map((n) => {
        const roleColor = ROLE_COLORS[n.role] ?? "#64748b";
        return (
          <Card
            key={n.id}
            size="sm"
            className="cursor-pointer gap-2 transition-shadow hover:shadow-md"
            onClick={() => openDetail(n)}
          >
            <div className="flex items-center gap-1.5 px-3">
              <TagBadge tag={n.tags[0]} />
              <Flame className="ml-auto size-3.5 shrink-0 text-orange-500" />
              <BookmarkButton
                active={bookmarks.has(n.id)}
                onToggle={() => handleFeedBookmark(n.id)}
              />
            </div>
            <div className="line-clamp-2 min-h-10 px-3 text-sm leading-snug font-semibold">
              {n.title}
            </div>
            <div className="flex items-center gap-1.5 px-3">
              <Avatar name={n.author} role={n.role} className="size-4.5 text-[9px]" />
              <span className="truncate text-xs font-medium" style={{ color: roleColor }}>
                {n.author}
              </span>
            </div>
            <div className="mt-auto flex items-center gap-3 px-3 text-xs text-muted-foreground">
              <Meta icon={Heart} value={n.hearts} />
              <Meta icon={MessageSquare} value={n.commentCount ?? n.comments.length} />
              <span className="ml-auto truncate">{n.time}</span>
            </div>
          </Card>
        );
      })}
    </div>
  );

  return (
    <div className="mx-auto max-w-4xl px-6 py-6">
      <div className="mb-5">
        <h1 className="font-heading text-lg font-semibold">Bản tin cộng đồng</h1>
        <p className="text-xs text-muted-foreground">
          AI tổng hợp từ kênh <span className="font-mono">#chia-sẻ</span> ·{" "}
          <span className="font-mono">#bài-học</span> — tóm tắt, gắn tag và tìm ảnh minh hoạ tự động
        </p>
      </div>

      {/* Hot trend (offline) / Dành cho bạn (online, nối recommendations API) */}
      <div className="mb-6">
        {users !== null ? (
          <>
            <div className="mb-2.5 flex items-center gap-2">
              <h2 className="flex items-center gap-1.5 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
                <Sparkles className="size-3.5 text-primary" /> Dành cho bạn
              </h2>
              <select
                className="h-8 rounded-lg border bg-background px-2 text-sm"
                value={currentUser ?? ""}
                onChange={(e) => onSelectUser(e.target.value)}
              >
                {users.map((u) => (
                  <option key={u.user_id} value={u.user_id}>
                    {u.name}
                  </option>
                ))}
              </select>
              <Button variant="outline" size="sm" onClick={openBio}>
                Sửa bio
              </Button>
            </div>
            {recs === null ? (
              <>
                <p className="mb-2 text-[11px] text-muted-foreground">
                  Gợi ý cá nhân tạm thời không khả dụng — đang hiển thị hot trend.
                </p>
                {renderHotCards()}
              </>
            ) : (
              <div className="grid gap-2.5 sm:grid-cols-3">
                {recs.slice(0, 6).map((r) => {
                  const roleColor = ROLE_COLORS[r.author_role] ?? "#64748b";
                  return (
                    <Card
                      key={r.message_id}
                      size="sm"
                      className="cursor-pointer gap-2 transition-shadow hover:shadow-md"
                      onClick={() => openDetail(r)}
                    >
                      <div className="flex items-center gap-1.5 px-3">
                        <TagBadge tag={r.tags[0]} />
                        <div className="ml-auto">
                          <BookmarkButton
                            active={bookmarks.has(r.message_id)}
                            onToggle={() => handleRecBookmark(r.message_id)}
                          />
                        </div>
                      </div>
                      <div className="line-clamp-2 min-h-10 px-3 text-sm leading-snug font-semibold">
                        {r.title}
                      </div>
                      <div className="flex items-center gap-1.5 px-3">
                        <Avatar name={r.author} role={r.author_role} className="size-4.5 text-[9px]" />
                        <span
                          className="truncate text-xs font-medium"
                          style={{ color: roleColor }}
                        >
                          {r.author}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 px-3 text-xs text-muted-foreground">
                        <Meta icon={Heart} value={r.hearts} />
                        <Meta icon={MessageSquare} value={r.comment_count} />
                      </div>
                      <div className="mt-auto px-3 text-[10px] text-muted-foreground">
                        ✨ {Math.round(r.parts.sim * 100)}% match · 🔥{" "}
                        {r.hearts + r.comment_count} · 🕐 {Math.round(r.parts.rec * 100)}% mới
                      </div>
                    </Card>
                  );
                })}
                {recs.length === 0 && (
                  <p className="col-span-full text-sm text-muted-foreground">
                    Chưa có gợi ý nào — hãy thử đánh dấu vài bài viết bạn quan tâm.
                  </p>
                )}
              </div>
            )}
          </>
        ) : (
          <>
            <h2 className="mb-2.5 flex items-center gap-1.5 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
              <Flame className="size-3.5 text-orange-500" /> Hot trend
            </h2>
            {renderHotCards()}
          </>
        )}
      </div>

      {/* Daily AI News cho bạn — AI crawl + verify nguồn, cập nhật mỗi ngày */}
      {currentUser != null && (
        <div className="mb-6">
          <h2 className="mb-1 flex items-center gap-1.5 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
            <Newspaper className="size-3.5 text-primary" /> Daily AI News cho bạn
          </h2>
          <p className="mb-2.5 text-[11px] text-muted-foreground">
            AI crawl &amp; xác minh nguồn tin AI mới theo sở thích của bạn · cập nhật mỗi ngày 1 lần
          </p>
          {aiNews === undefined ? (
            <div className="flex items-center gap-2 rounded-lg border bg-card/50 px-4 py-6 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" /> Đang tổng hợp tin AI cho bạn…
            </div>
          ) : aiNews.length === 0 ? (
            <p className="rounded-lg border bg-card/50 px-4 py-6 text-sm text-muted-foreground">
              Chưa lấy được tin hôm nay — thử lại sau nhé.
            </p>
          ) : (
            <div className="grid gap-2.5 sm:grid-cols-3">
              {aiNews.map((a, i) => (
                <a
                  key={i}
                  href={a.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex flex-col gap-1.5 rounded-lg border bg-card p-3 transition-shadow hover:shadow-md"
                >
                  <div className="flex items-center gap-1.5 text-[10px] font-medium text-primary">
                    <Newspaper className="size-3 shrink-0" />
                    <span className="truncate">{a.source}</span>
                    <ExternalLink className="ml-auto size-3 shrink-0 text-muted-foreground" />
                  </div>
                  <div className="line-clamp-2 text-sm leading-snug font-semibold">{a.title}</div>
                  <div className="line-clamp-3 text-xs text-muted-foreground">{a.summary}</div>
                </a>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tìm kiếm cộng đồng — hybrid (lexical + semantic) RRF theo heading + tóm tắt */}
      <div className="relative mb-3">
        <Search className="absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground" />
        <input
          value={searchQ}
          onChange={(e) => setSearchQ(e.target.value)}
          placeholder="Tìm bài trong cộng đồng (hybrid search)…"
          className="h-9 w-full rounded-lg border bg-background pr-3 pl-8 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
        />
      </div>

      {searchResults === null ? (
        <div className="mb-4 flex flex-wrap gap-1.5">
          <TagChip active={tag === "all"} onClick={() => setTag("all")} label="Tất cả" />
          {NEWS_TAGS.map((t) => (
            <TagChip
              key={t.id}
              active={tag === t.id}
              onClick={() => setTag(t.id)}
              label={t.label}
              color={t.color}
              icon={TAG_ICONS[t.id]}
            />
          ))}
        </div>
      ) : (
        <p className="mb-3 text-[11px] text-muted-foreground">
          Kết quả tìm kiếm cho{" "}
          <span className="font-medium text-foreground">“{searchQ}”</span> · {displayFeed.length} bài
          (hybrid + RRF)
        </p>
      )}

      {/* Feed */}
      <div className="space-y-3">
        {displayFeed.map((n) => (
          <NewsCard
            key={n.id}
            n={n}
            bookmarked={bookmarks.has(n.id)}
            onBookmark={() => handleFeedBookmark(n.id)}
            onOpen={() => openDetail(n)}
          />
        ))}
        {displayFeed.length === 0 && (
          <div className="flex flex-col items-center gap-2 py-16 text-muted-foreground">
            <Inbox className="size-8" />
            <p className="text-sm">
              {searchResults !== null
                ? "Không tìm thấy bài nào phù hợp."
                : "Chưa có tin thuộc tag này."}
            </p>
          </div>
        )}
      </div>

      {selected && <NewsModal news={selected} onClose={() => setSelected(null)} />}

      <Dialog open={bioOpen} onOpenChange={setBioOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Sửa bio — {currentUserObj?.name}</DialogTitle>
          </DialogHeader>
          <textarea
            className="min-h-28 w-full rounded-lg border bg-background p-2 text-sm"
            value={bioDraft}
            onChange={(e) => setBioDraft(e.target.value)}
            placeholder="Mô tả sở thích, mối quan tâm của bạn…"
          />
          <Button size="sm" onClick={saveBio}>
            Lưu
          </Button>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function NewsCard({ n, bookmarked, onBookmark, onOpen }) {
  const roleColor = ROLE_COLORS[n.role] ?? "#64748b";
  return (
    <Card
      className="cursor-pointer flex-row gap-0 p-0 transition-shadow hover:shadow-md"
      onClick={onOpen}
    >
      {/* Ảnh phủ kín góc trái block (Tavily; host chặn hotlink → placeholder theo màu tag) */}
      <img
        src={n.image}
        alt=""
        className="hidden w-40 shrink-0 self-stretch object-cover sm:block"
        onError={(e) => {
          e.currentTarget.onerror = null;
          e.currentTarget.src = thumb(tagOf(n.tags[0])?.color ?? "#64748b", "📰");
        }}
      />

      <div className="flex min-w-0 flex-1 flex-col gap-1.5 p-4">
        {/* Hàng trên: tags — time + bookmark */}
        <div className="flex items-start gap-1.5">
          <div className="flex flex-wrap items-center gap-1.5">
            {n.tags.map((tg) => (
              <TagBadge key={tg} tag={tg} />
            ))}
            {(n.hot ?? isHot(n)) && <Flame className="size-3.5 text-orange-500" />}
          </div>
          <div className="ml-auto flex shrink-0 items-center gap-1 text-xs text-muted-foreground">
            <span>{n.time}</span>
            <BookmarkButton active={bookmarked} onToggle={onBookmark} />
          </div>
        </div>

        <h3 className="text-[15px] leading-snug font-semibold">{n.title}</h3>

        {/* Tóm tắt AI 1-3 câu */}
        <p className="line-clamp-2 text-sm leading-relaxed text-muted-foreground">
          <Sparkles className="mr-1 inline size-3.5 -translate-y-px text-primary/70" />
          {n.aiSummary}
        </p>

        {/* Hàng dưới: author chip màu role + kênh + tim/comment */}
        <div className="mt-auto flex flex-wrap items-center gap-x-2.5 gap-y-1 pt-1.5 text-xs text-muted-foreground">
          <span
            className="flex items-center gap-1.5 rounded-full border py-0.5 pr-2.5 pl-0.5"
            style={{ borderColor: roleColor + "55", background: roleColor + "0d" }}
          >
            <Avatar name={n.author} role={n.role} className="size-5 text-[10px]" />
            <span className="font-medium" style={{ color: roleColor }}>
              {n.author}
            </span>
          </span>
          <span className="font-mono">{n.channel}</span>
          <span className="text-muted-foreground/40">·</span>
          <Meta icon={Heart} value={n.hearts} />
          <Meta icon={MessageSquare} value={n.commentCount ?? n.comments.length} />
        </div>
      </div>
    </Card>
  );
}

function BookmarkButton({ active, onToggle }) {
  return (
    <Button
      variant="ghost"
      size="icon-sm"
      aria-label={active ? "Bỏ đánh dấu" : "Đánh dấu bài viết"}
      className={cn("shrink-0", active && "text-primary")}
      onClick={(e) => {
        e.stopPropagation();
        onToggle();
      }}
    >
      <Bookmark className={cn(active && "fill-current")} />
    </Button>
  );
}

function Meta({ icon: Icon, value }) {
  return (
    <span className="flex items-center gap-1">
      <Icon className="size-3.5" />
      <span className="font-mono">{value}</span>
    </span>
  );
}

function TagChip({ active, onClick, label, color, icon: Icon }) {
  return (
    <Button
      variant={active ? "secondary" : "outline"}
      size="sm"
      onClick={onClick}
      className={cn(!active && "text-muted-foreground")}
    >
      {Icon ? <Icon style={color ? { color } : undefined} /> : null}
      {label}
    </Button>
  );
}
