import { SESSION_TYPES, fmtDM } from "../data/mock.js";

const DAY_FULL = ["Chủ nhật", "Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7"];

const LINK_DEFS = [
  { key: "zoom", label: "Tham gia Zoom", icon: "💻" },
  { key: "slide", label: "Slide", icon: "📑" },
  { key: "record", label: "Record", icon: "🎥" },
  { key: "materials", label: "Tài liệu", icon: "📄" },
];

export default function SessionModal({ session: s, onClose }) {
  const t = SESSION_TYPES[s.type];
  const available = LINK_DEFS.filter((l) => s.links?.[l.key]);
  const missing = LINK_DEFS.filter((l) => !s.links?.[l.key] && l.key !== "zoom");

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="max-h-[85vh] w-full max-w-[560px] overflow-y-auto rounded-2xl border border-[#2a3040] bg-[#151823] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-5 pb-4" style={{ background: `linear-gradient(135deg, ${t.color}22, transparent 60%)` }}>
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="mb-1.5 flex items-center gap-2">
                <span
                  className="rounded-md px-2 py-0.5 text-[11px] font-bold text-white"
                  style={{ background: t.color }}
                >
                  {s.code}
                </span>
                <span className="text-[11px] font-medium" style={{ color: t.color }}>
                  {t.label}
                </span>
              </div>
              <h2 className="text-[17px] font-bold leading-snug text-white">{s.title}</h2>
              <p className="mt-1 text-[12.5px] text-zinc-400">
                🕐 {DAY_FULL[s.date.getDay()]}, {fmtDM(s.date)} · {s.timeLabel}
              </p>
            </div>
            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-zinc-500 hover:bg-white/10 hover:text-white"
              aria-label="Đóng"
            >
              ✕
            </button>
          </div>
        </div>

        <div className="space-y-4 p-5 pt-1">
          {/* Info grid */}
          <div className="grid grid-cols-2 gap-2.5">
            <Info label="Hình thức" value={s.format === "Offline" ? "🏫 Offline" : "💻 Online (Zoom)"} />
            <Info label="Địa điểm / Lớp" value={s.location ? `${s.location} · ${s.cls}` : s.cls} />
            <Info label="Phụ trách / Diễn giả" value={s.host} />
            <Info label="Mã buổi" value={s.code} />
          </div>

          {s.desc && <p className="text-[13px] leading-relaxed text-zinc-300">{s.desc}</p>}

          {/* Links */}
          <div>
            <SectionTitle>Tài liệu buổi học</SectionTitle>
            <div className="flex flex-wrap gap-2">
              {available.map((l) => (
                <a
                  key={l.key}
                  href={s.links[l.key]}
                  onClick={(e) => e.preventDefault()}
                  className="flex items-center gap-1.5 rounded-lg bg-[#5865f2] px-3 py-1.5 text-[12.5px] font-semibold text-white transition-colors hover:bg-[#4752c4]"
                >
                  {l.icon} {l.label}
                </a>
              ))}
              {missing.map((l) => (
                <span
                  key={l.key}
                  className="flex items-center gap-1.5 rounded-lg border border-dashed border-zinc-700 px-3 py-1.5 text-[12.5px] text-zinc-600"
                  title="Sẽ tự động gắn vào buổi khi được đăng lên #tài-nguyên"
                >
                  {l.icon} {l.label} · chưa có
                </span>
              ))}
            </div>
            <p className="mt-1.5 text-[11px] text-zinc-600">
              Slide/record đăng tại <span className="text-zinc-500">#tài-nguyên</span> sẽ tự động gắn vào
              block buổi này (Session Linker).
            </p>
          </div>

          {/* FAQ */}
          {s.faqs?.length > 0 && (
            <div>
              <SectionTitle>Câu hỏi thường gặp ({t.label})</SectionTitle>
              <div className="space-y-1.5">
                {s.faqs.map((f, i) => (
                  <details key={i} className="group rounded-lg border border-[#232838] bg-[#171a24]">
                    <summary className="flex items-center justify-between gap-2 px-3 py-2.5 text-[13px] font-medium text-zinc-200">
                      {f.q}
                      <span className="text-zinc-600 transition-transform group-open:rotate-180">⌄</span>
                    </summary>
                    <p className="border-t border-[#232838] px-3 py-2.5 text-[12.5px] leading-relaxed text-zinc-400">
                      {f.a}
                    </p>
                  </details>
                ))}
              </div>
            </div>
          )}

          {/* Footer */}
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[#232838] bg-[#12141c] px-3 py-2.5">
            <span className="text-[11px] text-zinc-600">
              Nguồn: <span className="text-zinc-500">{s.source.channel}</span> · cập nhật {s.source.updated}
            </span>
            <span className="text-[11px] text-zinc-500">
              Chưa rõ? Hỏi Companion: <code className="rounded bg-black/40 px-1.5 py-0.5 text-[#aab4ff]">/ask</code>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function Info({ label, value }) {
  return (
    <div className="rounded-lg border border-[#232838] bg-[#171a24] px-3 py-2">
      <div className="text-[10px] uppercase tracking-wide text-zinc-600">{label}</div>
      <div className="mt-0.5 text-[12.5px] font-medium text-zinc-200">{value}</div>
    </div>
  );
}

function SectionTitle({ children }) {
  return (
    <h3 className="mb-2 text-[11px] font-bold uppercase tracking-wider text-zinc-500">{children}</h3>
  );
}
