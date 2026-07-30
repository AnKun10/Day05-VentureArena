import { useMemo, useState } from "react";
import { NEWS, NEWS_CATEGORIES, isHot } from "../data/mock.js";

const catOf = (id) => NEWS_CATEGORIES.find((c) => c.id === id);

export default function NewsPage() {
  const [cat, setCat] = useState("all");

  const hot = useMemo(
    () => [...NEWS].filter(isHot).sort((a, b) => b.hearts + b.comments - (a.hearts + a.comments)).slice(0, 4),
    []
  );
  const feed = useMemo(() => NEWS.filter((n) => cat === "all" || n.cat === cat), [cat]);

  return (
    <div className="mx-auto max-w-4xl px-6 py-6">
      <div className="mb-5">
        <h1 className="text-lg font-bold text-white">Bản tin cộng đồng</h1>
        <p className="text-xs text-zinc-500">
          Tổng hợp từ các kênh Discord của khoá, phân loại theo loại tin{" "}
          <span className="text-zinc-600">(taxonomy demo — nhóm chốt bộ loại tin sau)</span>
        </p>
      </div>

      {/* Hot trend */}
      <div className="mb-6">
        <h2 className="mb-2.5 text-[11px] font-bold uppercase tracking-wider text-zinc-500">
          🔥 Hot trend
        </h2>
        <div className="grid gap-2.5 sm:grid-cols-2">
          {hot.map((n) => {
            const c = catOf(n.cat);
            return (
              <a
                key={n.id}
                href={n.url}
                onClick={(e) => e.preventDefault()}
                className="group rounded-xl border border-[#232838] bg-gradient-to-br from-[#1a1d29] to-[#151823] p-3.5 transition-colors hover:border-[#3a4157]"
              >
                <div className="mb-1.5 flex items-center gap-2">
                  <CatBadge c={c} />
                  <span className="text-[10px] text-zinc-600">{n.channel}</span>
                  <span className="ml-auto text-[10px] font-bold text-orange-400">🔥</span>
                </div>
                <div className="line-clamp-2 text-[13.5px] font-semibold leading-snug text-zinc-100 group-hover:text-white">
                  {n.title}
                </div>
                <div className="mt-2 flex items-center gap-3 text-[11px] text-zinc-500">
                  <span>❤️ {n.hearts}</span>
                  <span>💬 {n.comments}</span>
                  <span className="ml-auto">{n.time}</span>
                </div>
              </a>
            );
          })}
        </div>
      </div>

      {/* Filter chips */}
      <div className="mb-4 flex flex-wrap gap-1.5">
        <CatChip active={cat === "all"} onClick={() => setCat("all")} label="Tất cả" color="#71717a" />
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
            <div
              key={n.id}
              className="rounded-xl border border-[#232838] bg-[#151823] px-4 py-3.5 transition-colors hover:border-[#3a4157]"
            >
              <div className="mb-1 flex flex-wrap items-center gap-2">
                <CatBadge c={c} />
                {n.open && (
                  <span className="rounded-md border border-blue-500/40 bg-blue-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-blue-400">
                    ⏳ Chờ TA trả lời
                  </span>
                )}
                {isHot(n) && <span className="text-[11px]">🔥</span>}
                <span className="ml-auto text-[11px] text-zinc-600">{n.time}</span>
              </div>
              <div className="text-[14px] font-semibold text-zinc-100">{n.title}</div>
              <p className="mt-1 line-clamp-2 text-[12.5px] leading-relaxed text-zinc-400">{n.summary}</p>
              <div className="mt-2.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-zinc-500">
                <span className="font-medium text-zinc-400">{n.author}</span>
                <RoleBadge role={n.role} />
                <span className="text-zinc-700">•</span>
                <span>{n.channel}</span>
                <span className="text-zinc-700">•</span>
                <span>❤️ {n.hearts}</span>
                <span>💬 {n.comments}</span>
                <a
                  href={n.url}
                  onClick={(e) => e.preventDefault()}
                  className="ml-auto font-semibold text-[#8891f2] hover:text-[#aab4ff]"
                >
                  Mở trên Discord ↗
                </a>
              </div>
            </div>
          );
        })}
        {feed.length === 0 && (
          <p className="py-10 text-center text-sm text-zinc-600">Chưa có tin thuộc loại này.</p>
        )}
      </div>
    </div>
  );
}

function CatBadge({ c }) {
  return (
    <span
      className="rounded-md px-1.5 py-0.5 text-[10px] font-bold"
      style={{ background: c.color + "22", color: c.color }}
    >
      {c.label}
    </span>
  );
}

function RoleBadge({ role }) {
  const isStaff = role !== "Học viên";
  return (
    <span
      className={
        "rounded px-1.5 py-0.5 text-[9.5px] font-semibold uppercase tracking-wide " +
        (isStaff ? "bg-emerald-500/15 text-emerald-400" : "bg-zinc-700/40 text-zinc-400")
      }
    >
      {role}
    </span>
  );
}

function CatChip({ active, onClick, label, color }) {
  return (
    <button
      onClick={onClick}
      className={
        "flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[12px] font-medium transition-colors " +
        (active
          ? "border-transparent text-white"
          : "border-[#232838] bg-[#171a24] text-zinc-400 hover:border-[#3a4157] hover:text-zinc-200")
      }
      style={active ? { background: color } : undefined}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: active ? "#fff" : color }} />
      {label}
    </button>
  );
}
