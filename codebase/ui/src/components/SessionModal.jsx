import { useEffect, useRef } from "react";
import { SESSION_TYPES, fmtDM } from "../data/mock.js";
import Icon from "./Icons.jsx";

const DAY_FULL = ["Chủ nhật", "Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7"];

const LINK_DEFS = [
  { key: "zoom", label: "Vào phòng Zoom", Glyph: Icon.Video, primary: true },
  { key: "slide", label: "Slide", Glyph: Icon.Slides },
  { key: "record", label: "Record", Glyph: Icon.Video },
  { key: "materials", label: "Tài liệu", Glyph: Icon.Doc },
];

export default function SessionModal({ session: s, onClose, onAskAbout }) {
  const t = SESSION_TYPES[s.type];
  const available = LINK_DEFS.filter((l) => s.links?.[l.key]);
  const missing = LINK_DEFS.filter((l) => !s.links?.[l.key] && l.key !== "zoom");
  const closeRef = useRef(null);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/35 p-4 backdrop-blur-[2px]"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`Chi tiết buổi ${s.code}`}
    >
      <div
        className="flex max-h-[86vh] w-full max-w-[560px] flex-col overflow-hidden rounded-2xl border border-line bg-surface shadow-float"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header — mã buổi + loại + thời gian, không lặp lại ở phần dưới */}
        <div className="shrink-0 border-b border-line px-5 py-4">
          <div className="flex items-start gap-3">
            <div className="min-w-0 flex-1">
              <div className="mb-1.5 flex flex-wrap items-center gap-2">
                <span
                  className="rounded px-1.5 py-0.5 text-2xs font-bold text-white"
                  style={{ background: t.color }}
                >
                  {s.code}
                </span>
                <span className="text-2xs font-bold uppercase tracking-wide" style={{ color: t.color }}>
                  {t.label}
                </span>
              </div>
              <h2 className="text-lg font-bold leading-snug text-ink">{s.title}</h2>
              <p className="mt-1.5 flex items-center gap-1.5 text-sm text-ink-2">
                <Icon.Clock className="h-3.5 w-3.5 shrink-0 text-ink-3" />
                {DAY_FULL[s.date.getDay()]}, {fmtDM(s.date)} · {s.timeLabel}
              </p>
            </div>
            <button
              ref={closeRef}
              onClick={onClose}
              className="shrink-0 rounded-lg p-1.5 text-ink-3 hover:bg-surface-2 hover:text-ink"
              aria-label="Đóng"
            >
              <Icon.Close className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-5">
          {/* Thông tin buổi — mỗi ô một ý, không gộp "Địa điểm / Lớp" như bản cũ */}
          <dl className="grid grid-cols-2 gap-2">
            <Info label="Hình thức" value={s.format === "Offline" ? "Học trực tiếp" : "Online (Zoom)"} />
            <Info label="Dành cho" value={s.cls} />
            <Info label="Địa điểm" value={s.format === "Offline" ? s.location : "Link Zoom bên dưới"} />
            <Info label="Phụ trách" value={s.host} />
          </dl>

          {s.desc && <p className="text-base leading-relaxed text-ink-2">{s.desc}</p>}

          <div>
            <SectionTitle>Tài liệu buổi học</SectionTitle>
            <div className="flex flex-wrap gap-2">
              {available.map(({ key, label, Glyph, primary }) => (
                <a
                  key={key}
                  href={s.links[key]}
                  onClick={(e) => e.preventDefault()}
                  className={
                    "flex items-center gap-1.5 rounded-lg px-3 py-2 text-base font-semibold transition-colors " +
                    (primary
                      ? "bg-brand text-white hover:bg-brand-hover"
                      : "border border-line text-ink-2 hover:border-brand-line hover:bg-brand-soft hover:text-brand")
                  }
                >
                  <Glyph className="h-4 w-4" />
                  {label}
                </a>
              ))}
              {missing.map(({ key, label, Glyph }) => (
                <span
                  key={key}
                  className="flex items-center gap-1.5 rounded-lg border border-dashed border-line-2 px-3 py-2 text-base text-ink-3"
                  title="Sẽ tự động gắn vào buổi khi được đăng lên #tài-nguyên"
                >
                  <Glyph className="h-4 w-4" />
                  {label} · chưa có
                </span>
              ))}
            </div>
            <p className="mt-2 text-xs leading-relaxed text-ink-3">
              Slide và record đăng tại <span className="font-medium text-ink-2">#tài-nguyên</span> sẽ
              tự động gắn vào buổi này (Session Linker).
            </p>
          </div>

          {s.faqs?.length > 0 && (
            <div>
              <SectionTitle>Câu hỏi thường gặp · {t.label}</SectionTitle>
              <div className="overflow-hidden rounded-xl border border-line">
                {s.faqs.map((f, i) => (
                  <details key={i} className="group border-b border-line last:border-b-0">
                    <summary className="flex items-center justify-between gap-2 bg-surface px-3 py-2.5 text-base font-medium text-ink hover:bg-surface-2">
                      {f.q}
                      <Icon.ChevronDown className="h-4 w-4 shrink-0 text-ink-3 transition-transform group-open:rotate-180" />
                    </summary>
                    <p className="border-t border-line bg-surface-2 px-3 py-2.5 text-sm leading-relaxed text-ink-2">
                      {f.a}
                    </p>
                  </details>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer — nguồn + lối đi tiếp. Bản cũ chỉ gợi ý gõ "/ask", giờ là nút thật. */}
        <div className="flex shrink-0 flex-wrap items-center gap-x-3 gap-y-2 border-t border-line bg-surface-2 px-5 py-3">
          <span className="text-xs text-ink-3">
            Nguồn: <span className="font-medium text-ink-2">{s.source.channel}</span> · cập nhật{" "}
            {s.source.updated}
          </span>
          <button
            onClick={() => {
              onClose();
              onAskAbout?.(`${s.code} — ${s.title} có gì cần chuẩn bị trước không?`);
            }}
            className="ml-auto flex items-center gap-1.5 rounded-lg border border-line bg-surface px-2.5 py-1.5 text-xs font-semibold text-ink-2 transition-colors hover:border-brand-line hover:text-brand"
          >
            <Icon.Sparkle className="h-3.5 w-3.5" />
            Hỏi Companion về buổi này
          </button>
        </div>
      </div>
    </div>
  );
}

function Info({ label, value }) {
  return (
    <div className="rounded-lg border border-line bg-surface-2 px-3 py-2">
      <dt className="text-2xs font-semibold uppercase tracking-wide text-ink-3">{label}</dt>
      <dd className="mt-0.5 text-sm font-semibold text-ink">{value}</dd>
    </div>
  );
}

function SectionTitle({ children }) {
  return (
    <h3 className="mb-2 text-2xs font-bold uppercase tracking-[0.1em] text-ink-3">{children}</h3>
  );
}
