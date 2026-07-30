import {
  BookOpenText,
  Building2,
  CalendarClock,
  Clapperboard,
  FileText,
  Hash,
  MapPin,
  Presentation,
  Radio,
  UserRound,
  Video,
} from "lucide-react";
import { SESSION_TYPES, fmtDM } from "../data/mock.js";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";

const DAY_FULL = ["Chủ nhật", "Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7"];

const LINK_DEFS = [
  { key: "zoom", label: "Tham gia Zoom", icon: Video },
  { key: "slide", label: "Slide", icon: Presentation },
  { key: "record", label: "Record", icon: Clapperboard },
  { key: "materials", label: "Tài liệu", icon: FileText },
];

export default function SessionModal({ session: s, onClose }) {
  const t = SESSION_TYPES[s.type];
  const available = LINK_DEFS.filter((l) => s.links?.[l.key]);
  const missing = LINK_DEFS.filter((l) => !s.links?.[l.key] && l.key !== "zoom");

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-[580px]">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <Badge className="font-mono" style={{ background: t.color + "1a", color: t.color }}>
              {s.code}
            </Badge>
            <span className="text-xs font-medium" style={{ color: t.color }}>
              {t.label}
            </span>
          </div>
          <DialogTitle className="text-lg leading-snug">{s.title}</DialogTitle>
        </DialogHeader>

        {/* Thông tin buổi học — icon + label highlight */}
        <div className="grid grid-cols-2 gap-2.5">
          <InfoCard
            icon={CalendarClock}
            label="Ngày & giờ"
            value={`${DAY_FULL[s.date.getDay()]}, ${fmtDM(s.date)} · ${s.timeLabel}`}
            mono
            wide
          />
          <InfoCard
            icon={s.format === "Offline" ? Building2 : Video}
            label="Hình thức"
            value={s.format === "Offline" ? "Offline" : "Online (Zoom)"}
          />
          <InfoCard
            icon={MapPin}
            label="Địa điểm / Lớp"
            value={s.location ? `${s.location} · ${s.cls}` : s.cls}
          />
          <InfoCard icon={UserRound} label="Phụ trách / Diễn giả" value={s.host} />
          <InfoCard icon={Hash} label="Mã buổi" value={s.code} mono />
        </div>

        {/* Tóm tắt nội dung bài học */}
        <div>
          <SectionTitle icon={BookOpenText}>Tóm tắt nội dung</SectionTitle>
          {s.desc && <p className="mb-2 text-sm leading-relaxed text-muted-foreground">{s.desc}</p>}
          {s.summary?.length > 0 && (
            <ul className="space-y-1.5">
              {s.summary.map((line, i) => (
                <li key={i} className="flex gap-2 text-sm leading-relaxed">
                  <span
                    className="mt-[7px] size-1.5 shrink-0 rounded-full"
                    style={{ background: t.color }}
                  />
                  {line}
                </li>
              ))}
            </ul>
          )}
        </div>

        <Separator />

        {/* Links */}
        <div>
          <SectionTitle icon={FileText}>Tài liệu buổi học</SectionTitle>
          <div className="flex flex-wrap gap-2">
            {available.map(({ key, label, icon: Icon }) => (
              <Button
                key={key}
                variant={key === "zoom" ? "default" : "outline"}
                size="sm"
                onClick={(e) => e.preventDefault()}
              >
                <Icon /> {label}
              </Button>
            ))}
            {missing.map(({ key, label, icon: Icon }) => (
              <Button key={key} variant="outline" size="sm" disabled>
                <Icon /> {label} · chưa có
              </Button>
            ))}
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            Slide/record đăng tại <span className="font-mono">#tài-nguyên</span> sẽ tự động gắn vào
            block buổi này (Session Linker).
          </p>
        </div>

        <DialogFooter className="items-center gap-2 sm:justify-between">
          <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Radio className="size-3" />
            Nguồn: <span className="font-mono">{s.source.channel}</span> · cập nhật {s.source.updated}
          </span>
          <span className="text-xs text-muted-foreground">
            Chưa rõ? Hỏi Companion:{" "}
            <kbd className="rounded border bg-muted px-1 py-0.5 font-mono text-[10px] text-foreground">
              /ask
            </kbd>
          </span>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function InfoCard({ icon: Icon, label, value, mono, wide }) {
  return (
    <div
      className={
        "flex items-center gap-2.5 rounded-lg border bg-muted/40 px-3 py-2.5 " +
        (wide ? "col-span-2" : "")
      }
    >
      <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <Icon className="size-4" />
      </div>
      <div className="min-w-0">
        <div className="text-[10px] font-semibold tracking-wider text-primary uppercase">
          {label}
        </div>
        <div className={"truncate text-sm font-medium " + (mono ? "font-mono" : "")}>{value}</div>
      </div>
    </div>
  );
}

function SectionTitle({ icon: Icon, children }) {
  return (
    <h3 className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
      <Icon className="size-3.5" /> {children}
    </h3>
  );
}
