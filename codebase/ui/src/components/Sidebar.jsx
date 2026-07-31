import { useEffect, useState } from "react";
import { Bookmark, CalendarDays, Library, MessagesSquare, Newspaper, Settings } from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

const NAV = [
  { id: "calendar", icon: CalendarDays, label: "Lịch học" },
  { id: "resources", icon: Library, label: "Tài nguyên" },
  { id: "news", icon: Newspaper, label: "Bản tin" },
  { id: "bookmarks", icon: Bookmark, label: "Đã lưu" },
  { id: "settings", icon: Settings, label: "Cài đặt" },
];

function initials(name) {
  const parts = (name || "?").trim().split(/\s+/);
  return ((parts[0]?.[0] || "") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

function UserAvatar({ user }) {
  const [broken, setBroken] = useState(false);
  const url = user?.avatar_url;
  if (url && !broken) {
    return (
      <img
        src={url}
        alt={user?.name || ""}
        onError={() => setBroken(true)}
        className="size-9 shrink-0 rounded-lg object-cover"
      />
    );
  }
  return (
    <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary text-sm font-semibold text-primary-foreground">
      {initials(user?.name)}
    </div>
  );
}

export default function Sidebar({ page, onNavigate, users, currentUser }) {
  const me = users?.find((u) => u.user_id === currentUser) ?? null;
  const [cohort, setCohort] = useState(null);

  // Cohort hiển thị dưới tên lấy theo settings của user hiện tại (đổi user → đổi theo)
  useEffect(() => {
    if (currentUser == null) return;
    let alive = true;
    api
      .settings(currentUser)
      .then((s) => alive && setCohort(s?.cohort ?? null))
      .catch(() => alive && setCohort(null));
    return () => {
      alive = false;
    };
  }, [currentUser]);

  const displayName = me?.name || (currentUser != null ? String(currentUser) : "Companion");

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r bg-sidebar">
      <div className="flex items-center gap-2.5 px-4 pt-5 pb-4">
        <UserAvatar user={me} />
        <div className="min-w-0 leading-tight">
          <div className="truncate font-heading text-sm font-semibold">{displayName}</div>
          <div className="text-xs text-muted-foreground">
            AI Thực Chiến{cohort ? ` · Khoá ${cohort}` : ""}
          </div>
        </div>
      </div>

      <nav className="flex flex-col gap-0.5 px-2.5">
        {NAV.map(({ id, icon: Icon, label }) => {
          const active = page === id;
          return (
            <button
              key={id}
              onClick={() => onNavigate(id)}
              className={cn(
                "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
                active
                  ? "bg-secondary text-foreground"
                  : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground"
              )}
            >
              <Icon className={cn("size-4", active && "text-primary")} />
              {label}
            </button>
          );
        })}

        <div className="flex cursor-not-allowed items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium text-muted-foreground/50">
          <MessagesSquare className="size-4" />
          Hỏi đáp
          <Badge variant="outline" className="ml-auto text-[10px] text-muted-foreground">
            Trên Discord
          </Badge>
        </div>
      </nav>

      <div className="mt-auto px-3 pb-4">
        <div className="rounded-lg border bg-card/50 p-3">
          <Badge variant="secondary" className="mb-1.5 text-[10px] uppercase tracking-wide">
            Demo
          </Badge>
          <p className="text-xs leading-relaxed text-muted-foreground">
            Bản tin &amp; gợi ý lấy từ backend (offline → mock). Mở từ Discord bằng lệnh{" "}
            <kbd className="rounded border bg-muted px-1 py-0.5 font-mono text-[10px] text-foreground">
              /hub
            </kbd>
          </p>
        </div>
      </div>
    </aside>
  );
}
