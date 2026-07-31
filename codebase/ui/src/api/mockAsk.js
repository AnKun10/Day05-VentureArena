// ============================================================
// MOCK ADAPTER cho POST /api/ask — dùng tới khi Nghĩa nối RAG thật.
// Shape trả về = contract đã chốt (xem README.md § Contract /api/ask).
// Đổi sang API thật: set VITE_USE_MOCK=false, KHÔNG phải sửa UI.
//
// 4 kịch bản = 4 đường trải nghiệm R3 (MASTERPLAN.md §4):
//   answer   → happy      : trả lời + citation + ngày cập nhật nguồn
//   clarify  → mơ hồ      : hỏi lại TỐI ĐA 1 lần, kèm lựa chọn cụ thể
//   refuse   → ngoài scope: từ chối hữu ích, chỉ đúng người có thẩm quyền
//   refuse + escalated_to → không có nguồn: ghi nhận, gửi TA phụ trách lớp
// ============================================================

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let seq = 0;
const traceId = () => `tr_${Date.now().toString(36)}_${++seq}`;

// Kịch bản khớp theo từ khoá. Thứ tự có ý nghĩa — match đầu tiên thắng.
const SCRIPTS = [
  {
    id: "happy-deadline",
    match: /deadline|hạn nộp|spec.*(nộp|hạn)|nộp.*spec/i,
    reply: {
      action: "answer",
      confidence: 0.93,
      answer:
        "Hạn cứng nộp spec.md là **23:59 ngày 1**. Mốc CP4 (chốt tiến độ) diễn ra 17:30 ngày 1, nhưng file spec vẫn được nhận tới 23:59 cùng ngày. Sau thời điểm này quality bar trong spec không được đổi nữa.",
      citations: [
        {
          source: "schedule.yaml",
          session_code: null,
          quote: "CP4 · Chốt spec — 17:30 N1, hạn cứng spec.md 23:59 N1",
          updated: "29/07",
          url: "#",
        },
        {
          source: "#thông-báo",
          session_code: null,
          quote: "Nhắc: spec.md nộp trước 23:59 ngày 1, quality bar chốt luôn trong file.",
          updated: "29/07",
          url: "#",
        },
      ],
    },
  },
  {
    id: "happy-ws3",
    match: /ws-?3|workshop 3|workshop.*(mấy giờ|tối nay)/i,
    reply: {
      action: "answer",
      confidence: 0.91,
      answer:
        "**WS-3 — Kinh nghiệm quản lý dự án & duy trì năng suất** diễn ra 20:00 – 22:00, hình thức online qua Zoom, diễn giả khách mời (Founder/CTO). Record sẽ đăng ở #tài-nguyên trong vòng 24h và tự gắn vào block WS-3.",
      citations: [
        {
          source: "schedule.yaml",
          session_code: "WS-3",
          quote: "WS-3 · 20:00–22:00 · Zoom · Diễn giả khách mời — Founder/CTO",
          updated: "29/07",
          url: "#",
        },
      ],
    },
  },
  {
    id: "clarify-lab",
    match: /lab.*(tuần này|hôm nay|sắp tới)|(tuần này|hôm nay).*lab/i,
    reply: {
      action: "clarify",
      confidence: 0.42,
      answer:
        "Tuần này có 2 buổi Lab và mình chưa rõ bạn hỏi buổi nào. Bạn chọn giúp mình:",
      clarify_options: [
        "Lab-10 · Discord bot + slash command (T4, D305)",
        "Lab-11 · Lab bù: Eval runner & trace log (T7, D302)",
      ],
      citations: [],
    },
  },
  {
    id: "refuse-scope",
    match: /đáp án|lời giải|bài giải|điểm của (tôi|mình|em)|mấy điểm|chấm bao nhiêu|gia hạn|extend/i,
    reply: {
      action: "refuse",
      confidence: 0.88,
      answer:
        "Việc này nằm ngoài thẩm quyền của mình. Mình chỉ tra cứu thông tin công khai của khoá (lịch học, tài liệu, thông báo) — không cung cấp đáp án bài tập, không tra điểm cá nhân và không quyết định gia hạn deadline.\n\nBạn liên hệ đúng người nhé: **đáp án / cách làm** → hỏi Lab Coach trong buổi Lab hoặc post ở #hỏi-đáp · **điểm & gia hạn** → nhắn TA phụ trách lớp hoặc email BTC chương trình.",
      citations: [],
      escalated_to: null,
    },
  },
];

// Không khớp kịch bản nào → không có căn cứ trong KB → refuse + escalate.
const FALLBACK = {
  action: "refuse",
  confidence: 0.19,
  answer:
    "Mình không tìm thấy thông tin chính thức nào của khoá về việc này, nên mình không đoán. Câu hỏi của bạn đã được ghi nhận vào hàng đợi và sẽ nằm trong bản tổng hợp gần nhất gửi TA phụ trách lớp của bạn.",
  citations: [],
  escalated_to: { ta: "T088", class: "Lab-D305", queue_position: 3 },
};

export async function mockAsk(question, clarifyContext = null) {
  await sleep(500 + Math.random() * 600);

  // Đã clarify 1 lần → lượt sau bắt buộc trả lời, không hỏi lại nữa (R3 ②).
  if (clarifyContext) {
    const isLab10 = /lab-?10|discord/i.test(question);
    return {
      ...base(),
      action: "answer",
      confidence: 0.89,
      answer: isLab10
        ? "**Lab-10 · Discord bot + slash command** — Thứ 4, 18:30 – 21:00, offline tại phòng D305, Lab Coach M.A. Nội dung: dựng Discord bot với discord.py, đăng ký slash command, nối API. Nộp bài qua link trong kênh Lab-D305, deadline 23:59 cùng ngày."
        : "**Lab-11 · Lab bù: Eval runner & trace log** — Thứ 7, 09:00 – 11:30, offline tại phòng D302, Lab Coach H.T. Đây là buổi bù dành cho nhóm vắng Lab-10: viết eval runner và log trace lời gọi AI.",
      citations: [
        {
          source: "schedule.yaml",
          session_code: isLab10 ? "Lab-10" : "Lab-11",
          quote: isLab10
            ? "Lab-10 · 18:30–21:00 · Offline — Phòng D305 · Lab Coach: M.A"
            : "Lab-11 · 09:00–11:30 · Offline — Phòng D302 · Lab Coach: H.T",
          updated: "29/07",
          url: "#",
        },
      ],
    };
  }

  const hit = SCRIPTS.find((s) => s.match.test(question));
  return { ...base(), ...(hit ? hit.reply : FALLBACK) };
}

function base() {
  return {
    action: "answer",
    answer: "",
    confidence: 0,
    citations: [],
    clarify_options: [],
    escalated_to: null,
    trace_id: traceId(),
    latency_ms: null,
  };
}

// Câu hỏi mẫu cho demo strip — bấm 1 nút diễn 1 đường trải nghiệm (CP6).
export const DEMO_QUESTIONS = [
  { label: "Deadline nộp spec?", q: "Deadline nộp spec là khi nào?", tone: "answer" },
  { label: "Lab tuần này học gì?", q: "Lab tuần này học gì vậy?", tone: "clarify" },
  { label: "Cho mình đáp án bài 3", q: "Cho mình xin đáp án bài 3 với", tone: "refuse" },
  { label: "Bảo lưu có trợ cấp?", q: "Bảo lưu thì có được nhận trợ cấp học viên không?", tone: "escalate" },
];