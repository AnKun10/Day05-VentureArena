import { useMemo, useState } from "react";
import { RESOURCES, RESOURCE_KINDS, SESSION_TYPES, SESSIONS } from "../data/mock.js";
import Icon from "../components/Icons.jsx";

const KIND_ICON = {
  slide: Icon.Slides,
  record: Icon.Video,
  doc: Icon.Doc,
  link: Icon.Link,
};

const sessionType = (code) => {
  if (!code) return null;
  const prefix = code.split("-")[0].toUpperCase();
  return SESSION_TYPES[prefix === "LAB" ? "LAB" : prefix] ?? null;
};

const knownSession = (code) => SESSIONS.some((s) => s.code === code);

export default function ResourcesPage({ query = "", onOpenSession }) {
  const [kind, setKind] = useState("all");

  // Ô tìm kiếm nằm ở TopBar — trang này không còn ô search riêng nữa.
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return RESOURCES.filter(
      (r) =>
        (kind === "all" || r.kind === kind) &&
        (q === "" || `${r.title} ${r.session || ""} ${r.by}`.toLowerCase().includes(q))
    );
  }, [kind, query]);

  const bySession = filtered.filter((r) => r.session);
  const general = filtered.filter((r) => !r.session);

  return (
    <div className="w-full px-4 py-5 lg:px-6">
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Chip active={kind === "all"} onClick={() => setKind("all")} count={RESOURCES.length}>
          Tất cả
        </Chip>
        {Object.entries(RESOURCE_KINDS).map(([k, v]) => {
          const Glyph = KIND_ICON[k];
          return (
            <Chip
              key={k}
              active={kind === k}
              onClick={() => setKind(k)}
              count={RESOURCES.filter((r) => r.kind === k).length}
            >
              <Glyph className="h-3.5 w-3.5" />
              {v.label}
            </Chip>
          );
        })}
        {query && (
          <span className="ml-auto text-sm text-ink-2">
            <span className="font-semibold text-ink">{filtered.length}</span> kết quả cho “{query}”
          </span>
        )}
      </div>

      <Section
        title="Gắn theo buổi học"
        hint="Session Linker đã nhận diện mã buổi từ #tài-nguyên"
        count={bySession.length}
      >
        {bySession.map((r) => (
          <ResourceCard key={r.id} r={r} onOpenSession={onOpenSession} />
        ))}
      </Section>

      <Section
        title="Tài nguyên chung"
        hint="Không thuộc buổi cụ thể — áp dụng cho toàn khoá"
        count={general.length}
      >
        {general.map((r) => (
          <ResourceCard key={r.id} r={r} onOpenSession={onOpenSession} />
        ))}
      </Section>

      {filtered.length === 0 && (
        <p className="py-12 text-center text-base text-ink-3">
          Không tìm thấy tài nguyên phù hợp{query ? ` với “${query}”` : ""}.
        </p>
      )}
    </div>
  );
}

function Section({ title, hint, count, children }) {
  if (count === 0) return null;
  return (
    <section className="mb-6">
      <div className="mb-2 flex items-baseline gap-2">
        <h2 className="text-2xs font-bold uppercase tracking-[0.1em] text-ink-3">{title}</h2>
        <span className="text-2xs font-semibold text-ink-3">· {count}</span>
        <span className="ml-auto hidden text-2xs text-ink-3 sm:block">{hint}</span>
      </div>
      <div className="overflow-hidden rounded-xl border border-line bg-surface shadow-card">
        {children}
      </div>
    </section>
  );
}

function ResourceCard({ r, onOpenSession }) {
  const k = RESOURCE_KINDS[r.kind];
  const Glyph = KIND_ICON[r.kind];
  const t = sessionType(r.session);
  const canOpen = r.session && knownSession(r.session);

  return (
    <div className="group flex items-center gap-3 border-b border-line px-4 py-3 transition-colors last:border-b-0 hover:bg-surface-2">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-surface-2 text-ink-2 group-hover:bg-surface">
        <Glyph className="h-[18px] w-[18px]" />
      </div>

      <div className="min-w-0 flex-1">
        <div className="truncate text-base font-semibold text-ink">{r.title}</div>
        <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-2xs text-ink-3">
          {r.session &&
            (canOpen ? (
              <button
                onClick={() => onOpenSession?.(r.session)}
                className="rounded px-1.5 py-0.5 text-2xs font-bold transition-opacity hover:opacity-80"
                style={{ background: (t?.color ?? "#8b98b0") + "1f", color: t?.color ?? "#8b98b0" }}
                title={`Mở buổi ${r.session} trên Lịch học`}
              >
                {r.session} ↗
              </button>
            ) : (
              <span
                className="rounded px-1.5 py-0.5 text-2xs font-bold"
                style={{ background: (t?.color ?? "#8b98b0") + "1f", color: t?.color ?? "#8b98b0" }}
              >
                {r.session}
              </span>
            ))}
          <span className="font-medium text-ink-2">{k.label}</span>
          <span className="text-line-2">·</span>
          <span>{r.by}</span>
          <span className="text-line-2">·</span>
          <span>{r.date}</span>
          {r.note && (
            <span className="flex items-center gap-1 font-medium text-warn">
              <Icon.Ban className="h-3 w-3" />
              {r.note}
            </span>
          )}
        </div>
      </div>

      <a
        href={r.url}
        onClick={(e) => e.preventDefault()}
        className="flex shrink-0 items-center gap-1.5 rounded-lg border border-line px-2.5 py-1.5 text-xs font-semibold text-ink-2 transition-colors hover:border-brand-line hover:bg-brand-soft hover:text-brand"
      >
        Mở
        <Icon.External className="h-3.5 w-3.5" />
      </a>
    </div>
  );
}

function Chip({ active, onClick, children, count }) {
  return (
    <button
      onClick={onClick}
      className={
        "flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition-colors " +
        (active
          ? "border-brand-line bg-brand-soft text-brand"
          : "border-line bg-surface text-ink-2 hover:border-line-2 hover:text-ink")
      }
    >
      {children}
      {count != null && (
        <span className={"text-2xs font-semibold " + (active ? "text-brand/70" : "text-ink-3")}>
          {count}
        </span>
      )}
    </button>
  );
}
