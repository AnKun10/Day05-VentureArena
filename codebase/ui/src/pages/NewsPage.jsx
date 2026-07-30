import { useEffect, useMemo, useState } from "react";
import { Bookmark, Flame, Heart, Inbox, MessageSquare, Sparkles } from "lucide-react";
import { NEWS, NEWS_TAGS, ROLE_COLORS, isHot } from "../data/mock.js";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import NewsModal, { Avatar, TagBadge, TAG_ICONS } from "../components/NewsModal.jsx";

export default function NewsPage() {
  const [tag, setTag] = useState("all");
  const [selected, setSelected] = useState(null);
  const [bookmarks, setBookmarks] = useState(() => new Set());

  // Trạng thái phần "Dành cho bạn" (nối backend recommendations)
  const [users, setUsers] = useState(null);
  const [selectedUser, setSelectedUser] = useState(null);
  const [recs, setRecs] = useState(null);
  const [bioDraft, setBioDraft] = useState("");
  const [bioOpen, setBioOpen] = useState(false);

  const toggleBookmark = (id) =>
    setBookmarks((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  // Mount: nạp danh sách user demo. Lỗi (backend chưa chạy) → users=null (chế độ offline: giữ Hot trend mock).
  useEffect(() => {
    api
      .users()
      .then((list) => {
        setUsers(list);
        if (list.length) setSelectedUser(list[0].user_id);
      })
      .catch(() => setUsers(null));
  }, []);

  const fetchRecs = (uid) => {
    if (uid == null) return;
    api
      .recommendations(uid, 6)
      .then((list) => setRecs(list))
      .catch(() => setRecs(null));
  };

  // Đổi user → nạp lại gợi ý
  useEffect(() => {
    if (selectedUser != null) fetchRecs(selectedUser);
  }, [selectedUser]);

  const currentUser = users?.find((u) => u.user_id === selectedUser) ?? null;

  const openBio = () => {
    setBioDraft(currentUser?.bio ?? "");
    setBioOpen(true);
  };

  const saveBio = () => {
    if (selectedUser == null) return;
    api
      .setBio(selectedUser, bioDraft)
      .then(() => {
        setUsers((prev) =>
          prev ? prev.map((u) => (u.user_id === selectedUser ? { ...u, bio: bioDraft } : u)) : prev
        );
        setBioOpen(false);
        fetchRecs(selectedUser);
      })
      .catch(() => {});
  };

  // Rec card chỉ mở modal nếu tìm được bài mock cùng title (dữ liệu API chưa có content/comments đầy đủ)
  const findMockByTitle = (title) => NEWS.find((n) => n.title === title);

  const handleRecBookmark = (messageId) => {
    if (selectedUser == null) return;
    api
      .setBookmark(selectedUser, messageId, true)
      .then(() => fetchRecs(selectedUser))
      .catch(() => {});
  };

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
                value={selectedUser ?? ""}
                onChange={(e) => setSelectedUser(e.target.value)}
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
            <div className="grid gap-2.5 sm:grid-cols-3">
              {(recs ?? []).slice(0, 3).map((r) => {
                const roleColor = ROLE_COLORS[r.author_role] ?? "#64748b";
                const mockMatch = findMockByTitle(r.title);
                return (
                  <Card
                    key={r.message_id}
                    size="sm"
                    className={cn(
                      "gap-2 transition-shadow hover:shadow-md",
                      mockMatch && "cursor-pointer"
                    )}
                    onClick={mockMatch ? () => setSelected(mockMatch) : undefined}
                  >
                    <div className="flex items-center gap-1.5 px-3">
                      <TagBadge tag={r.tags[0]} />
                      <div className="ml-auto">
                        <BookmarkButton
                          active={false}
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
              {recs !== null && recs.length === 0 && (
                <p className="col-span-full text-sm text-muted-foreground">
                  Chưa có gợi ý nào — hãy thử đánh dấu vài bài viết bạn quan tâm.
                </p>
              )}
            </div>
          </>
        ) : (
          <>
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
          </>
        )}
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

      <Dialog open={bioOpen} onOpenChange={setBioOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Sửa bio — {currentUser?.name}</DialogTitle>
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
