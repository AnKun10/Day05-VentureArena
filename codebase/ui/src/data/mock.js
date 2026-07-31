// ============================================================
// MOCK DATA — demo UI, chưa nối backend.
// Cấu trúc bám MASTERPLAN.md:
//  - Mã buổi chuẩn: LT-x / Lab-x / WS-x / OH-x / MD-x (schedule.yaml)
//  - Tài liệu gắn vào buổi qua Session Linker (kênh #tài-nguyên)
//  - Bản tin: AI agent lấy bài từ kênh chia-sẻ / bài-học →
//    tóm tắt 1-3 câu + gắn nhiều tag (taxonomy 10 tag đã chốt)
//    → lấy ảnh minh hoạ qua API (vd Tavily). Ảnh ở demo là
//    SVG placeholder tự sinh.
// ============================================================

// ---------- Loại buổi học (shade 600 — đọc tốt trên nền sáng) ----------
export const SESSION_TYPES = {
  LT: { label: "Lý thuyết", color: "#2563eb" },
  LAB: { label: "Thực hành Lab", color: "#16a34a" },
  WS: { label: "Workshop", color: "#9333ea" },
  OH: { label: "Office hour", color: "#d97706" },
  MD: { label: "Mentor duty", color: "#db2777" },
  OTHER: { label: "Deadline/Khác", color: "#64748b" },
};

// ---------- Màu role giống Discord ----------
export const ROLE_COLORS = {
  "Học viên": "#16a34a",
  "Lab Coach": "#db2777",
  BTC: "#dc2626",
  Mentor: "#7c3aed",
};

// ---------- Sinh lịch quanh tuần hiện tại để demo luôn "sống" ----------
const DAY_MS = 86400000;

export function startOfWeek(d) {
  const x = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const dow = (x.getDay() + 6) % 7; // 0 = Thứ 2
  return new Date(x.getTime() - dow * DAY_MS);
}
export const addDays = (d, n) => new Date(d.getTime() + n * DAY_MS);
export const fmtDM = (d) =>
  `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}`;
export const isSameDay = (a, b) =>
  a.getFullYear() === b.getFullYear() &&
  a.getMonth() === b.getMonth() &&
  a.getDate() === b.getDate();

const MONDAY = startOfWeek(new Date());
const day = (offset) => addDays(MONDAY, offset);
const hhmm = (dec) => {
  const h = Math.floor(dec);
  const m = Math.round((dec - h) * 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
};

// dayOffset tính từ Thứ 2 tuần hiện tại (âm = tuần trước, ≥7 = tuần sau)
const RAW_SESSIONS = [
  // ---- Tuần trước ----
  { code: "OH-4", type: "OH", dayOffset: -7, start: 19, end: 20.5, title: "Office hour tuần 4", format: "Zoom", cls: "Chung", host: "TA trực: T015", desc: "Giải đáp thắc mắc bài học tuần 4, hỗ trợ nhóm chuẩn bị canvas.", summary: ["Giải đáp bài tập tuần 4 và lỗi thường gặp khi nộp bài", "Hướng dẫn chuẩn bị canvas cho hackathon"], links: { record: "#" } },
  { code: "LT-9", type: "LT", dayOffset: -6, start: 19.5, end: 21.5, title: "RAG căn bản: retrieval, chunking, citation", format: "Zoom", cls: "Lý thuyết chung", host: "Giảng viên khoá", desc: "Kiến trúc RAG, chiến lược chunking, vì sao citation quan trọng với sản phẩm AI.", summary: ["Kiến trúc RAG end-to-end: ingest → embed → retrieve → generate", "3 chiến lược chunking và trade-off của từng loại", "Citation là guardrail chống bịa — cách buộc model trích nguồn"], links: { slide: "#", record: "#" } },
  { code: "Lab-9", type: "LAB", dayOffset: -5, start: 18.5, end: 21, title: "Lab: Build RAG pipeline đầu tiên", format: "Offline", location: "Phòng D305", cls: "Lab-D305", host: "Lab Coach: M.A", desc: "Thực hành dựng pipeline RAG với Chroma; nộp bài cuối buổi.", summary: ["Dựng pipeline RAG với Chroma từ 6 transcript bài giảng", "Đo chất lượng retrieval bằng bộ câu hỏi mẫu", "Nộp bài cuối buổi qua link kênh lớp"], links: { slide: "#", materials: "#" } },
  { code: "LT-10", type: "LT", dayOffset: -4, start: 19.5, end: 21.5, title: "Eval & Golden set cho sản phẩm AI", format: "Zoom", cls: "Lý thuyết chung", host: "Giảng viên khoá", desc: "Cách xây golden set, định nghĩa chiều chất lượng kiểm chứng được, quality bar.", summary: ["Golden set là gì, vì sao ≥20 case và phải có case khó", "Định nghĩa chiều chất lượng để người ngoài chấm ra cùng kết quả", "Đặt quality bar bằng con số và giữ nguyên sau khi chốt"], links: { slide: "#", record: "#" } },
  { code: "MD-4", type: "MD", dayOffset: -3, start: 20, end: 21.5, title: "Mentor duty tuần 4", format: "Zoom", cls: "Theo nhóm", host: "Mentor của nhóm", desc: "Review tiến độ tuần 4. Nhớ gửi báo cáo tiến độ trước buổi.", summary: ["Review tiến độ tuần 4 theo nhóm", "Gửi báo cáo tiến độ cho mentor TRƯỚC buổi làm việc"], links: {} },
  { code: "WS-2", type: "WS", dayOffset: -2, start: 20, end: 22, title: "Problem → MVP Canvas", format: "Zoom", cls: "Toàn khoá", host: "Diễn giả khách mời", desc: "Từ nỗi đau người dùng đến MVP: cách cắt lát vấn đề và dựng canvas sản phẩm.", summary: ["Từ pain có bằng chứng đến problem statement không chữ AI", "Cắt lát MỘT CÂU: 1 user · 1 việc · 1 quyết định · 1 kết quả", "Thực hành dựng MVP canvas ngay trong buổi"], links: { slide: "#", record: "#" } },

  // ---- Tuần này ----
  { code: "OH-5", type: "OH", dayOffset: 0, start: 19, end: 20.5, title: "Office hour tuần 5", format: "Zoom", cls: "Chung", host: "TA trực: T088", desc: "Giải đáp thắc mắc tuần 5; ưu tiên các nhóm chuẩn bị hackathon.", summary: ["Giải đáp thắc mắc tuần 5", "Ưu tiên gỡ vướng cho các nhóm chuẩn bị hackathon"], links: { zoom: "#" } },
  { code: "LT-11", type: "LT", dayOffset: 1, start: 19.5, end: 21.5, title: "Agent & tool use: từ demo đến production", format: "Zoom", cls: "Lý thuyết chung", host: "Giảng viên khoá", desc: "Vòng đời một AI agent, tool calling, guardrails và logging.", summary: ["Vòng đời một AI agent: nhận việc → gọi tool → kiểm chứng → trả kết quả", "Thiết kế tool declaration tốt và lỗi routing thường gặp", "Guardrails + logging: điều kiện bắt buộc trước khi lên production"], links: { slide: "#", zoom: "#" } },
  { code: "Lab-10", type: "LAB", dayOffset: 2, start: 18.5, end: 21, title: "Lab: Discord bot + slash command", format: "Offline", location: "Phòng D305", cls: "Lab-D305", host: "Lab Coach: M.A", desc: "Dựng Discord bot với discord.py, đăng ký slash command, nối API.", summary: ["Dựng bot discord.py và đăng ký slash command", "Nối bot với REST API qua aiohttp", "Xử lý lỗi timeout và permission trong server test"], links: { slide: "#", zoom: "#" } },
  { code: "LT-12", type: "LT", dayOffset: 3, start: 19.5, end: 21.5, title: "Human-AI interaction: HAX & PAIR", format: "Zoom", cls: "Lý thuyết chung", host: "Giảng viên khoá", desc: "Nguyên tắc thiết kế trải nghiệm AI: expectation setting, handoff, correction.", summary: ["Bộ nguyên tắc HAX/PAIR và cách trỏ vào prototype", "Expectation setting: nói rõ hệ thống làm được gì", "Handoff & correction: khi nào chuyển người, sửa sai thế nào"], links: { zoom: "#" } },
  { code: "MD-5", type: "MD", dayOffset: 4, start: 20, end: 21.5, title: "Mentor duty tuần 5", format: "Zoom", cls: "Theo nhóm", host: "Mentor của nhóm", desc: "Review tiến độ trước hackathon. Gửi báo cáo tiến độ trước buổi làm việc.", summary: ["Review tiến độ trước hackathon", "Chốt phân công và rủi ro với mentor"], links: { zoom: "#" } },
  { code: "Lab-11", type: "LAB", dayOffset: 5, start: 9, end: 11.5, title: "Lab bù: Eval runner & trace log", format: "Offline", location: "Phòng D302", cls: "Lab-D302", host: "Lab Coach: H.T", desc: "Buổi bù cho nhóm vắng Lab-10: viết eval runner, log trace lời gọi AI.", summary: ["Viết eval runner chạy trọn golden set", "Log trace mọi lời gọi AI để lấy điểm prototype"], links: { zoom: "#" } },
  { code: "WS-3", type: "WS", dayOffset: 5, start: 20, end: 22, title: "Kinh nghiệm quản lý dự án & duy trì năng suất", format: "Zoom", cls: "Toàn khoá", host: "Diễn giả khách mời — Founder/CTO", desc: "Cách phát triển sản phẩm AI từ bài toán thực tế đến hướng triển khai; quản lý dự án, phân chia công việc, theo dõi tiến độ trong team.", summary: ["Từ bài toán thực tế đến hướng triển khai sản phẩm AI", "Phân chia công việc và theo dõi tiến độ trong team nhỏ", "Q&A với Founder/CTO về nghề product engineer"], links: { zoom: "#" } },
  { code: "OH-6", type: "OH", dayOffset: 6, start: 15, end: 16.5, title: "Office hour cuối tuần", format: "Zoom", cls: "Chung", host: "TA trực: T101", desc: "Slot bổ sung cuối tuần cho các nhóm chạy nước rút hackathon.", summary: ["Slot bổ sung cho nhóm chạy nước rút hackathon"], links: { zoom: "#" } },

  // ---- Tuần sau ----
  { code: "LT-13", type: "LT", dayOffset: 8, start: 19.5, end: 21.5, title: "Ôn tập & định hướng Demo Day", format: "Zoom", cls: "Lý thuyết chung", host: "Giảng viên khoá", desc: "Tổng kết kiến thức, checklist chuẩn bị Demo Day.", summary: ["Tổng kết kiến thức 5 tuần", "Checklist chuẩn bị Demo Day theo rubric"], links: {} },
  { code: "Lab-12", type: "LAB", dayOffset: 9, start: 18.5, end: 21, title: "Lab: Hoàn thiện prototype", format: "Offline", location: "Phòng D305", cls: "Lab-D305", host: "Lab Coach: M.A", desc: "Buổi lab tự do hoàn thiện prototype, Lab Coach hỗ trợ tại chỗ.", summary: ["Hoàn thiện prototype với Lab Coach hỗ trợ tại chỗ"], links: {} },
  { code: "WS-4", type: "WS", dayOffset: 12, start: 20, end: 22, title: "Pitching: kể chuyện sản phẩm trong 5 phút", format: "Zoom", cls: "Toàn khoá", host: "Diễn giả khách mời", desc: "Cấu trúc pitch, demo case lỗi một cách tự tin, xử lý Q&A giám khảo.", summary: ["Cấu trúc pitch 5 phút theo khung bài toán → demo → số liệu", "Demo case lỗi một cách tự tin", "Xử lý Q&A giám khảo"], links: {} },
];

export const SESSIONS = RAW_SESSIONS.map((s) => {
  const date = day(s.dayOffset);
  return {
    ...s,
    date,
    timeLabel: `${hhmm(s.start)} – ${hhmm(s.end)}`,
    // nguồn enrich giả lập (thiết kế: từ kênh #thông-báo)
    source: { channel: "#thông-báo", updated: fmtDM(addDays(date, -1)) },
  };
});

// ---------- Tài nguyên (kênh #tài-nguyên → Session Linker gắn mã buổi) ----------
export const RESOURCE_KINDS = {
  slide: { label: "Slide" },
  record: { label: "Record" },
  doc: { label: "Tài liệu" },
  link: { label: "Link khác" },
};

export const RESOURCES = [
  { id: 1, kind: "slide", title: "Slide Workshop WS2: Problem → MVP Canvas", session: "WS-2", by: "BTC — Admin", date: fmtDM(day(-2)), note: "Nội bộ chương trình, không public ra ngoài", url: "#" },
  { id: 2, kind: "record", title: "Video Recording WS1: Kick off", session: "WS-1", by: "BTC — Admin", date: fmtDM(day(-9)), url: "#" },
  { id: 3, kind: "record", title: "Record LT-10: Eval & Golden set", session: "LT-10", by: "BTC — Admin", date: fmtDM(day(-3)), url: "#" },
  { id: 4, kind: "slide", title: "Slide LT-11: Agent & tool use", session: "LT-11", by: "Giảng viên khoá", date: fmtDM(day(1)), url: "#" },
  { id: 5, kind: "doc", title: "Đề bài + hướng dẫn Lab 10 (Discord bot)", session: "Lab-10", by: "Lab Coach — M.A", date: fmtDM(day(2)), url: "#" },
  { id: 6, kind: "record", title: "Record WS2: Problem → MVP Canvas", session: "WS-2", by: "BTC — Admin", date: fmtDM(day(-1)), url: "#" },
  { id: 7, kind: "doc", title: "Ngân hàng đề chính thức Build Phase (Khoá 3 & 4)", session: null, by: "BTC — Admin", date: fmtDM(day(-4)), url: "#" },
  { id: 8, kind: "doc", title: "Tổng quan chương trình: 6 tuần Sprint — lịch trình dự kiến", session: null, by: "BTC — Admin", date: fmtDM(day(-14)), url: "#" },
  { id: 9, kind: "link", title: "Worksheet JTBD đầy đủ (bản dịch)", session: null, by: "BTC — Admin", date: fmtDM(day(-7)), url: "#" },
];

// ---------- Bản tin: taxonomy 10 tag ĐÃ CHỐT (1 news có thể nhiều tag) ----------
export const NEWS_TAGS = [
  { id: "ai-model", label: "AI Model", color: "#2563eb" },
  { id: "ai-skill", label: "AI Skill", color: "#7c3aed" },
  { id: "ai-tools", label: "AI Tools", color: "#0891b2" },
  { id: "api-mcp", label: "API & MCP", color: "#ea580c" },
  { id: "system-design", label: "System Design", color: "#0d9488" },
  { id: "uiux", label: "UI/UX", color: "#db2777" },
  { id: "dataset", label: "Dataset", color: "#16a34a" },
  { id: "soft-skills", label: "Soft Skills", color: "#ca8a04" },
  { id: "survey", label: "Survey", color: "#dc2626" },
  { id: "other", label: "Other", color: "#64748b" },
];

export const tagOf = (id) => NEWS_TAGS.find((t) => t.id === id);

// Ảnh minh hoạ demo: SVG placeholder theo màu tag đầu tiên.
// Production: agent lấy ảnh thật qua API tìm ảnh (vd Tavily) — xem MASTERPLAN.
export const thumb = (color, glyph) =>
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="240" height="240">
      <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="${color}" stop-opacity="0.18"/>
        <stop offset="1" stop-color="${color}" stop-opacity="0.45"/>
      </linearGradient></defs>
      <rect width="240" height="240" fill="url(#g)"/>
      <text x="120" y="138" font-size="72" text-anchor="middle" font-family="Segoe UI Emoji,sans-serif">${glyph}</text>
    </svg>`
  );

export const NEWS = [
  {
    id: 1,
    tags: ["ai-model", "system-design"],
    title: "[Deep-dive] BEV — Góc nhìn “thượng đế” của xe tự hành",
    aiSummary:
      "BEV (Bird's-Eye View) đưa dữ liệu từ camera/LiDAR về một bản đồ nhìn từ trên xuống — nền tảng của perception hiện đại. Bài viết giải thích trực quan pipeline BEV và vì sao nó thay thế cách ghép ảnh truyền thống.",
    content:
      "BEV không chỉ là một cách hiển thị — nó là không gian chung để hợp nhất dữ liệu từ nhiều cảm biến. Khi mọi camera và LiDAR đều được chiếu về cùng một mặt phẳng nhìn từ trên xuống, bài toán tracking và planning trở nên đơn giản hơn rất nhiều.\n\nBài viết đi qua 3 phần: (1) vì sao ảnh 2D thuần không đủ cho xe tự hành, (2) cách các mạng như BEVFormer học phép chiếu này end-to-end, và (3) demo minh hoạ trên dataset nuScenes.",
    image: thumb("#2563eb", "🚗"),
    channel: "#bài-học",
    author: "GR16 — T112",
    role: "Học viên",
    hearts: 23,
    comments: [
      { author: "T057 — A.Minh", role: "Học viên", time: "14 giờ trước", text: "Phần chiếu multi-camera về một mặt phẳng giải thích dễ hiểu quá, cảm ơn bạn!" },
      { author: "Lab Coach — S.", role: "Lab Coach", time: "12 giờ trước", text: "Nhóm nào làm track RAV nên đọc bài này trước khi chọn dataset nhé." },
    ],
    time: "16 giờ trước",
    url: "#",
  },
  {
    id: 2,
    tags: ["dataset", "ai-model"],
    title: "[Research] Gợi ý dataset cho đề tài CV thuộc track RAV",
    aiSummary:
      "Không nên chọn dataset chỉ vì nó lớn hoặc phổ biến — hãy chọn theo bài toán. Bài tổng hợp 6 dataset CV cho xe tự hành kèm tiêu chí chọn và bẫy thường gặp khi benchmark.",
    content:
      "Tiêu chí chọn dataset: (1) khớp task — detection, segmentation hay tracking; (2) domain gap với dữ liệu thật của bạn; (3) license có cho phép dùng trong cuộc thi không.\n\nDanh sách đề xuất: nuScenes, Waymo Open, KITTI, Cityscapes, BDD100K, Argoverse 2 — kèm bảng so sánh kích thước, sensor và annotation trong bài.",
    image: thumb("#16a34a", "🗂️"),
    channel: "#bài-học",
    author: "GR16 — T112",
    role: "Học viên",
    hearts: 19,
    comments: [
      { author: "T081 — H.Nam", role: "Học viên", time: "18 giờ trước", text: "Bảng so sánh cuối bài đúng thứ nhóm mình đang cần, xin phép share về nhóm!" },
    ],
    time: "20 giờ trước",
    url: "#",
  },
  {
    id: 3,
    tags: ["soft-skills", "ai-skill"],
    title: "Bạn đang “LÀM CHỦ AI” hay “LẠM DỤNG AI”?",
    aiSummary:
      "Ranh giới giữa dùng AI để tăng tốc và đánh mất khả năng tự giải quyết vấn đề nằm ở việc bạn có kiểm chứng được output hay không. Tác giả đề xuất quy tắc: không nhận code/ý tưởng nào mình không giải thích lại được.",
    content:
      "Mình có một người bạn dùng AI trong mọi việc — từ lập trình đến những câu hỏi rất đơn giản. Điều đáng lo không phải là dùng nhiều, mà là dần mất phản xạ tự đặt câu hỏi.\n\nQuy tắc mình đang áp dụng: (1) tự phác hướng giải trước khi hỏi AI, (2) không merge code nào mình không giải thích lại được — trùng với vibe-coding rule của khoá, (3) mỗi tuần một buổi code “chay” không AI.",
    image: thumb("#ca8a04", "⚖️"),
    channel: "#bài-học",
    author: "T017 — Q.La",
    role: "Học viên",
    hearts: 15,
    comments: [
      { author: "T101 — TA trực", role: "Lab Coach", time: "3 giờ trước", text: "Quy tắc số 2 chính là vibe-coding rule khi chấm CP5/CP6 đó cả nhà 😄" },
      { author: "T063 — M.Châu", role: "Học viên", time: "2 giờ trước", text: "Buổi code chay nghe hay đấy, tuần này nhóm mình thử." },
    ],
    time: "4 giờ trước",
    url: "#",
  },
  {
    id: 4,
    tags: ["system-design", "api-mcp"],
    title: "Folder Structure as Agent Architecture: có cần Multi-Agent framework?",
    aiSummary:
      "Paper “Interpretable Context Methodology” cho thấy có thể tổ chức agent workflow chỉ bằng cấu trúc thư mục và context file thay vì framework multi-agent phức tạp. Trade-off: dễ debug hơn nhưng khó scale động.",
    content:
      "Ý tưởng chính: mỗi layer là một file context (CLAUDE.md, CONTEXT.md, reference material…) và agent đọc theo thứ tự thư mục — thay vì orchestration code.\n\nĐiểm hay là mọi quyết định của agent đều trace được về một file cụ thể, rất hợp với yêu cầu log/trace của khoá. Điểm yếu: khó xử lý các luồng động như spawn agent theo số lượng task.",
    image: thumb("#0d9488", "🗄️"),
    channel: "#bài-học",
    author: "T057 — A.Minh",
    role: "Học viên",
    hearts: 11,
    comments: [
      { author: "GR16 — T112", role: "Học viên", time: "20 giờ trước", text: "Cách này giống setup của Claude Code nhỉ, folder = context layer." },
    ],
    time: "23 giờ trước",
    url: "#",
  },
  {
    id: 5,
    tags: ["ai-skill", "ai-tools"],
    title: "Hiểu đúng về AI Agent và Tool Evaluation qua bài Lab “Research Agent Tool Eval”",
    aiSummary:
      "Tổng hợp các khái niệm cốt lõi trong bài Lab Day 04: tool declaration, routing error, và cách đo chất lượng tool call bằng JSON logs qua các phiên bản prompt v0–v3.",
    content:
      "Bối cảnh: nhiều bạn làm Lab Day 04 nhưng chưa rõ vì sao phải đo routing/arguments riêng. Bài này giải thích: tool đúng nhưng argument sai vẫn là fail — và chỉ nhìn output cuối sẽ không thấy.\n\nKèm checklist 5 bước cải tiến prompt + tool declaration mà nhóm mình đã dùng để tăng accuracy từ 62% lên 91% qua 4 phiên bản.",
    image: thumb("#7c3aed", "🤖"),
    channel: "#bài-học",
    author: "T071 — N.Minh",
    role: "Học viên",
    hearts: 18,
    comments: [
      { author: "T088 — TA trực", role: "Lab Coach", time: "1 ngày trước", text: "Checklist 5 bước rất chuẩn, mình pin lại trong kênh lớp nhé." },
      { author: "T112 — Q.Khánh", role: "Học viên", time: "22 giờ trước", text: "62% → 91% ấn tượng đấy, bạn share log eval được không?" },
    ],
    time: "1 ngày trước",
    url: "#",
  },
  {
    id: 6,
    tags: ["api-mcp", "ai-tools"],
    title: "Prompt caching giảm 80% chi phí gọi API — kinh nghiệm thực chiến",
    aiSummary:
      "Đặt phần context tĩnh (system prompt, tài liệu) lên đầu request và bật cache giúp nhóm giảm ~80% chi phí khi chạy eval lặp lại. Bài kèm số liệu trước/sau và các lỗi khiến cache miss.",
    content:
      "Khi chạy golden set 20+ case nhiều lượt, phần system prompt + knowledge base lặp lại y hệt — đó là ứng viên hoàn hảo cho prompt caching.\n\nLỗi hay gặp: đổi thứ tự message khiến prefix khác nhau → cache miss toàn bộ; timestamp động trong system prompt cũng vậy. Sau khi cố định prefix, chi phí eval của nhóm giảm từ ~$3.2 còn ~$0.6 mỗi lượt.",
    image: thumb("#ea580c", "⚡"),
    channel: "#chia-sẻ",
    author: "T093 — D.Phúc",
    role: "Học viên",
    hearts: 27,
    comments: [
      { author: "T015 — H.Anh", role: "Học viên", time: "5 giờ trước", text: "Đúng bài nhóm mình cần cho CP3, cảm ơn bạn nhiều!" },
      { author: "Mentor — L.Đ", role: "Mentor", time: "4 giờ trước", text: "Bổ sung: nhớ log cache_read tokens để chứng minh số liệu trong repo nhé." },
    ],
    time: "6 giờ trước",
    url: "#",
  },
  {
    id: 7,
    tags: ["api-mcp", "ai-skill"],
    title: "MCP là gì? Kết nối tool cho agent qua Model Context Protocol",
    aiSummary:
      "MCP chuẩn hoá cách agent kết nối tool và data source: một server khai báo tool, mọi client (Claude, IDE, bot) dùng lại được. Bài hướng dẫn viết MCP server tối giản bằng Python trong 40 dòng.",
    content:
      "Thay vì viết adapter riêng cho từng ứng dụng, MCP cho phép bạn khai báo tool một lần và dùng ở mọi client hỗ trợ.\n\nDemo trong bài: MCP server đọc schedule.yaml của khoá và expose tool `get_next_session` — Claude Desktop và bot Discord đều gọi được. Code 40 dòng kèm giải thích từng phần.",
    image: thumb("#ea580c", "🔌"),
    channel: "#chia-sẻ",
    author: "T042 — B.Long",
    role: "Học viên",
    hearts: 21,
    comments: [
      { author: "T057 — A.Minh", role: "Học viên", time: "8 giờ trước", text: "Ví dụ get_next_session hợp đề Companion ghê 👀" },
    ],
    time: "9 giờ trước",
    url: "#",
  },
  {
    id: 8,
    tags: ["uiux", "ai-tools"],
    title: "Thiết kế UI demo hackathon trong 2 giờ với shadcn/ui",
    aiSummary:
      "Quy trình 4 bước để có UI demo sạch trong 2 giờ: chốt token màu → dùng component có sẵn → mock data trước API → chỉ polish 3 màn hình chính. Kèm danh sách anti-pattern làm demo xấu đi.",
    content:
      "Trong hackathon, thời gian cho UI rất ít — đừng thiết kế từ đầu. Quy trình của mình: (1) chốt 1 accent màu + token, (2) shadcn/ui cho mọi primitive, (3) mock data giống cấu trúc API thật để sau chỉ đổi nguồn, (4) polish đúng 3 màn hình sẽ demo.\n\nAnti-pattern: nhiều màu accent, gradient khắp nơi, tự viết modal/dropdown thay vì dùng component có sẵn.",
    image: thumb("#db2777", "🎨"),
    channel: "#chia-sẻ",
    author: "T029 — T.Vy",
    role: "Học viên",
    hearts: 14,
    comments: [
      { author: "T063 — M.Châu", role: "Học viên", time: "11 giờ trước", text: "Bước mock data giống cấu trúc API thật là bài học xương máu của nhóm mình 😅" },
    ],
    time: "12 giờ trước",
    url: "#",
  },
  {
    id: 9,
    tags: ["survey"],
    title: "Khảo sát trải nghiệm AI Tutor trên VLearn (2–3 phút)",
    aiSummary:
      "Nhóm nghiên cứu cải thiện tính năng tóm tắt bài giảng của AI Tutor cần ý kiến người dùng thật. Form 2–3 phút, ai điền rồi nhóm sẽ điền lại form của bạn.",
    content:
      "Chào mọi người! Nhóm tụi mình đang nghiên cứu cải thiện tính năng AI Tutor trên VLearn để giúp sinh viên tóm tắt bài giảng nhanh, đúng trọng tâm và tiết kiệm thời gian ôn thi hơn.\n\nKhảo sát chỉ mất 2–3 phút. Ai đã điền thì thả tim, bọn mình sẽ điền lại form của bạn. Cảm ơn cả nhà!",
    image: thumb("#dc2626", "📋"),
    channel: "Lab-D305",
    author: "T227 — Đ.Mạnh",
    role: "Học viên",
    hearts: 15,
    comments: [
      { author: "T015 — H.Anh", role: "Học viên", time: "3 giờ trước", text: "Điền rồi nha, mọi người giúp nhóm bạn ấy với!" },
    ],
    time: "3 giờ trước",
    url: "#",
  },
  {
    id: 10,
    tags: ["survey", "other"],
    title: "Form khảo sát hackathon: khó khăn khi làm Lab demo",
    aiSummary:
      "Nhóm cần dữ liệu về khó khăn của học viên trong buổi thực hành để làm evidence cho đề tài hackathon. Form 1 phút, nhận khảo sát chéo qua DM.",
    content:
      "Xin chào mọi người, nhóm mình cần khảo sát về các khó khăn trong việc làm bài Lab demo trong buổi thực hành. Mong mọi người dành thời gian chỉ 1 phút thôi.\n\nNhóm nào cần khảo sát chéo cứ DM riêng mình nhé, win-win cả hai bên!",
    image: thumb("#dc2626", "📝"),
    channel: "Lab-D305",
    author: "T087 — H.Thành",
    role: "Học viên",
    hearts: 8,
    comments: [],
    time: "4 giờ trước",
    url: "#",
  },
  {
    id: 11,
    tags: ["other", "soft-skills"],
    title: "Recap tuần 4 bằng meme — học AI mà vui",
    aiSummary:
      "Tổng hợp 12 meme recap tuần 4 do cộng đồng đóng góp: từ nỗi khổ chunking đến niềm vui khi eval xanh toàn bảng. Giải trí nhẹ giữa mùa hackathon.",
    content:
      "Tuần 4 quá căng nên xin phép mở thread meme cho cả nhà xả stress. Top 3 được vote nhiều nhất sẽ lên digest tuần sau 😄\n\nĐóng góp bằng cách reply thread này, nhớ đúng chủ đề khoá học nhé!",
    image: thumb("#64748b", "😂"),
    channel: "#chia-sẻ",
    author: "T005 — V.An",
    role: "Học viên",
    hearts: 31,
    comments: [
      { author: "T042 — B.Long", role: "Học viên", time: "1 giờ trước", text: "Meme chunking đúng nỗi đau tuần trước 🤣" },
      { author: "Lab Coach — M.A", role: "Lab Coach", time: "30 phút trước", text: "Cười xong nhớ quay lại làm golden set nha cả nhà 🤝" },
    ],
    time: "2 giờ trước",
    url: "#",
  },
];

export const isHot = (n) => n.hearts + n.comments.length >= 20;
