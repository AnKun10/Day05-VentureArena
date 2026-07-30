import { Bot, CalendarDays, Library, MessagesSquare, Newspaper } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

const NAV = [
  { id: "calendar", icon: CalendarDays, label: "Lịch học" },
  { id: "resources", icon: Library, label: "Tài nguyên" },
  { id: "news", icon: Newspaper, label: "Bản tin" },
];

export default function Sidebar({ page, onNavigate }) {
  return (
    <aside className="flex w-60 shrink-0 flex-col border-r bg-sidebar">
      <div className="flex items-center gap-2.5 px-4 pt-5 pb-4">
        <div className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Bot className="size-5" />
        </div>
        <div className="leading-tight">
          <div className="font-heading text-sm font-semibold">Companion</div>
          <div className="text-xs text-muted-foreground">AI Thực Chiến · Cohort 3</div>
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
            Sắp có
          </Badge>
        </div>
      </nav>

      <div className="mt-auto px-3 pb-4">
        <div className="rounded-lg border bg-card/50 p-3">
          <Badge variant="secondary" className="mb-1.5 text-[10px] uppercase tracking-wide">
            Demo
          </Badge>
          <p className="text-xs leading-relaxed text-muted-foreground">
            Bản tin & gợi ý lấy từ backend (offline → mock). Mở từ Discord bằng lệnh{" "}
            <kbd className="rounded border bg-muted px-1 py-0.5 font-mono text-[10px] text-foreground">
              /hub
            </kbd>
          </p>
        </div>
      </div>
    </aside>
  );
}
