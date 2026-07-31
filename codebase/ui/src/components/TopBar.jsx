import { useState } from "react";
import { isMock } from "../api/client.js";
import { CLASSES } from "../config.js";
import Icon from "./Icons.jsx";

export default function TopBar({
  meta,
  query,
  onQuery,
  myClass,
  onClass,
  queueCount = 0,
  onOpenNav,
}) {
  const [panel, setPanel] = useState(null); // "bell" | "help" | null

  return (
    <header className="relative z-20 shrink-0 border-b border-line bg-surface">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-3 px-4 py-3 lg:px-6">
        <button
          onClick={onOpenNav}
          className="-ml-1 rounded-lg p-2 text-ink-2 hover:bg-surface-2 lg:hidden"
          aria-label="Mở menu"
        >
          <Icon.Filter className="h-5 w-5" />
        </button>

        {/* Tiêu đề trang nằm ở TopBar → cả 3 trang cùng một cấp bậc chữ,
            thay vì mỗi page tự đặt h1 với cỡ riêng như bản cũ. */}
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-xl font-bold text-ink">{meta.title}</h1>
          <p className="mt-0.5 truncate text-sm text-ink-2">{meta.desc}</p>
        </div>

        <div className="order-last flex w-full min-w-0 items-center gap-2 md:order-none md:w-auto md:flex-1 md:justify-end">
          {/* MỘT ô tìm kiếm duy nhất, luôn áp vào trang đang mở.
              Bản cũ: ô này chỉ chạy ở Bản tin, còn Tài nguyên có ô search thứ hai. */}
          <label className="flex min-w-0 flex-1 items-center gap-2 rounded-lg border border-line bg-surface-2 px-2.5 py-2 transition-colors focus-within:border-brand focus-within:bg-surface md:max-w-[430px]">
            <Icon.Search className="h-4 w-4 shrink-0 text-ink-3" />
            <input
              value={query}
              onChange={(e) => onQuery(e.target.value)}
              placeholder={meta.searchHint}
              className="min-w-0 flex-1 bg-transparent text-base text-ink outline-none placeholder:text-ink-3"
            />
            {query && (
              <button
                onClick={() => onQuery("")}
                className="shrink-0 rounded p-0.5 text-ink-3 hover:text-ink"
                aria-label="Xoá tìm kiếm"
              >
                <Icon.Close className="h-3.5 w-3.5" />
              </button>
            )}
          </label>

          {isMock() && (
            <span className="hidden shrink-0 rounded-md border border-warn/25 bg-warn-soft px-2 py-1 text-2xs font-bold uppercase tracking-wide text-warn xl:inline">
              Dữ liệu mẫu
            </span>
          )}

          <div className="flex shrink-0 items-center gap-0.5">
            <IconButton
              label="Thông báo"
              active={panel === "bell"}
              dot={queueCount > 0}
              onClick={() => setPanel((p) => (p === "bell" ? null : "bell"))}
            >
              <Icon.Bell className="h-[18px] w-[18px]" />
            </IconButton>
            <IconButton
              label="Companion làm được gì"
              active={panel === "help"}
              onClick={() => setPanel((p) => (p === "help" ? null : "help"))}
            >
              <Icon.Help className="h-[18px] w-[18px]" />
            </IconButton>
          </div>

          <div className="mx-1 hidden h-6 w-px shrink-0 bg-line sm:block" />

          <label className="flex shrink-0 items-center gap-1.5 rounded-lg border border-line bg-surface px-2.5 py-1.5 transition-colors hover:border-line-2">
            <span className="text-2xs font-semibold uppercase tracking-wide text-ink-3">Lớp</span>
            <select
              value={myClass}
              onChange={(e) => onClass(e.target.value)}
              className="cursor-pointer bg-transparent text-sm font-semibold text-ink outline-none"
            >
              {CLASSES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {panel && (
        <>
          <button
            className="fixed inset-0 z-10 cursor-default"
            onClick={() => setPanel(null)}
            aria-label="Đóng"
          />
          <div className="absolute right-4 top-full z-20 mt-1 w-[300px] rounded-xl border border-line bg-surface p-3.5 shadow-float lg:right-6">
            {panel === "bell" ? <BellPanel queueCount={queueCount} /> : <HelpPanel />}
          </div>
        </>
      )}
    </header>
  );
}

function BellPanel({ queueCount }) {
  return (
    <>
      <PanelTitle>Thông báo của bạn</PanelTitle>
      {queueCount > 0 ? (
        <div className="rounded-lg border border-warn/25 bg-warn-soft p-2.5">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-warn">
            <Icon.Inbox className="h-3.5 w-3.5" />
            {queueCount} câu hỏi đang chờ TA xác nhận
          </div>
          <p className="mt-1 text-2xs leading-relaxed text-warn/85">
            Companion đã chuyển sang TA phụ trách lớp. Bạn sẽ nhận trả lời qua Discord.
          </p>
        </div>
      ) : (
        <p className="text-xs leading-relaxed text-ink-2">
          Chưa có thông báo nào. Khi Companion chuyển một câu hỏi của bạn sang TA, trạng thái sẽ
          hiện ở đây.
        </p>
      )}
    </>
  );
}

function HelpPanel() {
  return (
    <>
      <PanelTitle>Companion làm được gì</PanelTitle>
      <ul className="space-y-1.5 text-xs leading-relaxed text-ink-2">
        <li className="flex gap-2">
          <Icon.Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ok" />
          Trả lời về lịch học, tài liệu, thông báo — luôn kèm nguồn.
        </li>
        <li className="flex gap-2">
          <Icon.Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ok" />
          Không có căn cứ thì chuyển TA phụ trách lớp, không đoán.
        </li>
        <li className="flex gap-2">
          <Icon.Ban className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-3" />
          Không tra web, không trả lời về điểm số hay việc cá nhân.
        </li>
      </ul>
      <p className="mt-2.5 border-t border-line pt-2.5 text-2xs text-ink-3">
        Ô tìm kiếm ở trên chỉ lọc trong trang bạn đang mở. Cần tra cứu ngang trang thì hỏi
        Companion.
      </p>
    </>
  );
}

function PanelTitle({ children }) {
  return (
    <h2 className="mb-2 text-2xs font-bold uppercase tracking-[0.1em] text-ink-3">{children}</h2>
  );
}

function IconButton({ children, label, onClick, active, dot }) {
  return (
    <button
      onClick={onClick}
      aria-label={label}
      title={label}
      className={
        "relative rounded-lg p-2 transition-colors " +
        (active ? "bg-brand-soft text-brand" : "text-ink-2 hover:bg-surface-2 hover:text-ink")
      }
    >
      {children}
      {dot && (
        <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-danger ring-2 ring-surface" />
      )}
    </button>
  );
}
