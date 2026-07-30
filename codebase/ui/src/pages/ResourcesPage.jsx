import { useMemo, useState } from "react";
import { RESOURCES, RESOURCE_KINDS, SESSION_TYPES } from "../data/mock.js";

const sessionColor = (code) => {
  if (!code) return "#71717a";
  const prefix = code.split("-")[0].toUpperCase();
  return SESSION_TYPES[prefix === "LAB" ? "LAB" : prefix]?.color ?? "#71717a";
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
        <h1 className="text-lg font-bold text-white">Tài nguyên</h1>
        <p className="text-xs text-zinc-500">
          Slide, record, tài liệu từ kênh <span className="text-zinc-400">#tài-nguyên</span> — tự động
          gắn vào buổi học tương ứng
        </p>
      </div>

      {/* Filters */}
      <div className="mb-5 flex flex-wrap items-center gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="🔍  Tìm theo tên hoặc mã buổi (VD: WS-2)…"
          className="w-72 rounded-lg border border-[#232838] bg-[#171a24] px-3 py-2 text-[13px] text-zinc-200 placeholder:text-zinc-600 focus:border-[#5865f2] focus:outline-none"
        />
        <div className="flex flex-wrap gap-1.5">
          <Chip active={kind === "all"} onClick={() => setKind("all")}>
            Tất cả
          </Chip>
          {Object.entries(RESOURCE_KINDS).map(([k, v]) => (
            <Chip key={k} active={kind === k} onClick={() => setKind(k)}>
              {v.icon} {v.label}
            </Chip>
          ))}
        </div>
      </div>

      <Section title="Gắn theo buổi học" count={bySession.length}>
        {bySession.map((r) => (
          <ResourceCard key={r.id} r={r} />
        ))}
      </Section>

      <Section title="Tài nguyên chung" count={general.length}>
        {general.map((r) => (
          <ResourceCard key={r.id} r={r} />
        ))}
      </Section>

      {filtered.length === 0 && (
        <p className="py-10 text-center text-sm text-zinc-600">Không tìm thấy tài nguyên phù hợp.</p>
      )}
    </div>
  );
}

function Section({ title, count, children }) {
  if (count === 0) return null;
  return (
    <div className="mb-6">
      <h2 className="mb-2.5 text-[11px] font-bold uppercase tracking-wider text-zinc-500">
        {title} <span className="text-zinc-700">· {count}</span>
      </h2>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function ResourceCard({ r }) {
  const k = RESOURCE_KINDS[r.kind];
  return (
    <div className="group flex items-center gap-3.5 rounded-xl border border-[#232838] bg-[#151823] px-4 py-3 transition-colors hover:border-[#3a4157]">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#1d212e] text-lg">
        {k.icon}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-[13.5px] font-semibold text-zinc-100">{r.title}</span>
          {r.session && (
            <span
              className="shrink-0 rounded-md px-1.5 py-0.5 text-[10px] font-bold text-white"
              style={{ background: sessionColor(r.session) }}
            >
              {r.session}
            </span>
          )}
        </div>
        <div className="mt-0.5 flex flex-wrap items-center gap-x-2 text-[11px] text-zinc-500">
          <span>{k.label}</span>
          <span className="text-zinc-700">•</span>
          <span>{r.by}</span>
          <span className="text-zinc-700">•</span>
          <span>{r.date}</span>
          {r.note && (
            <>
              <span className="text-zinc-700">•</span>
              <span className="text-amber-500/80">🔒 {r.note}</span>
            </>
          )}
        </div>
      </div>
      <a
        href={r.url}
        onClick={(e) => e.preventDefault()}
        className="shrink-0 rounded-lg border border-[#2a3040] px-3 py-1.5 text-[12px] font-semibold text-zinc-300 transition-colors hover:border-[#5865f2] hover:bg-[#5865f2]/10 hover:text-[#aab4ff]"
      >
        Mở ↗
      </a>
    </div>
  );
}

function Chip({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={
        "rounded-full border px-3 py-1.5 text-[12px] font-medium transition-colors " +
        (active
          ? "border-[#5865f2] bg-[#5865f2]/15 text-[#aab4ff]"
          : "border-[#232838] bg-[#171a24] text-zinc-400 hover:border-[#3a4157] hover:text-zinc-200")
      }
    >
      {children}
    </button>
  );
}
