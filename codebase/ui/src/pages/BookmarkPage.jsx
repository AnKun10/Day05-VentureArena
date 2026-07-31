import { useEffect, useState } from "react";
import { Bookmark, BookmarkX, Heart, Inbox, MessageSquare } from "lucide-react";
import { ROLE_COLORS, tagOf, thumb } from "../data/mock.js";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import NewsModal, { Avatar, TagBadge } from "../components/NewsModal.jsx";

const CHANNEL_LABELS = { "chia-se": "#chia-sẻ", "bai-hoc": "#bài-học", "tai-nguyen": "#tài-nguyên" };

const relTime = (iso) => {
  if (!iso) return "";
  const mins = Math.max(0, (Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 60) return `${Math.round(mins)} phút trước`;
  if (mins < 1440) return `${Math.round(mins / 60)} giờ trước`;
  return `${Math.round(mins / 1440)} ngày trước`;
};

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

export default function BookmarkPage({ currentUser }) {
  const [items, setItems] = useState(null);      // null = đang tải / offline
  const [selected, setSelected] = useState(null);

  const load = () => {
    if (currentUser == null) return;
    api
      .bookmarksNews(currentUser)
      .then((list) => setItems(list.map(fromApi)))
      .catch(() => setItems([]));
  };

  useEffect(load, [currentUser]);

  const openDetail = (item) => {
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
      .catch(() => setSelected({ ...item, content: item.aiSummary || "", comments: [] }));
  };

  const removeBookmark = (id) => {
    if (currentUser == null) return;
    setItems((prev) => (prev || []).filter((n) => n.id !== id));   // optimistic
    api.setBookmark(currentUser, id, false).catch(load);           // lỗi → tải lại
  };

  return (
    <div className="mx-auto max-w-4xl px-6 py-6">
      <div className="mb-5">
        <h1 className="font-heading flex items-center gap-2 text-lg font-semibold">
          <Bookmark className="size-5 text-primary" /> Bản tin đã lưu
        </h1>
        <p className="text-xs text-muted-foreground">Các bản tin bạn đã bookmark — chỉ hiển thị của riêng bạn.</p>
      </div>

      {!items || items.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed py-16 text-muted-foreground">
          <Inbox className="size-8" />
          <p className="text-sm">Chưa có bản tin nào được lưu. Bấm biểu tượng bookmark ở trang Bản tin để lưu.</p>
        </div>
      ) : (
        <div className="grid gap-2.5 sm:grid-cols-2">
          {items.map((n) => {
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
                  <button
                    className="ml-auto text-primary transition-colors hover:text-destructive"
                    title="Bỏ lưu"
                    onClick={(e) => {
                      e.stopPropagation();
                      removeBookmark(n.id);
                    }}
                  >
                    <BookmarkX className="size-4" />
                  </button>
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
                  <span className="flex items-center gap-1">
                    <Heart className="size-3.5" /> {n.hearts ?? 0}
                  </span>
                  <span className="flex items-center gap-1">
                    <MessageSquare className="size-3.5" /> {n.commentCount ?? 0}
                  </span>
                  <span className="ml-auto truncate">{n.time}</span>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {selected && <NewsModal news={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
