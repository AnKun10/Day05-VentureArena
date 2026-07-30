import { useMemo, useState } from "react";
import { Bookmark, Flame, Heart, Inbox, MessageSquare, Sparkles } from "lucide-react";
import { NEWS, NEWS_TAGS, ROLE_COLORS, isHot } from "../data/mock.js";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import NewsModal, { Avatar, TagBadge, TAG_ICONS } from "../components/NewsModal.jsx";

export default function NewsPage() {
  const [tag, setTag] = useState("all");
  const [selected, setSelected] = useState(null);
  const [bookmarks, setBookmarks] = useState(() => new Set());

  const toggleBookmark = (id) =>
    setBookmarks((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const hot = useMemo(
    () =>
      [...NEWS]
        .filter(isHot)
        .sort((a, b) => b.hearts + b.comments.length - (a.hearts + a.comments.length))
        .slice(0, 3),
    []
  );
  const feed = useMemo(
    () => NEWS.filter((n) => tag === "all" || n.tags.includes(tag)),
    [tag]
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

      {/* Hot trend */}
      <div className="mb-6">
        <h2 className="mb-2.5 flex items-center gap-1.5 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
          <Flame className="size-3.5 text-orange-500" /> Hot trend
        </h2>
        <div className="grid gap-2.5 sm:grid-cols-3">
          {hot.map((n) => {
            const roleColor = ROLE_COLORS[n.role] ?? "#64748b";
            return (
              <Card
                key={n.id}
                size="sm"
                className="cursor-pointer gap-2 transition-shadow hover:shadow-md"
                onClick={() => setSelected(n)}
              >
                <div className="flex items-center gap-1.5 px-3">
                  <TagBadge tag={n.tags[0]} />
                  <Flame className="ml-auto size-3.5 shrink-0 text-orange-500" />
                  <BookmarkButton
                    active={bookmarks.has(n.id)}
                    onToggle={() => toggleBookmark(n.id)}
                  />
                </div>
                <div className="line-clamp-2 min-h-10 px-3 text-sm leading-snug font-semibold">
                  {n.title}
                </div>
                <div className="flex items-center gap-1.5 px-3">
                  <Avatar name={n.author} role={n.role} className="size-4.5 text-[9px]" />
                  <span
                    className="truncate text-xs font-medium"
                    style={{ color: roleColor }}
                  >
                    {n.author}
                  </span>
                </div>
                <div className="mt-auto flex items-center gap-3 px-3 text-xs text-muted-foreground">
                  <Meta icon={Heart} value={n.hearts} />
                  <Meta icon={MessageSquare} value={n.comments.length} />
                  <span className="ml-auto truncate">{n.time}</span>
                </div>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Filter theo tag (taxonomy 10 tag — AI gắn, 1 bài có thể nhiều tag) */}
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

      {/* Feed */}
      <div className="space-y-3">
        {feed.map((n) => (
          <NewsCard
            key={n.id}
            n={n}
            bookmarked={bookmarks.has(n.id)}
            onBookmark={() => toggleBookmark(n.id)}
            onOpen={() => setSelected(n)}
          />
        ))}
        {feed.length === 0 && (
          <div className="flex flex-col items-center gap-2 py-16 text-muted-foreground">
            <Inbox className="size-8" />
            <p className="text-sm">Chưa có tin thuộc tag này.</p>
          </div>
        )}
      </div>

      {selected && <NewsModal news={selected} onClose={() => setSelected(null)} />}
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
      {/* Ảnh phủ kín góc trái block (production: AI lấy qua API tìm ảnh, vd Tavily) */}
      <img
        src={n.image}
        alt=""
        className="hidden w-40 shrink-0 self-stretch object-cover sm:block"
      />

      <div className="flex min-w-0 flex-1 flex-col gap-1.5 p-4">
        {/* Hàng trên: tags — time + bookmark */}
        <div className="flex items-start gap-1.5">
          <div className="flex flex-wrap items-center gap-1.5">
            {n.tags.map((tg) => (
              <TagBadge key={tg} tag={tg} />
            ))}
            {isHot(n) && <Flame className="size-3.5 text-orange-500" />}
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
          <Meta icon={MessageSquare} value={n.comments.length} />
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
