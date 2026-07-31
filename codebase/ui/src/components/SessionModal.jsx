import {
  BookOpenText,
  Building2,
  CalendarClock,
  Clapperboard,
  FileText,
  MapPin,
  Presentation,
  Radio,
  UserRound,
  Video,
} from "lucide-react";
import { SESSION_TYPES, fmtDM } from "../data/mock.js";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
  // SESSION_TYPES không có "OTHER" (buổi từ API) — dùng lại palette OH.
  const t = SESSION_TYPES[s.type] ?? SESSION_TYPES.OH;
  const available = LINK_DEFS.filter((l) => s.links?.[l.key]);
  const missing = LINK_DEFS.filter((l) => !s.links?.[l.key] && l.key !== "zoom");
  const hasSummary = Boolean(s.desc) || Boolean(s.summary?.length);
  const hasMaterials = Array.isArray(s.materials) && s.materials.length > 0;
  const openInNewTab = (url) => window.open(url, "_blank", "noopener,noreferrer");

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[85vh] gap-5 overflow-y-auto p-6 sm:max-w-[600px]">
        {/* Header thoáng: badge → title lớn → ngày giờ nổi bật */}
        <DialogHeader className="gap-2.5">
          <div className="flex items-center gap-2">
            <Badge className="font-mono" style={{ background: t.color + "1a", color: t.color }}>
              {s.code}
            </Badge>
            <span className="text-xs font-medium" style={{ color: t.color }}>
              {t.label}
            </span>
          </div>
          <DialogTitle className="text-xl leading-snug">{s.title}</DialogTitle>
          <div className="flex items-center gap-2 text-sm font-medium text-primary">
            <CalendarClock className="size-4" />
            <span className="font-mono">
              {DAY_FULL[s.date.getDay()]}, {fmtDM(s.date)} · {s.timeLabel}
            </span>
          </div>
        </DialogHeader>

        {/* Một panel mềm duy nhất thay vì 5 ô đóng khung */}
        <div className="grid grid-cols-2 gap-x-6 gap-y-4 rounded-xl bg-muted/50 p-4 sm:grid-cols-3">
          <Info
            icon={s.format === "Offline" ? Building2 : Video}
            label="Hình thức"
            value={s.format === "Offline" ? "Offline" : "Online (Zoom)"}
          />
          <Info
            icon={MapPin}
            label="Địa điểm / Lớp"
            value={s.location ? `${s.location} · ${s.cls}` : s.cls}
          />
          <Info icon={UserRound} label="Phụ trách / Diễn giả" value={s.host} />
        </div>

        {/* Tóm tắt nội dung — API thật không có desc/summary → ẩn cả block */}
        {hasSummary && (
          <div>
            <SectionTitle icon={BookOpenText}>Tóm tắt nội dung</SectionTitle>
            {s.desc && (
              <p className="mb-2.5 text-sm leading-relaxed text-muted-foreground">{s.desc}</p>
            )}
            {s.summary?.length > 0 && (
              <ul className="space-y-2">
                {s.summary.map((line, i) => (
                  <li key={i} className="flex gap-2.5 text-sm leading-relaxed">
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
        )}

        {/* Tài liệu */}
        <div>
          <SectionTitle icon={FileText}>Tài liệu buổi học</SectionTitle>
          {hasMaterials ? (
            <div className="flex flex-wrap gap-2">
              {s.links?.zoom && (
                <Button variant="default" size="sm" onClick={() => openInNewTab(s.links.zoom)}>
                  <Video /> Tham gia Zoom
                </Button>
              )}
              {s.materials.map((m, i) => (
                <Button key={i} variant="outline" size="sm" onClick={() => openInNewTab(m.url)}>
                  <FileText /> {m.label}
                </Button>
              ))}
            </div>
          ) : s.fromApi ? (
            // Buổi từ API không có materials — chỉ hiện thứ có thật (Zoom), không
            // vẽ placeholder Slide/Record/Tài liệu "chưa có" (không có trong API schema).
            s.links?.zoom ? (
              <div className="flex flex-wrap gap-2">
                <Button variant="default" size="sm" onClick={() => openInNewTab(s.links.zoom)}>
                  <Video /> Tham gia Zoom
                </Button>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Chưa có tài liệu</p>
            )
          ) : (
            <div className="flex flex-wrap gap-2">
              {available.map(({ key, label, icon: Icon }) => (
                <Button
                  key={key}
                  variant={key === "zoom" ? "default" : "outline"}
                  size="sm"
                  onClick={
                    key === "zoom" && s.links?.zoom
                      ? () => openInNewTab(s.links.zoom)
                      : (e) => e.preventDefault()
                  }
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
          )}
          <p className="mt-2 text-xs text-muted-foreground">
            Slide/record đăng tại <span className="font-mono">#tài-nguyên</span> sẽ tự động gắn vào
            block buổi này (Session Linker).
          </p>
        </div>

        <DialogFooter className="-mx-6 -mb-6 items-center gap-2 px-6 sm:justify-between">
          <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
            {s.source ? (
              <>
                <Radio className="size-3" />
                Nguồn: <span className="font-mono">{s.source.channel}</span> · cập nhật{" "}
                {s.source.updated}
              </>
            ) : s.jump_url ? (
              <a
                href={s.jump_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-primary hover:underline"
              >
                <Radio className="size-3" />
                Xem thông báo gốc
              </a>
            ) : null}
          </span>
          <span className="text-xs text-muted-foreground">
            Chưa rõ? Hỏi Companion:{" "}
            <kbd className="rounded border bg-background px-1 py-0.5 font-mono text-[10px] text-foreground">
              /ask
            </kbd>
          </span>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Info({ icon: Icon, label, value }) {
  return (
    <div className="min-w-0">
      <div className="flex items-center gap-1.5 text-[10px] font-semibold tracking-wider text-primary uppercase">
        <Icon className="size-3.5 shrink-0" /> {label}
      </div>
      <div className="mt-1 text-sm font-medium">{value}</div>
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
