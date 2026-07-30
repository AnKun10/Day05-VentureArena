import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, MapPin, Video } from "lucide-react";
import {
  SESSIONS,
  SESSION_TYPES,
  startOfWeek,
  addDays,
  fmtDM,
  isSameDay,
} from "../data/mock.js";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
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

  const nowTop = (today.getHours() + today.getMinutes() / 60 - START_H) * HPX;

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-4 border-b px-6 py-4">
        <div className="mr-2">
          <h1 className="font-heading text-lg font-semibold">Lịch học</h1>
          <p className="text-xs text-muted-foreground">
            Tuần {fmtDM(days[0])} – {fmtDM(days[6])} · bấm vào block để xem chi tiết
          </p>
        </div>

        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="icon-sm"
            aria-label="Tuần trước"
            onClick={() => setWeekOffset((w) => w - 1)}
          >
            <ChevronLeft />
          </Button>
          <Button
            variant={weekOffset === 0 ? "secondary" : "outline"}
            size="sm"
            onClick={() => setWeekOffset(0)}
          >
            Tuần này
          </Button>
          <Button
            variant="outline"
            size="icon-sm"
            aria-label="Tuần sau"
            onClick={() => setWeekOffset((w) => w + 1)}
          >
            <ChevronRight />
          </Button>
        </div>

        <div className="ml-auto flex flex-wrap items-center gap-x-3.5 gap-y-1.5">
          {Object.entries(SESSION_TYPES).map(([k, t]) => (
            <span key={k} className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span className="size-2 rounded-full" style={{ background: t.color }} />
              {t.label}
            </span>
          ))}
        </div>
      </div>

      {/* Day headers */}
      <div className="grid shrink-0 grid-cols-[56px_repeat(7,1fr)] border-b bg-sidebar pr-2">
        <div />
        {days.map((d, i) => {
          const isToday = isSameDay(d, today);
          return (
            <div key={i} className="flex items-center justify-center gap-2 border-l py-2.5">
              <span
                className={cn(
                  "text-[11px] font-medium",
                  isToday ? "text-primary" : "text-muted-foreground"
                )}
              >
                {DAY_LABELS[i]}
              </span>
              <span
                className={cn(
                  "flex size-6 items-center justify-center rounded-full font-mono text-xs font-medium",
                  isToday ? "bg-primary text-primary-foreground" : "text-foreground"
                )}
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
                className="absolute right-2.5 -translate-y-1/2 font-mono text-[10px] text-muted-foreground/70"
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
                className={cn("relative border-l", isToday && "bg-primary/[0.04]")}
                style={{
                  height: (END_H - START_H) * HPX,
                  backgroundImage:
                    "repeating-linear-gradient(to bottom, color-mix(in oklch, var(--foreground) 7%, transparent) 0, color-mix(in oklch, var(--foreground) 7%, transparent) 1px, transparent 1px, transparent " +
                    HPX +
                    "px)",
                }}
              >
                {/* now line */}
                {isToday && nowTop > 0 && nowTop < (END_H - START_H) * HPX && (
                  <div className="absolute right-0 left-0 z-10" style={{ top: nowTop }}>
                    <div className="h-px bg-destructive" />
                    <div className="-mt-[3px] size-1.5 rounded-full bg-destructive" />
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
                      className="absolute right-1.5 left-1 overflow-hidden rounded-md px-2 py-1 text-left transition-all outline-none hover:ring-1 hover:ring-foreground/20 focus-visible:ring-2 focus-visible:ring-ring"
                      style={{
                        top,
                        height,
                        background: t.color + "1c",
                        borderLeft: `2px solid ${t.color}`,
                      }}
                    >
                      <div className="font-mono text-[10px] font-medium" style={{ color: t.color }}>
                        {s.code} · {s.timeLabel.split(" – ")[0]}
                      </div>
                      <div className="mt-0.5 line-clamp-2 text-[11px] leading-tight font-medium text-foreground/90">
                        {s.title}
                      </div>
                      {height > 70 && (
                        <div className="mt-1 flex items-center gap-1 truncate text-[10px] text-muted-foreground">
                          {s.format === "Offline" ? (
                            <MapPin className="size-2.5 shrink-0" />
                          ) : (
                            <Video className="size-2.5 shrink-0" />
                          )}
                          {s.format === "Offline" ? s.location : s.format}
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
