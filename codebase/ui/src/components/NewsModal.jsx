import { ArrowUpRight, Heart, MessageSquare, Send, Sparkles } from "lucide-react";
import { ROLE_COLORS, tagOf } from "../data/mock.js";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export function Avatar({ name, role, className = "size-6 text-[11px]" }) {
  const color = ROLE_COLORS[role] ?? "#64748b";
  const initial = (name.split("—").pop() || name).trim()[0]?.toUpperCase() || "?";
  return (
    <span
      className={`flex shrink-0 items-center justify-center rounded-full font-semibold ${className}`}
      style={{ background: color + "1f", color }}
    >
      {initial}
    </span>
  );
}

export function TagBadge({ tag }) {
  const t = tagOf(tag);
  if (!t) return null;
  return (
    <Badge className="font-medium" style={{ background: t.color + "16", color: t.color }}>
      {t.label}
    </Badge>
  );
}

export default function NewsModal({ news: n, onClose }) {
  const roleColor = ROLE_COLORS[n.role] ?? "#64748b";
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-[640px]">
        <DialogHeader>
          <div className="flex flex-wrap items-center gap-1.5">
            {n.tags.map((tg) => (
              <TagBadge key={tg} tag={tg} />
            ))}
            <span className="ml-auto text-xs text-muted-foreground">{n.time}</span>
          </div>
          <DialogTitle className="text-lg leading-snug">{n.title}</DialogTitle>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Avatar name={n.author} role={n.role} />
            <span className="font-medium" style={{ color: roleColor }}>
              {n.author}
            </span>
            <Badge variant="outline" className="text-[10px]" style={{ color: roleColor }}>
              {n.role}
            </Badge>
            <span className="text-muted-foreground/50">·</span>
            <span className="font-mono">{n.channel}</span>
          </div>
        </DialogHeader>

        <img src={n.image} alt="" className="h-44 w-full rounded-lg border object-cover" />

        {/* Tóm tắt AI */}
        <div className="rounded-lg border border-primary/20 bg-primary/5 p-3">
          <div className="mb-1 flex items-center gap-1.5 text-[11px] font-semibold tracking-wider text-primary uppercase">
            <Sparkles className="size-3.5" /> Tóm tắt bởi AI
          </div>
          <p className="text-sm leading-relaxed">{n.aiSummary}</p>
        </div>

        {/* Nội dung gốc */}
        <div className="space-y-3">
          {n.content.split("\n\n").map((p, i) => (
            <p key={i} className="text-sm leading-relaxed text-foreground/90">
              {p}
            </p>
          ))}
        </div>

        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <Heart className="size-4" /> <span className="font-mono">{n.hearts}</span>
          </span>
          <span className="flex items-center gap-1.5">
            <MessageSquare className="size-4" />{" "}
            <span className="font-mono">{n.comments.length}</span>
          </span>
          <Button
            variant="outline"
            size="sm"
            className="ml-auto"
            onClick={(e) => e.preventDefault()}
          >
            Mở trên Discord <ArrowUpRight data-icon="inline-end" />
          </Button>
        </div>

        <Separator />

        {/* Bình luận */}
        <div>
          <h3 className="mb-3 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
            Bình luận · {n.comments.length}
          </h3>
          <div className="space-y-3.5">
            {n.comments.map((c, i) => {
              const cColor = ROLE_COLORS[c.role] ?? "#64748b";
              return (
                <div key={i} className="flex gap-2.5">
                  <Avatar name={c.author} role={c.role} className="size-7 text-xs" />
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-1.5 text-xs">
                      <span className="font-medium" style={{ color: cColor }}>
                        {c.author}
                      </span>
                      <span className="text-muted-foreground/70">{c.time}</span>
                    </div>
                    <p className="mt-0.5 text-sm leading-relaxed">{c.text}</p>
                  </div>
                </div>
              );
            })}
            {n.comments.length === 0 && (
              <p className="text-sm text-muted-foreground">Chưa có bình luận nào.</p>
            )}
          </div>
          <div className="mt-4 flex gap-2">
            <Input disabled placeholder="Viết bình luận… (demo — đồng bộ với Discord khi nối backend)" />
            <Button size="icon" disabled aria-label="Gửi bình luận">
              <Send />
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
