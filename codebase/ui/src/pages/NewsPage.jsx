import { useMemo, useState } from "react";
import { ArrowUpRight, Clock3, Flame, Heart, Inbox, MessageSquare } from "lucide-react";
import { NEWS, NEWS_CATEGORIES, isHot } from "../data/mock.js";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const catOf = (id) => NEWS_CATEGORIES.find((c) => c.id === id);

export default function NewsPage() {
  const [cat, setCat] = useState("all");

  const hot = useMemo(
    () =>
      [...NEWS]
        .filter(isHot)
        .sort((a, b) => b.hearts + b.comments - (a.hearts + a.comments))
        .slice(0, 4),
    []
  );
  const feed = useMemo(() => NEWS.filter((n) => cat === "all" || n.cat === cat), [cat]);

  return (
    <div className="mx-auto max-w-4xl px-6 py-6">
      <div className="mb-5">
        <h1 className="font-heading text-lg font-semibold">Bản tin cộng đồng</h1>
        <p className="text-xs text-muted-foreground">
          Tổng hợp từ các kênh Discord của khoá, phân loại theo loại tin{" "}
          <span className="text-muted-foreground/60">(taxonomy demo — nhóm chốt bộ loại tin sau)</span>
        </p>
      </div>

      {/* Hot trend */}
      <div className="mb-6">
        <h2 className="mb-2.5 flex items-center gap-1.5 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
          <Flame className="size-3.5 text-orange-400" /> Hot trend
        </h2>
        <div className="grid gap-2.5 sm:grid-cols-2">
          {hot.map((n) => {
            const c = catOf(n.cat);
            return (
              <Card
                key={n.id}
                size="sm"
                className="cursor-pointer gap-2 transition-colors hover:ring-foreground/20"
              >
                <div className="flex items-center gap-2 px-3">
                  <CatBadge c={c} />
                  <span className="font-mono text-[10px] text-muted-foreground">{n.channel}</span>
                  <Flame className="ml-auto size-3.5 text-orange-400" />
                </div>
                <div className="line-clamp-2 px-3 text-sm leading-snug font-medium">{n.title}</div>
                <div className="flex items-center gap-3 px-3 text-xs text-muted-foreground">
                  <Meta icon={Heart} value={n.hearts} />
                  <Meta icon={MessageSquare} value={n.comments} />
                  <span className="ml-auto">{n.time}</span>
                </div>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Filter chips */}
      <div className="mb-4 flex flex-wrap gap-1.5">
        <CatChip active={cat === "all"} onClick={() => setCat("all")} label="Tất cả" />
        {NEWS_CATEGORIES.map((c) => (
          <CatChip
            key={c.id}
            active={cat === c.id}
            onClick={() => setCat(c.id)}
            label={c.label}
            color={c.color}
          />
        ))}
      </div>

      {/* Feed */}
      <div className="space-y-2.5">
        {feed.map((n) => {
          const c = catOf(n.cat);
          return (
            <Card key={n.id} size="sm" className="gap-1.5 transition-colors hover:ring-foreground/20">
              <div className="flex flex-wrap items-center gap-2 px-3">
                <CatBadge c={c} />
                {n.open && (
                  <Badge variant="outline" className="gap-1 text-sky-400">
                    <Clock3 /> Chờ TA trả lời
                  </Badge>
                )}
                {isHot(n) && <Flame className="size-3.5 text-orange-400" />}
                <span className="ml-auto text-xs text-muted-foreground">{n.time}</span>
              </div>
              <div className="px-3 text-sm font-medium">{n.title}</div>
              <p className="line-clamp-2 px-3 text-xs leading-relaxed text-muted-foreground">
                {n.summary}
              </p>
              <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 px-3 text-xs text-muted-foreground">
                <span className="font-medium text-foreground/80">{n.author}</span>
                <RoleBadge role={n.role} />
                <span className="text-muted-foreground/40">·</span>
                <span className="font-mono">{n.channel}</span>
                <span className="text-muted-foreground/40">·</span>
                <Meta icon={Heart} value={n.hearts} />
                <Meta icon={MessageSquare} value={n.comments} />
                <Button
                  variant="link"
                  size="xs"
                  className="ml-auto"
                  onClick={(e) => e.preventDefault()}
                >
                  Mở trên Discord <ArrowUpRight data-icon="inline-end" />
                </Button>
              </div>
            </Card>
          );
        })}
        {feed.length === 0 && (
          <div className="flex flex-col items-center gap-2 py-16 text-muted-foreground">
            <Inbox className="size-8" />
            <p className="text-sm">Chưa có tin thuộc loại này.</p>
          </div>
        )}
      </div>
    </div>
  );
}

function Meta({ icon: Icon, value }) {
  return (
    <span className="flex items-center gap-1">
      <Icon className="size-3" />
      <span className="font-mono">{value}</span>
    </span>
  );
}

function CatBadge({ c }) {
  return (
    <Badge className="font-medium" style={{ background: c.color + "22", color: c.color }}>
      {c.label}
    </Badge>
  );
}

function RoleBadge({ role }) {
  const isStaff = role !== "Học viên";
  return (
    <Badge variant="outline" className={cn("text-[10px]", isStaff && "text-emerald-400")}>
      {role}
    </Badge>
  );
}

function CatChip({ active, onClick, label, color }) {
  return (
    <Button
      variant={active ? "secondary" : "outline"}
      size="sm"
      onClick={onClick}
      className={cn(!active && "text-muted-foreground")}
    >
      {color && <span className="size-2 rounded-full" style={{ background: color }} />}
      {label}
    </Button>
  );
}
