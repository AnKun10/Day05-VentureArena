import Icon from "./Icons.jsx";
import { PAGES } from "../config.js";

const NAV = [
  { id: "news", Glyph: Icon.News },
  { id: "calendar", Glyph: Icon.Calendar },
  { id: "resources", Glyph: Icon.Library },
];

export default function Sidebar({ page, onNavigate, onAskCompanion, myClass, myQueue = 0, open }) {
  return (
    <aside
      className={
        "fixed inset-y-0 left-0 z-40 flex w-[244px] shrink-0 flex-col border-r border-line bg-surface " +
        "transition-transform duration-200 lg:static lg:translate-x-0 " +
        (open ? "translate-x-0 shadow-float" : "-translate-x-full")
      }
    >
      {/* Thương hiệu — chỗ DUY NHẤT dùng gradient trong app */}
      <div className="flex items-center gap-2.5 px-4 pt-5 pb-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand to-brand-2 text-white">
          <Icon.Bot className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <div className="text-md font-bold leading-tight text-ink">Companion</div>
          <div className="truncate text-2xs font-semibold uppercase tracking-[0.1em] text-ink-3">
            AI Thực Chiến
          </div>
        </div>
      </div>

      {/* CTA chính — mở thẳng quyết định AI trung tâm */}
      <div className="px-3 pb-4">
        <button
          onClick={onAskCompanion}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-brand py-2.5 text-base font-semibold text-white transition-colors hover:bg-brand-hover"
        >
          <Icon.Chat className="h-4 w-4" />
          Hỏi Companion
        </button>
      </div>

      <nav className="flex flex-col gap-0.5 px-3" aria-label="Điều hướng chính">
        <div className="px-3 pb-1.5 text-2xs font-bold uppercase tracking-[0.1em] text-ink-3">
          Khoá học
        </div>
        {NAV.map(({ id, Glyph }) => {
          const active = page === id;
          return (
            <button
              key={id}
              onClick={() => onNavigate(id)}
              aria-current={active ? "page" : undefined}
              className={
                "flex items-center gap-2.5 rounded-lg px-3 py-2 text-left text-base font-medium transition-colors " +
                (active
                  ? "bg-brand-soft text-brand"
                  : "text-ink-2 hover:bg-surface-2 hover:text-ink")
              }
            >
              <Glyph className={"h-[18px] w-[18px] " + (active ? "" : "text-ink-3")} />
              {PAGES[id].label}
            </button>
          );
        })}
      </nav>

      {/* Chỉ hiện khi CHÍNH user này có câu đang chờ — tổng hàng đợi là việc của TA.
          HAX #4: đã bàn giao thì phải nói rõ đang ở đâu. */}
      {myQueue > 0 && (
        <div className="mt-5 px-3">
          <div className="rounded-xl border border-warn/25 bg-warn-soft p-3">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-warn">
              <Icon.Inbox className="h-3.5 w-3.5 shrink-0" />
              {myQueue} câu hỏi đang chờ TA
            </div>
            <p className="mt-1 text-2xs leading-relaxed text-warn/85">
              Sẽ gửi TA phụ trách <span className="font-semibold">{myClass}</span> trong bản tổng hợp
              kế tiếp.
            </p>
          </div>
        </div>
      )}

      {/* Hồ sơ học viên */}
      <div className="mt-auto border-t border-line p-2.5">
        <button className="flex w-full items-center gap-2.5 rounded-lg px-2 py-1.5 text-left transition-colors hover:bg-surface-2">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-soft text-xs font-bold text-brand">
            HV
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-semibold text-ink">Học viên T227</span>
            <span className="block truncate text-2xs text-ink-3">{myClass} · Cohort 4</span>
          </span>
          <Icon.Dots className="h-4 w-4 shrink-0 text-ink-3" />
        </button>
      </div>
    </aside>
  );
}
