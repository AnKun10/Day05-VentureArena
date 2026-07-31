// ============================================================
// API CLIENT — một chỗ duy nhất đổi giữa mock và backend thật.
//
//   .env.local:  VITE_USE_MOCK=false
//                VITE_API_BASE=http://localhost:8000
//
// Mặc định là mock để `npm run dev` chạy được khi backend chưa lên
// (và là phương án B khi hết credit lúc demo — MASTERPLAN.md §9).
// ============================================================

import { mockAsk } from "./mockAsk.js";

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== "false";
const BASE = import.meta.env.VITE_API_BASE ?? "";

export const isMock = () => USE_MOCK;

/**
 * Hỏi agent.
 * @returns {Promise<{
 *   action: "answer"|"clarify"|"refuse",
 *   answer: string,
 *   confidence: number,
 *   citations: {source:string, session_code:string|null, quote:string, updated:string, url:string}[],
 *   clarify_options: string[],
 *   escalated_to: {ta:string, class:string, queue_position:number}|null,
 *   trace_id: string
 * }>}
 */
export async function ask(question, clarifyContext = null) {
  const t0 = performance.now();
  const data = USE_MOCK
    ? await mockAsk(question, clarifyContext)
    : await postJSON("/api/ask", { question, clarify_context: clarifyContext });
  return { ...data, latency_ms: Math.round(performance.now() - t0) };
}

/** Nút "Báo sai" — ghi feedback log + đẩy câu hỏi vào hàng đợi TA xác nhận. */
export async function reportWrong(traceId, question, answer) {
  if (USE_MOCK) {
    console.info("[mock] report-wrong", { traceId, question });
    return { ok: true, queued_for_ta: true };
  }
  return postJSON("/api/feedback", {
    trace_id: traceId,
    question,
    answer,
    verdict: "wrong",
  });
}

async function postJSON(path, body) {
  const res = await fetch(BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${path} → HTTP ${res.status}`);
  return res.json();
}