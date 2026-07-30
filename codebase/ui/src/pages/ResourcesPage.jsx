import { useMemo, useState } from "react";
import {
  Clapperboard,
  ExternalLink,
  FileText,
  Link2,
  Lock,
  Presentation,
  Search,
  SearchX,
} from "lucide-react";
import { RESOURCES, RESOURCE_KINDS, SESSION_TYPES } from "../data/mock.js";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const KIND_ICONS = {
  slide: Presentation,
  record: Clapperboard,
  doc: FileText,
  link: Link2,
};

const sessionColor = (code) => {
  if (!code) return "var(--muted-foreground)";
  const prefix = code.split("-")[0].toUpperCase();
  return SESSION_TYPES[prefix === "LAB" ? "LAB" : prefix]?.color ?? "var(--muted-foreground)";
};

export default function ResourcesPage() {
  const [kind, setKind] = useState("all");
  const [query, setQuery] = useState("");

  const filtered = useMemo(
    () =>
      RESOURCES.filter(
        (r) =>
          (kind === "all" || r.kind === kind) &&
          (query.trim() === "" ||
            (r.title + " " + (r.session || "")).toLowerCase().includes(query.toLowerCase()))
      ),
    [kind, query]
  );

  const bySession = filtered.filter((r) => r.session);
  const general = filtered.filter((r) => !r.session);

  return (
    <div className="mx-auto max-w-4xl px-6 py-6">
      <div className="mb-5">
        <h1 className="font-heading text-lg font-semibold">Tài nguyên</h1>
        <p className="text-xs text-muted-foreground">
          Slide, record, tài liệu từ kênh <span className="font-mono">#tài-nguyên</span> — tự động
          gắn vào buổi học tương ứng
        </p>
      </div>

      {/* Filters */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <div className="relative w-72">
          <Search className="absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Tìm theo tên hoặc mã buổi (VD: WS-2)…"
            className="pl-8"
          />
        </div>
        <div className="flex flex-wrap gap-1.5">
          <FilterChip active={kind === "all"} onClick={() => setKind("all")}>
            Tất cả
          </FilterChip>
          {Object.entries(RESOURCE_KINDS).map(([k, v]) => (
            <FilterChip key={k} active={kind === k} onClick={() => setKind(k)}>
              {v.label}
            </FilterChip>
          ))}
        </div>
      </div>

      <Section title="Gắn theo buổi học" count={bySession.length}>
        {bySession.map((r) => (
          <ResourceRow key={r.id} r={r} />
        ))}
      </Section>

      <Section title="Tài nguyên chung" count={general.length}>
        {general.map((r) => (
          <ResourceRow key={r.id} r={r} />
        ))}
      </Section>

      {filtered.length === 0 && (
        <div className="flex flex-col items-center gap-2 py-16 text-muted-foreground">
          <SearchX className="size-8" />
          <p className="text-sm">Không tìm thấy tài nguyên phù hợp.</p>
        </div>
      )}
    </div>
  );
}

function Section({ title, count, children }) {
  if (count === 0) return null;
  return (
    <div className="mb-6">
      <h2 className="mb-2.5 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
        {title} <span className="text-muted-foreground/50">· {count}</span>
      </h2>
      <Card className="divide-y py-0 [--card-spacing:0]">{children}</Card>
    </div>
  );
}

function ResourceRow({ r }) {
  const k = RESOURCE_KINDS[r.kind];
  const Icon = KIND_ICONS[r.kind];
  return (
    <div className="flex items-center gap-3.5 px-4 py-3">
      <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
        <Icon className="size-4" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium">{r.title}</span>
          {r.session && (
            <Badge
              className="shrink-0 font-mono"
              style={{ background: sessionColor(r.session) + "24", color: sessionColor(r.session) }}
            >
              {r.session}
            </Badge>
          )}
        </div>
        <div className="mt-0.5 flex flex-wrap items-center gap-x-1.5 text-xs text-muted-foreground">
          <span>{k.label}</span>
          <span className="text-muted-foreground/40">·</span>
          <span>{r.by}</span>
          <span className="text-muted-foreground/40">·</span>
          <span className="font-mono">{r.date}</span>
          {r.note && (
            <>
              <span className="text-muted-foreground/40">·</span>
              <span className="flex items-center gap-1 text-amber-400/90">
                <Lock className="size-3" /> {r.note}
              </span>
            </>
          )}
        </div>
      </div>
      <Button variant="ghost" size="sm" className="shrink-0" onClick={(e) => e.preventDefault()}>
        Mở <ExternalLink data-icon="inline-end" />
      </Button>
    </div>
  );
}

function FilterChip({ active, onClick, children }) {
  return (
    <Button
      variant={active ? "secondary" : "outline"}
      size="sm"
      onClick={onClick}
      className={cn(!active && "text-muted-foreground")}
    >
      {children}
    </Button>
  );
}
