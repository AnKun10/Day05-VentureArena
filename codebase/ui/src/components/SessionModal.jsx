import { Clapperboard, FileText, Presentation, Radio, Video } from "lucide-react";
import { SESSION_TYPES, fmtDM } from "../data/mock.js";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

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
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-[560px]">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <Badge
              className="font-mono"
              style={{ background: t.color + "24", color: t.color }}
            >
              {s.code}
            </Badge>
            <span className="text-xs font-medium text-muted-foreground">{t.label}</span>
          </div>
          <DialogTitle className="text-base leading-snug">{s.title}</DialogTitle>
          <DialogDescription className="font-mono text-xs">
            {DAY_FULL[s.date.getDay()]}, {fmtDM(s.date)} · {s.timeLabel}
          </DialogDescription>
        </DialogHeader>

        {/* Info */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-2.5 text-sm">
          <InfoRow label="Hình thức" value={s.format === "Offline" ? "Offline" : "Online (Zoom)"} />
          <InfoRow label="Địa điểm / Lớp" value={s.location ? `${s.location} · ${s.cls}` : s.cls} />
          <InfoRow label="Phụ trách / Diễn giả" value={s.host} />
          <InfoRow label="Mã buổi" value={s.code} mono />
        </div>

        {s.desc && <p className="text-sm leading-relaxed text-muted-foreground">{s.desc}</p>}

        <Separator />

        {/* Links */}
        <div>
          <SectionTitle>Tài liệu buổi học</SectionTitle>
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
            Slide/record đăng tại <span className="font-mono">#tài-nguyên</span> sẽ tự động gắn
            vào block buổi này (Session Linker).
          </p>
        </div>

        {/* FAQ */}
        {s.faqs?.length > 0 && (
          <div>
            <SectionTitle>Câu hỏi thường gặp · {t.label}</SectionTitle>
            <Accordion>
              {s.faqs.map((f, i) => (
                <AccordionItem key={i} value={String(i)}>
                  <AccordionTrigger>{f.q}</AccordionTrigger>
                  <AccordionContent className="text-muted-foreground">{f.a}</AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </div>
        )}

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

function InfoRow({ label, value, mono }) {
  return (
    <div>
      <div className="text-[10px] font-medium tracking-wider text-muted-foreground uppercase">
        {label}
      </div>
      <div className={"mt-0.5 text-sm " + (mono ? "font-mono" : "")}>{value}</div>
    </div>
  );
}

function SectionTitle({ children }) {
  return (
    <h3 className="mb-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
      {children}
    </h3>
  );
}
