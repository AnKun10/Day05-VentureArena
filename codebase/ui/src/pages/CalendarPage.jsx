import { useEffect, useMemo, useRef, useState } from "react";
import {
  SESSIONS,
  SESSION_TYPES,
  startOfWeek,
  addDays,
  fmtDM,
  isSameDay,
} from "../data/mock.js";
import SessionModal from "../components/SessionModal.jsx";

const START_H = 8;
const END_H = 23;
const HPX = 52; // px mỗi giờ
const DAY_LABELS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];

export default function CalendarPage() {
  const [weekOffset, setWeekOffset] = useState(0);
  const [selected, setSelected] = useState(null);
  const scrollRef = useRef(null);

  const today = new Date();
  const monday = addDays(startOfWeek(today), weekOffset * 7);
  const days = useMemo(
    () => Array.from({ length: 7 }, (_, i) => addDays(monday, i)),
    [monday.getTime()]
  );

  const sessionsByDay = useMemo(
    () => days.map((d) => SESSIONS.filter((s) => isSameDay(s.date, d))),
    [days]
  );

  // mở trang là cuộn tới khung giờ có lớp (≈17:00)
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = (17 - START_H) * HPX - 40;
  }, []);

  const nowTop =
    (today.getHours() + today.getMinutes() / 60 - START_H) * HPX;

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-4 border-b border-[#232838] px-6 py-4">
        <div>
          <h1 className="text-lg font-bold text-white">Lịch học</h1>
          <p className="text-xs text-zinc-500">
            Tuần {fmtDM(days[0])} – {fmtDM(days[6])} · bấm vào block để xem chi tiết buổi học
          </p>
        </div>

        <div className="flex items-center gap-1 rounded-lg border border-[#232838] bg-[#171a24] p-1">
          <button
            onClick={() => setWeekOffset((w) => w - 1)}
            className="rounded-md px-2.5 py-1 text-sm text-zinc-400 hover:bg-white/5 hover:text-white"
            aria-label="Tuần trước"
          >
            ‹
          </button>
          <button
            onClick={() => setWeekOffset(0)}
            className={
              "rounded-md px-3 py-1 text-xs font-semibold " +
              (weekOffset === 0
                ? "bg-[#5865f2]/20 text-[#aab4ff]"
                : "text-zinc-400 hover:bg-white/5 hover:text-white")
            }
          >
            Tuần này
          </button>
          <button
            onClick={() => setWeekOffset((w) => w + 1)}
            className="rounded-md px-2.5 py-1 text-sm text-zinc-400 hover:bg-white/5 hover:text-white"
            aria-label="Tuần sau"
          >
            ›
          </button>
        </div>

        <div className="ml-auto flex flex-wrap items-center gap-2">
          {Object.entries(SESSION_TYPES).map(([k, t]) => (
            <span
              key={k}
              className="flex items-center gap-1.5 rounded-full border border-[#232838] bg-[#171a24] px-2.5 py-1 text-[11px] text-zinc-400"
            >
              <span
                className="h-2 w-2 rounded-full"
                style={{ background: t.color }}
              />
              {t.label}
            </span>
          ))}
        </div>
      </div>

      {/* Day headers */}
      <div className="grid shrink-0 grid-cols-[56px_repeat(7,1fr)] border-b border-[#232838] bg-[#12141c] pr-2">
        <div />
        {days.map((d, i) => {
          const isToday = isSameDay(d, today);
          return (
            <div key={i} className="flex items-center justify-center gap-2 border-l border-[#232838] py-2.5">
              <span className={"text-[11px] font-medium " + (isToday ? "text-[#aab4ff]" : "text-zinc-500")}>
                {DAY_LABELS[i]}
              </span>
              <span
                className={
                  "flex h-6 w-6 items-center justify-center rounded-full text-[12px] font-bold " +
                  (isToday ? "bg-[#5865f2] text-white" : "text-zinc-300")
                }
              >
                {d.getDate()}
              </span>
            </div>
          );
        })}
      </div>

      {/* Grid */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="grid grid-cols-[56px_repeat(7,1fr)] pr-2">
          {/* cột giờ */}
          <div className="relative" style={{ height: (END_H - START_H) * HPX }}>
            {Array.from({ length: END_H - START_H }, (_, i) => (
              <div
                key={i}
                className="absolute right-2 -translate-y-1/2 text-[10px] text-zinc-600"
                style={{ top: (i + 1) * HPX }}
              >
                {String(START_H + i + 1).padStart(2, "0")}:00
              </div>
            ))}
          </div>

          {days.map((d, di) => {
            const isToday = isSameDay(d, today);
            return (
              <div
                key={di}
                className={"relative border-l border-[#232838] " + (isToday ? "bg-[#5865f2]/[0.04]" : "")}
                style={{
                  height: (END_H - START_H) * HPX,
                  backgroundImage:
                    "repeating-linear-gradient(to bottom, #1d212e 0, #1d212e 1px, transparent 1px, transparent " +
                    HPX +
                    "px)",
                }}
              >
                {/* now line */}
                {isToday && nowTop > 0 && nowTop < (END_H - START_H) * HPX && (
                  <div className="absolute left-0 right-0 z-10" style={{ top: nowTop }}>
                    <div className="h-px bg-red-500/80" />
                    <div className="-mt-[3px] ml-0 h-1.5 w-1.5 rounded-full bg-red-500" />
                  </div>
                )}

                {sessionsByDay[di].map((s) => {
                  const t = SESSION_TYPES[s.type];
                  const top = (s.start - START_H) * HPX + 2;
                  const height = (s.end - s.start) * HPX - 5;
                  return (
                    <button
                      key={s.code}
                      onClick={() => setSelected(s)}
                      className="absolute left-1 right-1.5 overflow-hidden rounded-md px-2 py-1 text-left transition-transform hover:scale-[1.02] hover:brightness-110"
                      style={{
                        top,
                        height,
                        background: t.color + "26",
                        borderLeft: `3px solid ${t.color}`,
                      }}
                    >
                      <div className="text-[10px] font-bold" style={{ color: t.color }}>
                        {s.code} · {s.timeLabel.split(" – ")[0]}
                      </div>
                      <div className="mt-0.5 line-clamp-2 text-[11px] font-medium leading-tight text-zinc-200">
                        {s.title}
                      </div>
                      {height > 70 && (
                        <div className="mt-0.5 truncate text-[10px] text-zinc-500">
                          {s.format === "Offline" ? `📍 ${s.location}` : "💻 " + s.format}
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>

      {selected && <SessionModal session={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
