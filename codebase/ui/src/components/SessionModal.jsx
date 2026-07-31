import { useState } from "react";
import {
  BookOpenText,
  Building2,
  CalendarClock,
  Clapperboard,
  FileText,
  MapPin,
  Pencil,
  Presentation,
  Radio,
  RotateCcw,
  Trash2,
  UserRound,
  Video,
} from "lucide-react";
import { SESSION_TYPES, fmtDM } from "../data/mock.js";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";

const DAY_FULL = ["Chủ nhật", "Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7"];
const TYPES = ["LT", "LAB", "WS", "OH", "MD", "OTHER"];

const LINK_DEFS = [
  { key: "zoom", label: "Tham gia Zoom", icon: Video },
  { key: "slide", label: "Slide", icon: Presentation },
  { key: "record", label: "Record", icon: Clapperboard },
  { key: "materials", label: "Tài liệu", icon: FileText },
];

const toISO = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

// Chế độ sửa: form cho các trường buổi học. onSave nhận patch (buổi có sẵn) hoặc
// custom fields (buổi tự thêm — isNew). onHide/onRevert cho buổi có sẵn.
export default function SessionModal({ session: s, onClose, editable, onSave, onHide, onRevert, isNew }) {
  const t = SESSION_TYPES[s.type] ?? SESSION_TYPES.OTHER;
  const [editing, setEditing] = useState(Boolean(isNew));
  const [f, setF] = useState({
    date: isNew ? toISO(s.date) : "",
    type: s.type || "OTHER",
    title: s.title || "",
    start: s.rawStart || "",
    end: s.rawEnd || "",
    location: s.location || "",
    format: s.format || "Offline",
    host: s.host || "",
    zoom_url: s.links?.zoom || "",
  });
  const set = (k) => (e) => setF((p) => ({ ...p, [k]: e.target.value }));

  const available = LINK_DEFS.filter((l) => s.links?.[l.key]);
  const missing = LINK_DEFS.filter((l) => !s.links?.[l.key] && l.key !== "zoom");
  const hasMaterials = Array.isArray(s.materials) && s.materials.length > 0;
  const openInNewTab = (url) => window.open(url, "_blank", "noopener,noreferrer");

  const save = () => {
    if (isNew) {
      onSave({
        date: f.date, type: f.type, title: f.title, start: f.start || null,
        end: f.end || null, location: f.location || null, format: f.format,
        host: f.host || null, zoom_url: f.zoom_url || null,
      });
    } else {
      onSave({
        title: f.title, start: f.start || null, end: f.end || null,
        location: f.location || null, format: f.format, host: f.host || null,
        zoom_url: f.zoom_url || null,
      });
    }
  };

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[85vh] gap-5 overflow-y-auto p-6 sm:max-w-[600px]">
        <DialogHeader className="gap-2.5">
          <div className="flex flex-wrap items-center gap-2">
            <Badge className="font-mono" style={{ background: t.color + "1a", color: t.color }}>
              {s.code}
            </Badge>
            <span className="text-xs font-medium" style={{ color: t.color }}>{t.label}</span>
            {s.edited && !isNew && (
              <Badge variant="outline" className="text-[10px] text-amber-600">✎ đã sửa</Badge>
            )}
            {s.custom && <Badge variant="outline" className="text-[10px] text-primary">＋ tự thêm</Badge>}
            {/* Nút chỉnh sửa cá nhân (chỉ khi có user) */}
            {editable && !editing && (
              <div className="ml-auto flex gap-1.5">
                <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
                  <Pencil /> Sửa
                </Button>
                {s.edited && !s.custom && (
                  <Button variant="ghost" size="sm" onClick={onRevert} title="Khôi phục bản gốc">
                    <RotateCcw /> Khôi phục
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-destructive hover:text-destructive"
                  onClick={s.custom ? onRevert : onHide}
                  title={s.custom ? "Xoá buổi tự thêm" : "Ẩn buổi này khỏi lịch của bạn"}
                >
                  <Trash2 /> Xoá
                </Button>
              </div>
            )}
          </div>
          <DialogTitle className="text-xl leading-snug">{isNew ? "Thêm buổi mới" : s.title}</DialogTitle>
          {!isNew && (
            <div className="flex items-center gap-2 text-sm font-medium text-primary">
              <CalendarClock className="size-4" />
              <span className="font-mono">
                {DAY_FULL[s.date.getDay()]}, {fmtDM(s.date)} · {s.timeLabel}
              </span>
            </div>
          )}
        </DialogHeader>

        {editing ? (
          <div className="grid grid-cols-2 gap-3">
            {isNew && (
              <>
                <Field label="Ngày"><Input type="date" value={f.date} onChange={set("date")} /></Field>
                <Field label="Loại">
                  <select className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                          value={f.type} onChange={set("type")}>
                    {TYPES.map((x) => <option key={x} value={x}>{x}</option>)}
                  </select>
                </Field>
              </>
            )}
            <Field label="Tiêu đề" full><Input value={f.title} onChange={set("title")} /></Field>
            <Field label="Giờ bắt đầu"><Input placeholder="HH:MM" value={f.start} onChange={set("start")} /></Field>
            <Field label="Giờ kết thúc"><Input placeholder="HH:MM" value={f.end} onChange={set("end")} /></Field>
            <Field label="Hình thức">
              <select className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                      value={f.format} onChange={set("format")}>
                <option value="Offline">Offline</option>
                <option value="Zoom">Online (Zoom)</option>
              </select>
            </Field>
            <Field label="Địa điểm / Phòng"><Input value={f.location} onChange={set("location")} /></Field>
            <Field label="Phụ trách / Giảng viên" full><Input value={f.host} onChange={set("host")} /></Field>
            <Field label="Link Zoom" full><Input value={f.zoom_url} onChange={set("zoom_url")} /></Field>
            <p className="col-span-2 text-xs text-muted-foreground">
              Thay đổi chỉ áp dụng cho <b>riêng bạn</b>, không ảnh hưởng người khác.
            </p>
            <div className="col-span-2 flex justify-end gap-2">
              {!isNew && (
                <Button variant="outline" size="sm" onClick={() => setEditing(false)}>Huỷ</Button>
              )}
              <Button size="sm" onClick={save}>Lưu</Button>
            </div>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-x-6 gap-y-4 rounded-xl bg-muted/50 p-4 sm:grid-cols-3">
              <Info icon={s.format === "Offline" ? Building2 : Video} label="Hình thức"
                    value={s.format === "Offline" ? "Offline" : "Online (Zoom)"} />
              <Info icon={MapPin} label="Địa điểm / Lớp"
                    value={s.location ? `${s.location} · ${s.cls}` : s.cls} />
              <Info icon={UserRound} label="Phụ trách / Diễn giả" value={s.host} />
            </div>

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
              ) : s.links?.zoom ? (
                <div className="flex flex-wrap gap-2">
                  <Button variant="default" size="sm" onClick={() => openInNewTab(s.links.zoom)}>
                    <Video /> Tham gia Zoom
                  </Button>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Chưa có tài liệu</p>
              )}
              <p className="mt-2 text-xs text-muted-foreground">
                Slide/record đăng tại <span className="font-mono">#tài-nguyên</span> sẽ tự động gắn vào
                block buổi này.
              </p>
            </div>

            <DialogFooter className="-mx-6 -mb-6 items-center gap-2 px-6 sm:justify-between">
              <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                {s.jump_url ? (
                  <a href={s.jump_url} target="_blank" rel="noreferrer"
                     className="inline-flex items-center gap-1.5 text-primary hover:underline">
                    <Radio className="size-3" /> Xem thông báo gốc
                  </a>
                ) : null}
              </span>
              <span className="text-xs text-muted-foreground">
                Chưa rõ? Hỏi Companion:{" "}
                <kbd className="rounded border bg-background px-1 py-0.5 font-mono text-[10px] text-foreground">/ask</kbd>
              </span>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

function Field({ label, full, children }) {
  return (
    <div className={full ? "col-span-2" : ""}>
      <div className="mb-1 text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">{label}</div>
      {children}
    </div>
  );
}

function Info({ icon: Icon, label, value }) {
  return (
    <div className="min-w-0">
      <div className="flex items-center gap-1.5 text-[10px] font-semibold tracking-wider text-primary uppercase">
        <Icon className="size-3.5 shrink-0" /> {label}
      </div>
      <div className="mt-1 text-sm font-medium">{value || "—"}</div>
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
