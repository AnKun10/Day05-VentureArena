import { useEffect, useMemo, useRef, useState } from "react";
import { SESSIONS, SESSION_TYPES, startOfWeek, addDays, fmtDM, isSameDay } from "../data/mock.js";
import { SHARED_CLASSES } from "../config.js";
import SessionModal from "../components/SessionModal.jsx";
import Icon from "../components/Icons.jsx";

const HPX = 56; // px mỗi giờ
const PAD_H = 1; // đệm 1 giờ trên/dưới quanh buổi sớm nhất / muộn nhất
const DAY_LABELS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];
const MONTHS = ["Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6", "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"];

const isShared = (s) => SHARED_CLASSES.includes(s.cls);

export default function CalendarPage({ query = "", myClass, focusCode, onFocusHandled, onAskAbout }) {
  const [weekOffset, setWeekOffset] = useState(0);
  const [selected, setSelected] = useState(null);
  const scrollRef = useRef(null);

  // Bấm citation trong chat (vd "WS-3") → nhảy đúng tuần và mở block buổi đó.
  useEffect(() => {
    if (!focusCode) return;
    const s = SESSIONS.find((x) => x.code === focusCode);
    if (s) {
      setWeekOffset(
        Math.round((startOfWeek(s.date) - startOfWeek(new Date())) / (7 * 86400000))
      );
      setSelected(s);
    }
    onFocusHandled?.();
  }, [focusCode]);

  const today = new Date();
  const monday = addDays(startOfWeek(today), weekOffset * 7);
  const days = useMemo(
    () => Array.from({ length: 7 }, (_, i) => addDays(monday, i)),
    [monday.getTime()]
  );

  const weekSessions = useMemo(
    () => SESSIONS.filter((s) => days.some((d) => isSameDay(s.date, d))),
    [days]
  );

  // Lớp lấy thẳng từ bộ chọn ở TopBar — trang không có bộ lọc riêng nữa.
  const visible = useMemo(
    () => weekSessions.filter((s) => isShared(s) || s.cls === myClass),
    [weekSessions, myClass]
  );

  const q = query.trim().toLowerCase();
  const matches = (s) =>
    !q || [s.code, s.title, s.host, s.cls, s.location].join(" ").toLowerCase().includes(q);
  const matchCount = visible.filter(matches).length;

  // Khung giờ bám theo dữ liệu thật: bản cũ cố định 8:00–23:00 nên ~70%
  // chiều cao lưới là khoảng trắng (gần như mọi buổi nằm 18:30–22:00).
  const [startH, endH] = useMemo(() => {
    if (visible.length === 0) return [17, 22];
    const lo = Math.floor(Math.min(...visible.map((s) => s.start))) - PAD_H;
    const hi = Math.ceil(Math.max(...visible.map((s) => s.end))) + PAD_H;
    return [Math.max(0, lo), Math.min(24, hi)];
  }, [visible]);

  const gridH = (endH - startH) * HPX;
  const nowTop = (today.getHours() + today.getMinutes() / 60 - startH) * HPX;

  const sessionsByDay = useMemo(
    () => days.map((d) => visible.filter((s) => isSameDay(s.date, d))),
    [days, visible]
  );

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = 0;
  }, [weekOffset]);

  return (
    <div className="flex h-full flex-col">
      {/* Thanh công cụ: điều hướng tuần | bộ lọc | chú giải — mỗi nhóm một vùng */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2.5 border-b border-line bg-surface px-4 py-2.5 lg:px-6">
        <div className="flex items-center gap-2">
          <div className="flex items-center rounded-lg border border-line">
            <button
              onClick={() => setWeekOffset((w) => w - 1)}
              className="rounded-l-lg px-2 py-1.5 text-ink-2 hover:bg-surface-2 hover:text-ink"
              aria-label="Tuần trước"
            >
              <Icon.ChevronLeft className="h-4 w-4" />
            </button>
            <span className="h-5 w-px bg-line" />
            <button
              onClick={() => setWeekOffset((w) => w + 1)}
              className="rounded-r-lg px-2 py-1.5 text-ink-2 hover:bg-surface-2 hover:text-ink"
              aria-label="Tuần sau"
            >
              <Icon.ChevronRight className="h-4 w-4" />
            </button>
          </div>
          <button
            onClick={() => setWeekOffset(0)}
            disabled={weekOffset === 0}
            className="rounded-lg border border-line px-2.5 py-1.5 text-xs font-semibold text-ink-2 transition-colors hover:bg-surface-2 hover:text-ink disabled:opacity-40"
          >
            Hôm nay
          </button>
        </div>

        <div className="min-w-0">
          <div className="text-base font-semibold text-ink">
            {fmtDM(days[0])} – {fmtDM(days[6])}
          </div>
          <div className="text-2xs text-ink-3">
            {MONTHS[days[3].getMonth()]} {days[3].getFullYear()}
            {weekOffset === 0 && " · Tuần này"}
          </div>
        </div>

        <div className="ml-auto flex flex-wrap items-center gap-2">
          {q && (
            <span className="rounded-lg bg-brand-soft px-2 py-1 text-xs font-semibold text-brand">
              {matchCount} buổi khớp “{query}”
            </span>
          )}
        </div>
      </div>

      {/* Chú giải loại buổi — hàng riêng, cỡ nhỏ, không tranh chỗ với điều hướng */}
      <div className="flex shrink-0 flex-wrap items-center gap-x-4 gap-y-1.5 border-b border-line bg-surface px-4 py-2 lg:px-6">
        <span className="text-2xs font-bold uppercase tracking-[0.1em] text-ink-3">Loại buổi</span>
        {Object.entries(SESSION_TYPES).map(([k, t]) => (
          <span key={k} className="flex items-center gap-1.5 text-xs text-ink-2">
            <span className="h-2 w-2 rounded-sm" style={{ background: t.color }} />
            {t.label}
          </span>
        ))}
      </div>

      {/* Đầu cột ngày */}
      <div className="grid shrink-0 grid-cols-[52px_repeat(7,minmax(0,1fr))] border-b border-line bg-surface pr-2.5">
        <div />
        {days.map((d, i) => {
          const isToday = isSameDay(d, today);
          const count = sessionsByDay[i].length;
          return (
            <div
              key={i}
              className={
                "flex flex-col items-center border-l border-line py-2 " +
                (isToday ? "bg-brand-soft/60" : "")
              }
            >
              <span
                className={
                  "text-2xs font-semibold uppercase " + (isToday ? "text-brand" : "text-ink-3")
                }
              >
                {DAY_LABELS[i]}
              </span>
              <span
                className={
                  "mt-0.5 flex h-6 w-6 items-center justify-center rounded-full text-sm font-bold " +
                  (isToday ? "bg-brand text-white" : "text-ink")
                }
              >
                {d.getDate()}
              </span>
              <span className="mt-0.5 h-3 text-2xs text-ink-3">
                {count > 0 ? `${count} buổi` : ""}
              </span>
            </div>
          );
        })}
      </div>

      {/* Lưới */}
      <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto bg-surface">
        <div className="grid grid-cols-[52px_repeat(7,minmax(0,1fr))] pb-3 pr-2.5">
          {/* cột giờ */}
          <div className="relative" style={{ height: gridH }}>
            {Array.from({ length: endH - startH + 1 }, (_, i) => (
              <div
                key={i}
                className="absolute right-2 -translate-y-1/2 text-2xs font-medium tabular-nums text-ink-3"
                style={{ top: i * HPX }}
              >
                {i === 0 ? "" : `${String(startH + i).padStart(2, "0")}:00`}
              </div>
            ))}
          </div>

          {days.map((d, di) => {
            const isToday = isSameDay(d, today);
            return (
              <div
                key={di}
                className={"relative border-l border-line " + (isToday ? "bg-brand-soft/35" : "")}
                style={{
                  height: gridH,
                  backgroundImage:
                    "repeating-linear-gradient(to bottom, transparent 0, transparent " +
                    (HPX - 1) +
                    "px, #eef1f8 " +
                    (HPX - 1) +
                    "px, #eef1f8 " +
                    HPX +
                    "px)",
                }}
              >
                {isToday && nowTop > 0 && nowTop < gridH && (
                  <div className="pointer-events-none absolute inset-x-0 z-20" style={{ top: nowTop }}>
                    <div className="h-px bg-danger" />
                    <div className="-mt-[3px] h-1.5 w-1.5 rounded-full bg-danger" />
                  </div>
                )}

                {sessionsByDay[di].map((s) => {
                  const t = SESSION_TYPES[s.type];
                  const top = (s.start - startH) * HPX + 2;
                  const height = (s.end - s.start) * HPX - 5;
                  const dim = q && !matches(s);
                  return (
                    <button
                      key={s.code}
                      onClick={() => setSelected(s)}
                      className={
                        "absolute left-1 right-1.5 z-10 overflow-hidden rounded-md border-l-[3px] px-1.5 py-1 text-left transition-shadow hover:shadow-card " +
                        (dim ? "opacity-25" : "")
                      }
                      style={{
                        top,
                        height,
                        background: t.color + "1c",
                        borderLeftColor: t.color,
                      }}
                    >
                      <div
                        className="flex items-baseline gap-1 text-2xs font-bold"
                        style={{ color: t.color }}
                      >
                        <span>{s.code}</span>
                        <span className="truncate font-semibold tabular-nums opacity-80">
                          {s.timeLabel}
                        </span>
                      </div>
                      <div className="mt-0.5 line-clamp-2 text-xs font-semibold leading-tight text-ink">
                        {s.title}
                      </div>
                      {height > 78 && (
                        <div className="mt-1 flex items-center gap-1 truncate text-2xs text-ink-2">
                          {s.format === "Offline" ? (
                            <Icon.Pin className="h-3 w-3 shrink-0" />
                          ) : (
                            <Icon.Video className="h-3 w-3 shrink-0" />
                          )}
                          <span className="truncate">
                            {s.format === "Offline" ? s.location : "Zoom"}
                          </span>
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            );
          })}
        </div>

        {visible.length === 0 && (
          <p className="py-10 text-center text-base text-ink-3">
            Tuần này không có buổi nào cho lớp {myClass}.
          </p>
        )}
      </div>

      {selected && (
        <SessionModal
          session={selected}
          onClose={() => setSelected(null)}
          onAskAbout={onAskAbout}
        />
      )}
    </div>
  );
}
