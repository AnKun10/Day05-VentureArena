import { useEffect, useMemo, useRef, useState } from "react";
import {
  NEWS,
  NEWS_CATEGORIES,
  SESSIONS,
  SESSION_TYPES,
  addDays,
  fmtDM,
  isSameDay,
  isHot,
} from "../data/mock.js";
import Icon from "../components/Icons.jsx";

const catOf = (id) => NEWS_CATEGORIES.find((c) => c.id === id);
const DAY_LABELS = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];
const SESSION_RE = /\b(LT|Lab|WS|OH|MD)-\d+\b/i;
const PER_PAGE = 20;

/** Thời điểm bắt đầu thật của buổi học (date là 00:00, start là giờ thập phân). */
const startAt = (s) => new Date(s.date.getTime() + s.start * 3600000);

function whenLabel(s) {
  const today = new Date();
  if (isSameDay(s.date, today)) return "Hôm nay";
  if (isSameDay(s.date, addDays(today, 1))) return "Ngày mai";
  return `${DAY_LABELS[s.date.getDay()]}, ${fmtDM(s.date)}`;
}

/** Mã buổi được nhắc tới trong tin → cho phép nhảy thẳng sang Lịch học. */
function linkedSession(n) {
  const hit = `${n.title} ${n.summary}`.match(SESSION_RE)?.[0];
  if (!hit) return null;
  return SESSIONS.find((s) => s.code.toLowerCase() === hit.toLowerCase())?.code ?? null;
}

export default function NewsPage({ query = "", onAsk, onOpenSession }) {
  const [cat, setCat] = useState("all");
  const [sort, setSort] = useState("new"); // "new" | "hot"
  const [page, setPage] = useState(1);
  const topRef = useRef(null);

  // Buổi học gần nhất chưa diễn ra — thông tin học viên cần nhất mỗi ngày.
  const next = useMemo(() => {
    const now = new Date();
    return SESSIONS.filter((s) => startAt(s) >= now).sort((a, b) => startAt(a) - startAt(b))[0];
  }, []);

  const feed = useMemo(() => {
    const q = query.trim().toLowerCase();
    let out = NEWS.filter((n) => cat === "all" || n.cat === cat);
    if (q) {
      out = out.filter((n) =>
        [n.title, n.summary, n.channel, n.author].join(" ").toLowerCase().includes(q)
      );
    }
    return sort === "hot"
      ? [...out].sort((a, b) => b.hearts + b.comments - (a.hearts + a.comments))
      : out;
  }, [cat, sort, query]);

  // Đổi loại tin / thứ tự / từ khoá → luôn về trang 1, nếu không sẽ rơi vào
  // cảnh "lọc xong thấy trống" chỉ vì đang đứng ở trang 3 của kết quả cũ.
  useEffect(() => setPage(1), [cat, sort, query]);

  const pageCount = Math.max(1, Math.ceil(feed.length / PER_PAGE));
  const current = Math.min(page, pageCount);
  const from = (current - 1) * PER_PAGE;
  const pageItems = feed.slice(from, from + PER_PAGE);

  function goPage(p) {
    const next = Math.min(pageCount, Math.max(1, p));
    setPage(next);
    // Cuộn về đầu danh sách (vùng cuộn là <main>), không phải cả cửa sổ.
    topRef.current?.closest("main")?.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <div ref={topRef} className="w-full px-4 py-5 lg:px-6">
      {next && <NextSessionBar s={next} onOpenSession={onOpenSession} onAsk={onAsk} />}

      {/* Bộ lọc: loại tin (tabs) tách khỏi thứ tự sắp xếp (segmented) —
          bản cũ trộn hai loại điều khiển này vào cùng một hàng gạch chân. */}
      <div className="sticky top-0 z-10 -mx-4 mt-5 bg-canvas/92 px-4 pb-2 pt-3 backdrop-blur lg:-mx-6 lg:px-6">
        <div className="flex items-end justify-between gap-3 border-b border-line">
          <div className="-mb-px flex min-w-0 flex-1 gap-0.5 overflow-x-auto">
            <Tab active={cat === "all"} onClick={() => setCat("all")} label="Tất cả" count={NEWS.length} />
            {NEWS_CATEGORIES.map((c) => (
              <Tab
                key={c.id}
                active={cat === c.id}
                onClick={() => setCat(c.id)}
                label={c.label}
                color={c.color}
                count={NEWS.filter((n) => n.cat === c.id).length}
              />
            ))}
          </div>

          <div className="mb-1.5 flex shrink-0 rounded-lg bg-surface-2 p-0.5">
            <SortBtn active={sort === "new"} onClick={() => setSort("new")}>
              Mới nhất
            </SortBtn>
            <SortBtn active={sort === "hot"} onClick={() => setSort("hot")}>
              Nổi bật
            </SortBtn>
          </div>
        </div>
      </div>

      {query && (
        <p className="mb-2 text-sm text-ink-2">
          <span className="font-semibold text-ink">{feed.length}</span> tin khớp “{query}”
        </p>
      )}

      <div className="overflow-hidden rounded-xl border border-line bg-surface shadow-card">
        {pageItems.map((n, i) => (
          <NewsRow key={n.id} n={n} first={i === 0} onOpenSession={onOpenSession} onAsk={onAsk} />
        ))}
        {feed.length === 0 && (
          <p className="py-12 text-center text-base text-ink-3">
            {query ? `Không có tin nào khớp “${query}”.` : "Chưa có tin thuộc loại này."}
          </p>
        )}
      </div>

      {feed.length > 0 && (
        <Pager
          from={from + 1}
          to={from + pageItems.length}
          total={feed.length}
          page={current}
          pageCount={pageCount}
          onPage={goPage}
        />
      )}
    </div>
  );
}

/** Thanh "Tiếp theo" — trả lời sẵn câu hỏi phổ biến nhất của học viên mỗi ngày. */
function NextSessionBar({ s, onOpenSession, onAsk }) {
  const t = SESSION_TYPES[s.type];
  return (
    <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-card">
      <div className="h-0.5 w-full" style={{ background: t.color }} />
      <div className="flex flex-wrap items-center gap-x-4 gap-y-3 p-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 text-2xs font-bold uppercase tracking-[0.08em]">
            <span className="relative flex h-1.5 w-1.5">
              <span
                className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-60"
                style={{ background: t.color }}
              />
              <span
                className="relative inline-flex h-1.5 w-1.5 rounded-full"
                style={{ background: t.color }}
              />
            </span>
            <span style={{ color: t.color }}>Buổi tiếp theo</span>
            <span className="text-line-2">·</span>
            <span className="text-ink-2">
              {whenLabel(s)}, {s.timeLabel}
            </span>
          </div>

          <h2 className="mt-1.5 truncate text-lg font-bold text-ink">{s.title}</h2>

          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-2">
            <span
              className="rounded px-1.5 py-0.5 text-2xs font-bold"
              style={{ background: t.color + "1a", color: t.color }}
            >
              {s.code} · {t.label}
            </span>
            <span className="flex items-center gap-1">
              {s.format === "Offline" ? (
                <Icon.Pin className="h-3.5 w-3.5 text-ink-3" />
              ) : (
                <Icon.Video className="h-3.5 w-3.5 text-ink-3" />
              )}
              {s.format === "Offline" ? s.location : "Online qua Zoom"}
            </span>
            <span className="flex items-center gap-1">
              <Icon.User className="h-3.5 w-3.5 text-ink-3" />
              {s.host}
            </span>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {s.links?.zoom && (
            <a
              href={s.links.zoom}
              onClick={(e) => e.preventDefault()}
              className="rounded-lg bg-brand px-3.5 py-2 text-base font-semibold text-white transition-colors hover:bg-brand-hover"
            >
              Vào Zoom
            </a>
          )}
          <button
            onClick={() => onOpenSession?.(s.code)}
            className="flex items-center gap-1 rounded-lg border border-line px-3 py-2 text-base font-semibold text-ink-2 transition-colors hover:border-brand-line hover:bg-brand-soft hover:text-brand"
          >
            Chi tiết
            <Icon.ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      <button
        onClick={() => onAsk?.(`${s.code} diễn ra lúc mấy giờ và cần chuẩn bị gì?`)}
        className="flex w-full items-center gap-1.5 border-t border-line px-4 py-2 text-left text-xs text-ink-3 transition-colors hover:bg-surface-2 hover:text-brand"
      >
        <Icon.Sparkle className="h-3.5 w-3.5" />
        Chưa rõ gì về buổi này? <span className="font-semibold">Hỏi Companion</span>
      </button>
    </section>
  );
}

function NewsRow({ n, first, onOpenSession, onAsk }) {
  const [open, setOpen] = useState(false);
  const c = catOf(n.cat);
  const session = linkedSession(n);

  return (
    <div className={first ? "" : "border-t border-line"}>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className={
          "group flex w-full gap-3 px-4 py-3 text-left transition-colors hover:bg-surface-2 " +
          (open ? "bg-surface-2" : "")
        }
      >
        {/* Cột loại tin cố định → mắt quét theo màu, không phải đọc từng dòng */}
        <span className="w-[88px] shrink-0 pt-0.5">
          <span
            className="block truncate rounded px-1.5 py-1 text-center text-2xs font-bold uppercase leading-none"
            style={{ background: c.color + "1a", color: c.color }}
          >
            {c.label}
          </span>
        </span>

        <span className="min-w-0 flex-1">
          {/* Dòng 1: tiêu đề + trạng thái */}
          <span className="flex items-start gap-2">
            <span className="min-w-0 flex-1 text-base font-semibold text-ink group-hover:text-brand">
              {n.title}
            </span>
            {n.open && (
              <span className="mt-0.5 shrink-0 rounded border border-brand-line bg-brand-soft px-1.5 py-0.5 text-2xs font-semibold text-brand">
                Chờ TA
              </span>
            )}
            {isHot(n) && (
              <Icon.Flame className="mt-0.5 h-4 w-4 shrink-0 text-warn" title="Đang được quan tâm" />
            )}
          </span>

          {/* Dòng 2: tóm tắt — có không gian riêng, không còn tranh chỗ với meta */}
          <span
            className={
              "mt-1 block text-sm leading-relaxed text-ink-2 " + (open ? "" : "line-clamp-1")
            }
          >
            {n.summary}
          </span>

          {/* Dòng 3: meta — tách hẳn xuống dòng riêng, cỡ nhỏ nhất */}
          <span className="mt-1.5 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-2xs text-ink-3">
            <span className="font-medium text-ink-2">{n.channel}</span>
            <span className="text-line-2">·</span>
            <span>
              {n.author}
              {n.role && n.role !== "Học viên" && (
                <span className="ml-1 rounded bg-surface-3 px-1 py-px font-semibold text-ink-2">
                  {n.role}
                </span>
              )}
            </span>
            <span className="text-line-2">·</span>
            <span>{n.time}</span>
            <span className="ml-auto flex items-center gap-2.5">
              <span className="flex items-center gap-1">
                <Icon.Heart className="h-3.5 w-3.5" />
                {n.hearts}
              </span>
              <span className="flex items-center gap-1">
                <Icon.Comment className="h-3.5 w-3.5" />
                {n.comments}
              </span>
              <Icon.ChevronDown
                className={"h-3.5 w-3.5 transition-transform " + (open ? "rotate-180" : "")}
              />
            </span>
          </span>
        </span>
      </button>

      {/* Mở rộng — bản cũ dòng tin là link chết, bấm không ra gì */}
      {open && (
        <div className="flex flex-wrap items-center gap-2 border-t border-line bg-surface-2 px-4 py-2.5 pl-[116px]">
          <a
            href={n.url}
            onClick={(e) => e.preventDefault()}
            className="flex items-center gap-1.5 rounded-lg border border-line bg-surface px-2.5 py-1.5 text-xs font-semibold text-ink-2 transition-colors hover:border-brand-line hover:text-brand"
          >
            <Icon.External className="h-3.5 w-3.5" />
            Mở trong Discord
          </a>
          {session && (
            <button
              onClick={() => onOpenSession?.(session)}
              className="flex items-center gap-1.5 rounded-lg border border-line bg-surface px-2.5 py-1.5 text-xs font-semibold text-ink-2 transition-colors hover:border-brand-line hover:text-brand"
            >
              <Icon.Calendar className="h-3.5 w-3.5" />
              Xem buổi {session}
            </button>
          )}
          <button
            onClick={() => onAsk?.(n.title)}
            className="flex items-center gap-1.5 rounded-lg border border-line bg-surface px-2.5 py-1.5 text-xs font-semibold text-ink-2 transition-colors hover:border-brand-line hover:text-brand"
          >
            <Icon.Sparkle className="h-3.5 w-3.5" />
            Hỏi Companion
          </button>
          {n.open && (
            <span className="ml-auto text-2xs text-ink-3">
              Câu hỏi chưa có trả lời chính thức — đã vào hàng đợi TA
            </span>
          )}
        </div>
      )}
    </div>
  );
}

/** Dãy số trang có rút gọn: 1 … 4 5 6 … 12 (luôn giữ trang đầu/cuối + lân cận). */
function pageList(page, pageCount) {
  const keep = new Set([1, pageCount, page, page - 1, page + 1]);
  if (page <= 3) [2, 3, 4].forEach((p) => keep.add(p));
  if (page >= pageCount - 2) [pageCount - 3, pageCount - 2, pageCount - 1].forEach((p) => keep.add(p));

  const nums = [...keep].filter((p) => p >= 1 && p <= pageCount).sort((a, b) => a - b);
  const out = [];
  nums.forEach((p, i) => {
    if (i > 0 && p - nums[i - 1] > 1) out.push(`gap-${p}`);
    out.push(p);
  });
  return out;
}

function Pager({ from, to, total, page, pageCount, onPage }) {
  return (
    <nav
      className="mt-3 grid grid-cols-1 items-center gap-2 sm:grid-cols-[1fr_auto_1fr]"
      aria-label="Phân trang bản tin"
    >
      <p className="text-center text-xs text-ink-3 sm:text-left">
        Đang xem <span className="font-semibold text-ink-2">{from}–{to}</span> trong{" "}
        <span className="font-semibold text-ink-2">{total}</span> tin
        {pageCount > 1 && ` · trang ${page}/${pageCount}`}
      </p>

      {pageCount > 1 && (
        <div className="flex flex-wrap items-center justify-center gap-1">
          <PagerBtn onClick={() => onPage(page - 1)} disabled={page === 1} label="Trang trước">
            <Icon.ChevronLeft className="h-4 w-4" />
          </PagerBtn>

          {pageList(page, pageCount).map((p) =>
            typeof p === "string" ? (
              <span key={p} className="px-1 text-xs text-ink-3">
                …
              </span>
            ) : (
              <button
                key={p}
                onClick={() => onPage(p)}
                aria-current={p === page ? "page" : undefined}
                className={
                  "min-w-8 rounded-lg border px-2 py-1.5 text-xs font-semibold tabular-nums transition-colors " +
                  (p === page
                    ? "border-brand bg-brand text-white"
                    : "border-line bg-surface text-ink-2 hover:border-brand-line hover:bg-brand-soft hover:text-brand")
                }
              >
                {p}
              </button>
            )
          )}

          <PagerBtn onClick={() => onPage(page + 1)} disabled={page === pageCount} label="Trang sau">
            <Icon.ChevronRight className="h-4 w-4" />
          </PagerBtn>
        </div>
      )}
    </nav>
  );
}

function PagerBtn({ onClick, disabled, label, children }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      className="rounded-lg border border-line bg-surface px-2 py-1.5 text-ink-2 transition-colors hover:border-brand-line hover:bg-brand-soft hover:text-brand disabled:pointer-events-none disabled:opacity-40"
    >
      {children}
    </button>
  );
}

function Tab({ active, onClick, label, color = "#8b98b0", count }) {
  return (
    <button
      onClick={onClick}
      className={
        "relative flex shrink-0 items-center gap-1.5 border-b-2 px-2.5 py-2 text-sm font-medium transition-colors " +
        (active
          ? "border-brand text-ink"
          : "border-transparent text-ink-3 hover:text-ink-2")
      }
    >
      <span
        className="h-1.5 w-1.5 shrink-0 rounded-full"
        style={{ background: color, opacity: active ? 1 : 0.45 }}
      />
      {label}
      {count != null && (
        <span
          className={
            "rounded px-1 py-px text-2xs font-semibold " +
            (active ? "bg-brand-soft text-brand" : "bg-surface-2 text-ink-3")
          }
        >
          {count}
        </span>
      )}
    </button>
  );
}

function SortBtn({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={
        "rounded-md px-2.5 py-1 text-xs font-semibold transition-colors " +
        (active ? "bg-surface text-ink shadow-card" : "text-ink-3 hover:text-ink-2")
      }
    >
      {children}
    </button>
  );
}
