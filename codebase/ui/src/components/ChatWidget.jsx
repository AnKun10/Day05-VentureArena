import { useEffect, useRef, useState } from "react";
import { ask, reportWrong, isMock } from "../api/client.js";
import { DEMO_QUESTIONS } from "../api/mockAsk.js";
import Icon from "./Icons.jsx";

// ============================================================
// CHAT WIDGET — mặt tiền của QUYẾT ĐỊNH AI TRUNG TÂM.
// Mỗi action (answer / clarify / refuse) render thành một loại card
// nhìn khác hẳn nhau, để người xem phân biệt được quyết định từ xa.
// Nguyên tắc HAX áp dụng: #1 scope · #2 citation · #3 báo sai · #4 handoff · #5 ngày cập nhật
//
// Bố cục: bản cũ có 5 tầng khung (header + banner phạm vi + hội thoại +
// demo strip + input + caption) bóp vùng đọc còn rất hẹp, và banner với
// caption nói trùng ý nhau. Giờ phần "phạm vi" nằm trong lời chào (nói MỘT
// lần), demo strip tự thu lại sau câu hỏi đầu tiên.
// ============================================================

export default function ChatWidget({ open, prefill, onToggle, onClose, onOpenCitation, onEscalate }) {
  const [messages, setMessages] = useState([{ role: "bot", kind: "greeting" }]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [showDemo, setShowDemo] = useState(false);
  // câu hỏi gốc đang chờ user làm rõ — có giá trị nghĩa là đã clarify 1 lần rồi
  const [pendingClarify, setPendingClarify] = useState(null);
  const endRef = useRef(null);
  const inputRef = useRef(null);
  const sendRef = useRef(null);

  const fresh = messages.length === 1;

  async function send(text, clarifyContext = null) {
    const q = text.trim();
    if (!q || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setBusy(true);
    try {
      const res = await ask(q, clarifyContext);
      setPendingClarify(res.action === "clarify" ? q : null);
      if (res.escalated_to) onEscalate?.(res);
      setMessages((m) => [...m, { role: "bot", kind: "reply", question: q, res }]);
    } catch (err) {
      setMessages((m) => [...m, { role: "bot", kind: "error", text: String(err.message || err) }]);
    } finally {
      setBusy(false);
    }
  }
  sendRef.current = send;

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy, open]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  // Câu hỏi mồi từ nơi khác trong app ("Hỏi Companion về buổi này").
  useEffect(() => {
    if (prefill?.question) sendRef.current(prefill.question);
  }, [prefill?.at]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && onClose?.();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) {
    return (
      <button
        onClick={onToggle}
        className="fixed bottom-5 right-5 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-brand text-white shadow-float transition-colors hover:bg-brand-hover"
        aria-label="Mở chat với Companion"
      >
        <Icon.Chat className="h-6 w-6" />
      </button>
    );
  }

  return (
    <div className="fixed bottom-5 right-5 z-40 flex h-[min(640px,calc(100vh-2.5rem))] w-[400px] max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-2xl border border-line bg-surface shadow-float">
      {/* Header */}
      <div className="flex shrink-0 items-center gap-2.5 border-b border-line bg-surface px-4 py-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-brand to-brand-2 text-white">
          <Icon.Bot className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <div className="text-md font-bold text-ink">Companion</div>
          <div className="flex items-center gap-1.5 text-2xs font-medium text-ink-3">
            <span className={"h-1.5 w-1.5 rounded-full " + (isMock() ? "bg-warn" : "bg-ok")} />
            {isMock() ? "Chạy dữ liệu mẫu" : "Đang hoạt động"}
          </div>
        </div>
        <button
          onClick={onClose}
          className="ml-auto rounded-lg p-1.5 text-ink-3 hover:bg-surface-2 hover:text-ink"
          aria-label="Đóng chat"
        >
          <Icon.Close className="h-4 w-4" />
        </button>
      </div>

      {/* Luồng hội thoại */}
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto bg-canvas px-3.5 py-4">
        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="flex justify-end">
              <div className="max-w-[85%] rounded-2xl rounded-br-md bg-brand px-3.5 py-2 text-base leading-relaxed text-white">
                {m.text}
              </div>
            </div>
          ) : m.kind === "greeting" ? (
            <Greeting key={i} />
          ) : m.kind === "error" ? (
            <BotBubble key={i} tone="error">
              Không gọi được API: {m.text}
            </BotBubble>
          ) : (
            <ReplyCard
              key={i}
              question={m.question}
              res={m.res}
              canClarify={pendingClarify === m.question}
              onPickOption={(opt) => send(opt, m.question)}
              onOpenCitation={onOpenCitation}
              onEscalate={onEscalate}
            />
          )
        )}
        {busy && (
          <BotBubble>
            <span className="inline-flex gap-1 py-1">
              <Dot /> <Dot d="150ms" /> <Dot d="300ms" />
            </span>
          </BotBubble>
        )}
        <div ref={endRef} />
      </div>

      {/* Câu hỏi mẫu — mở sẵn khi chưa hỏi gì, sau đó thu lại thành 1 nút */}
      <div className="shrink-0 border-t border-line bg-surface px-3 pt-2">
        {fresh || showDemo ? (
          <div className="flex flex-wrap gap-1.5 pb-1">
            {DEMO_QUESTIONS.map((d) => (
              <button
                key={d.label}
                disabled={busy}
                onClick={() => send(d.q)}
                className="rounded-full border border-line bg-surface-2 px-2.5 py-1 text-xs font-medium text-ink-2 transition-colors hover:border-brand-line hover:bg-brand-soft hover:text-brand disabled:opacity-40"
              >
                {d.label}
              </button>
            ))}
          </div>
        ) : (
          <button
            onClick={() => setShowDemo(true)}
            className="flex items-center gap-1.5 pb-1 text-2xs font-semibold text-ink-3 hover:text-brand"
          >
            <Icon.Sparkle className="h-3.5 w-3.5" />
            Câu hỏi mẫu
          </button>
        )}
      </div>

      {/* Ô nhập */}
      <div className="shrink-0 bg-surface px-3 pb-3 pt-1.5">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input, pendingClarify);
          }}
          className="flex items-center gap-2 rounded-xl border border-line bg-surface-2 px-3 py-2 transition-colors focus-within:border-brand focus-within:bg-surface"
        >
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Hỏi về lịch học, tài liệu, thông báo…"
            className="min-w-0 flex-1 bg-transparent text-base text-ink outline-none placeholder:text-ink-3"
          />
          <button
            type="submit"
            disabled={busy || !input.trim()}
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-brand text-white transition-opacity hover:bg-brand-hover disabled:opacity-30"
            aria-label="Gửi câu hỏi"
          >
            <Icon.Send className="h-3.5 w-3.5" />
          </button>
        </form>
      </div>
    </div>
  );
}

/** HAX #1 — nói rõ phạm vi MỘT lần, trong lời chào, thay vì banner dính cứng. */
function Greeting() {
  return (
    <div className="rounded-2xl rounded-bl-md border border-line bg-surface px-3.5 py-3">
      <p className="text-base leading-relaxed text-ink">
        Chào bạn! Mình là <strong className="font-semibold">Companion</strong> — trợ lý của khoá AI
        Thực Chiến.
      </p>
      <ul className="mt-2.5 space-y-1.5 border-t border-line pt-2.5 text-xs leading-relaxed text-ink-2">
        <li className="flex gap-1.5">
          <Icon.Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ok" />
          Mình trả lời về <strong className="font-semibold text-ink">lịch học, tài liệu, thông
          báo</strong> — luôn kèm nguồn.
        </li>
        <li className="flex gap-1.5">
          <Icon.Ban className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-3" />
          Mình không tra web, không trả lời về điểm cá nhân.
        </li>
        <li className="flex gap-1.5">
          <Icon.Inbox className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-3" />
          Thiếu căn cứ thì mình chuyển TA phụ trách, không đoán bừa.
        </li>
      </ul>
    </div>
  );
}

// ---------- Card trả lời: hình dạng đổi theo action ----------

const TONE = {
  answer: {
    ring: "border-ok/25 bg-ok-soft",
    badge: "bg-ok/12 text-ok",
    label: "Có nguồn",
    Glyph: Icon.Check,
  },
  clarify: {
    ring: "border-warn/25 bg-warn-soft",
    badge: "bg-warn/12 text-warn",
    label: "Cần làm rõ",
    Glyph: Icon.Help,
  },
  escalate: {
    ring: "border-danger/25 bg-danger-soft",
    badge: "bg-danger/12 text-danger",
    label: "Đã chuyển TA",
    Glyph: Icon.Inbox,
  },
  scope: {
    ring: "border-line-2 bg-surface-2",
    badge: "bg-surface-3 text-ink-2",
    label: "Ngoài phạm vi",
    Glyph: Icon.Ban,
  },
};

function toneOf(res) {
  if (res.action === "answer") return "answer";
  if (res.action === "clarify") return "clarify";
  return res.escalated_to ? "escalate" : "scope";
}

function ReplyCard({ question, res, canClarify, onPickOption, onOpenCitation, onEscalate }) {
  const [reported, setReported] = useState(false);
  const t = TONE[toneOf(res)];

  async function flagWrong() {
    await reportWrong(res.trace_id, question, res.answer);
    setReported(true);
    // Đường "Correction" (R3): câu bị báo sai cũng vào hàng đợi để TA xác nhận.
    onEscalate?.(res);
  }

  return (
    <div className={"rounded-xl border px-3.5 py-3 " + t.ring}>
      <div className="mb-2 flex items-center gap-2">
        <span
          className={
            "flex items-center gap-1 rounded px-1.5 py-0.5 text-2xs font-bold uppercase tracking-wide " +
            t.badge
          }
        >
          <t.Glyph className="h-3 w-3" />
          {t.label}
        </span>
      </div>

      <RichText text={res.answer} />

      {/* HAX #2 — citation bấm được, kèm ngày cập nhật nguồn (HAX #5) */}
      {res.citations?.length > 0 && (
        <div className="mt-3 space-y-1.5 border-t border-black/5 pt-2.5">
          <div className="text-2xs font-bold uppercase tracking-[0.1em] text-ink-3">Nguồn</div>
          {res.citations.map((c, i) => (
            <button
              key={i}
              onClick={() => onOpenCitation?.(c)}
              className="group block w-full rounded-lg border border-line bg-surface px-2.5 py-2 text-left transition-colors hover:border-brand-line"
            >
              <div className="flex items-center gap-1.5">
                <Icon.Doc className="h-3.5 w-3.5 shrink-0 text-brand" />
                <span className="min-w-0 flex-1 truncate text-xs font-semibold text-brand">
                  {c.source}
                  {c.session_code && ` · ${c.session_code}`}
                </span>
                <span className="shrink-0 text-2xs text-ink-3">cập nhật {c.updated}</span>
              </div>
              <p className="mt-1 line-clamp-2 text-2xs italic leading-snug text-ink-2">“{c.quote}”</p>
            </button>
          ))}
        </div>
      )}

      {/* Clarify — hỏi lại TỐI ĐA 1 lần, kèm lựa chọn cụ thể */}
      {res.action === "clarify" && res.clarify_options?.length > 0 && (
        <div className="mt-3 space-y-1.5">
          {res.clarify_options.map((o) => (
            <button
              key={o}
              disabled={!canClarify}
              onClick={() => onPickOption(o)}
              className="flex w-full items-center gap-2 rounded-lg border border-warn/30 bg-surface px-2.5 py-2 text-left text-sm font-medium text-warn transition-colors hover:bg-warn-soft disabled:opacity-50"
            >
              <Icon.ArrowRight className="h-3.5 w-3.5 shrink-0" />
              {o}
            </button>
          ))}
        </div>
      )}

      {/* HAX #4 — nói rõ đã bàn giao cho ai, không để user treo trong im lặng */}
      {res.escalated_to && (
        <div className="mt-3 flex gap-2 rounded-lg border border-danger/25 bg-surface px-2.5 py-2 text-xs leading-relaxed text-danger">
          <Icon.Inbox className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>
            Đã vào hàng đợi <strong className="font-semibold">TA {res.escalated_to.ta}</strong> (lớp{" "}
            {res.escalated_to.class}) — vị trí #{res.escalated_to.queue_position} trong bản tổng hợp
            gần nhất.
          </span>
        </div>
      )}

      {/* HAX #3 — sửa sai rẻ và nhanh. Số liệu kỹ thuật để cuối, cỡ nhỏ nhất:
          chứng minh là lời gọi AI thật mà không tranh chỗ với nội dung. */}
      <div className="mt-3 flex items-center gap-2 border-t border-black/5 pt-2">
        {reported ? (
          <span className="flex items-center gap-1 text-2xs font-semibold text-warn">
            <Icon.Check className="h-3 w-3" />
            Đã ghi nhận — TA sẽ xác nhận lại câu này
          </span>
        ) : (
          <button
            onClick={flagWrong}
            className="flex items-center gap-1 text-2xs font-medium text-ink-3 transition-colors hover:text-warn"
          >
            <Icon.Alert className="h-3 w-3" />
            Báo sai
          </button>
        )}
        <span className="ml-auto font-mono text-2xs tracking-tight text-ink-3/80">
          {res.action} · {res.confidence.toFixed(2)}
          {res.latency_ms != null && ` · ${res.latency_ms}ms`} · {res.trace_id}
        </span>
      </div>
    </div>
  );
}

// ---------- phụ trợ ----------

function BotBubble({ children, tone }) {
  return (
    <div className="flex justify-start">
      <div
        className={
          "max-w-[85%] rounded-2xl rounded-bl-md px-3.5 py-2 text-base leading-relaxed " +
          (tone === "error"
            ? "border border-danger/25 bg-danger-soft text-danger"
            : "border border-line bg-surface text-ink-2")
        }
      >
        {children}
      </div>
    </div>
  );
}

function Dot({ d = "0ms" }) {
  return (
    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-ink-3" style={{ animationDelay: d }} />
  );
}

/** Render **đậm** và xuống dòng — đủ cho câu trả lời của agent, không cần thư viện markdown. */
function RichText({ text }) {
  return (
    <div className="space-y-1.5">
      {String(text)
        .split("\n")
        .filter((l) => l.trim())
        .map((line, i) => (
          <p key={i} className="text-base leading-relaxed text-ink">
            {line.split(/(\*\*[^*]+\*\*)/g).map((seg, j) =>
              seg.startsWith("**") && seg.endsWith("**") ? (
                <strong key={j} className="font-semibold">
                  {seg.slice(2, -2)}
                </strong>
              ) : (
                seg
              )
            )}
          </p>
        ))}
    </div>
  );
}
