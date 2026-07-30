const NAV = [
  { id: "calendar", icon: "📅", label: "Lịch học" },
  { id: "resources", icon: "📚", label: "Tài nguyên" },
  { id: "news", icon: "📰", label: "Bản tin" },
];

export default function Sidebar({ page, onNavigate }) {
  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-[#232838] bg-[#12141c]">
      <div className="flex items-center gap-3 px-5 pt-6 pb-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#5865f2] text-xl shadow-lg shadow-[#5865f2]/25">
          🤖
        </div>
        <div>
          <div className="text-[15px] font-bold tracking-wide text-white">Companion</div>
          <div className="text-[11px] text-zinc-500">AI Thực Chiến · Cohort 3</div>
        </div>
      </div>

      <nav className="mt-2 flex flex-col gap-1 px-3">
        {NAV.map((item) => {
          const active = page === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-left text-[14px] font-medium transition-colors " +
                (active
                  ? "bg-[#5865f2]/15 text-[#aab4ff]"
                  : "text-zinc-400 hover:bg-white/5 hover:text-zinc-200")
              }
            >
              <span className="text-base">{item.icon}</span>
              {item.label}
              {active && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-[#5865f2]" />}
            </button>
          );
        })}

        <div className="mt-1 flex cursor-not-allowed items-center gap-3 rounded-lg px-3 py-2.5 text-[14px] font-medium text-zinc-600">
          <span className="text-base">💬</span>
          Hỏi đáp
          <span className="ml-auto rounded-full border border-zinc-700 px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-zinc-500">
            sắp có
          </span>
        </div>
      </nav>

      <div className="mt-auto px-4 pb-5">
        <div className="rounded-xl border border-[#232838] bg-[#171a24] p-3 text-[11px] leading-relaxed text-zinc-500">
          <span className="mb-1 inline-block rounded bg-amber-500/15 px-1.5 py-0.5 font-semibold text-amber-400">
            DEMO
          </span>
          <p>
            Mock data — chưa nối backend. Mở từ Discord bằng lệnh{" "}
            <code className="rounded bg-black/40 px-1 text-zinc-400">/hub</code>
          </p>
        </div>
      </div>
    </aside>
  );
}
