// ============================================================
// MOCK DATA — demo UI, chưa nối backend.
// Cấu trúc bám MASTERPLAN.md:
//  - Mã buổi chuẩn: LT-x / Lab-x / WS-x / OH-x / MD-x (schedule.yaml)
//  - Tài liệu gắn vào buổi qua Session Linker (kênh #tài-nguyên)
//  - Thông tin buổi enrich từ kênh #thông-báo
//  - Loại tin: ⚠️ taxonomy PLACEHOLDER — nhóm sẽ chốt bộ loại tin
//    chính thức sau, sửa NEWS_CATEGORIES là toàn UI đổi theo.
// ============================================================

// ---------- Loại buổi học ----------
export const SESSION_TYPES = {
  LT: { label: "Lý thuyết", color: "#3b82f6" },
  LAB: { label: "Thực hành Lab", color: "#22c55e" },
  WS: { label: "Workshop", color: "#a855f7" },
  OH: { label: "Office hour", color: "#f59e0b" },
  MD: { label: "Mentor duty", color: "#ec4899" },
};

// FAQ chung theo LOẠI buổi (từ file faq/*.md trong thiết kế)
export const COMMON_FAQS = {
  LT: [
    { q: "Buổi lý thuyết có điểm danh không?", a: "Có, điểm danh qua link trong kênh lớp 15 phút đầu giờ. Vắng có phép thì báo TA trước buổi học." },
    { q: "Record buổi học đăng ở đâu, khi nào?", a: "Record đăng tại kênh #tài-nguyên trong vòng 24h sau buổi học và tự động gắn vào block buổi tương ứng trên trang Lịch học." },
  ],
  LAB: [
    { q: "Không có thẻ vào phòng lab / thẻ lỗi thì làm sao?", a: "Điền form báo lỗi thẻ được pin trong kênh #hỏi-đáp (bài 'QR báo lỗi/thiếu thẻ'). Lab Coach sẽ xử lý trước buổi học." },
    { q: "Nộp bài lab ở đâu, deadline khi nào?", a: "Nộp qua link trong kênh lớp Lab của bạn, deadline 23:59 cùng ngày buổi lab. Xem chi tiết trong block buổi trên Lịch học." },
    { q: "Kẹt kỹ thuật trong buổi lab thì gọi ai?", a: "Giơ tay gọi Lab Coach trong phòng, hoặc post vào kênh lớp kèm ảnh chụp lỗi để TA hỗ trợ." },
  ],
  WS: [
    { q: "Workshop có bắt buộc tham gia không?", a: "Khuyến khích tham gia trực tiếp; nếu bận có thể xem record (đăng trong vòng 24h tại #tài-nguyên)." },
    { q: "Slide và record của workshop lấy ở đâu?", a: "Sau buổi, slide + record được đăng ở #tài-nguyên và gắn vào đúng block buổi này — mở tab 'Tài liệu buổi học' phía trên." },
  ],
  OH: [
    { q: "Đăng ký slot office hour thế nào?", a: "Đăng ký qua link trong thông báo tuần ở #thông-báo; mỗi nhóm tối đa 1 slot / tuần." },
    { q: "Office hour hỏi được những gì?", a: "Mọi thứ về bài học, dự án, định hướng. Câu hỏi về điểm số / trường hợp cá nhân thì liên hệ BTC qua email chương trình." },
  ],
  MD: [
    { q: "Mentor duty là gì?", a: "Buổi làm việc định kỳ giữa team và mentor: review tiến độ, gỡ vướng, định hướng tuần kế tiếp." },
    { q: "Team cần chuẩn bị gì trước buổi mentor duty?", a: "Gửi báo cáo tiến độ cho mentor TRƯỚC buổi làm việc (quy định bắt buộc — xem thông báo ở #thông-báo)." },
  ],
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
  { code: "OH-4", type: "OH", dayOffset: -7, start: 19, end: 20.5, title: "Office hour tuần 4", format: "Zoom", cls: "Chung", host: "TA trực: T015", desc: "Giải đáp thắc mắc bài học tuần 4, hỗ trợ nhóm chuẩn bị canvas.", links: { record: "#" } },
  { code: "LT-9", type: "LT", dayOffset: -6, start: 19.5, end: 21.5, title: "RAG căn bản: retrieval, chunking, citation", format: "Zoom", cls: "Lý thuyết chung", host: "Giảng viên khoá", desc: "Kiến trúc RAG, chiến lược chunking, vì sao citation quan trọng với sản phẩm AI.", links: { slide: "#", record: "#" } },
  { code: "Lab-9", type: "LAB", dayOffset: -5, start: 18.5, end: 21, title: "Lab: Build RAG pipeline đầu tiên", format: "Offline", location: "Phòng D305", cls: "Lab-D305", host: "Lab Coach: M.A", desc: "Thực hành dựng pipeline RAG với Chroma; nộp bài cuối buổi.", links: { slide: "#", materials: "#" } },
  { code: "LT-10", type: "LT", dayOffset: -4, start: 19.5, end: 21.5, title: "Eval & Golden set cho sản phẩm AI", format: "Zoom", cls: "Lý thuyết chung", host: "Giảng viên khoá", desc: "Cách xây golden set, định nghĩa chiều chất lượng kiểm chứng được, quality bar.", links: { slide: "#", record: "#" } },
  { code: "MD-4", type: "MD", dayOffset: -3, start: 20, end: 21.5, title: "Mentor duty tuần 4", format: "Zoom", cls: "Theo nhóm", host: "Mentor của nhóm", desc: "Review tiến độ tuần 4. Nhớ gửi báo cáo tiến độ trước buổi.", links: { } },
  { code: "WS-2", type: "WS", dayOffset: -2, start: 20, end: 22, title: "Problem → MVP Canvas", format: "Zoom", cls: "Toàn khoá", host: "Diễn giả khách mời", desc: "Từ nỗi đau người dùng đến MVP: cách cắt lát vấn đề và dựng canvas sản phẩm.", links: { slide: "#", record: "#" } },

  // ---- Tuần này ----
  { code: "OH-5", type: "OH", dayOffset: 0, start: 19, end: 20.5, title: "Office hour tuần 5", format: "Zoom", cls: "Chung", host: "TA trực: T088", desc: "Giải đáp thắc mắc tuần 5; ưu tiên các nhóm chuẩn bị hackathon.", links: { zoom: "#" } },
  { code: "LT-11", type: "LT", dayOffset: 1, start: 19.5, end: 21.5, title: "Agent & tool use: từ demo đến production", format: "Zoom", cls: "Lý thuyết chung", host: "Giảng viên khoá", desc: "Vòng đời một AI agent, tool calling, guardrails và logging.", links: { slide: "#", zoom: "#" } },
  { code: "Lab-10", type: "LAB", dayOffset: 2, start: 18.5, end: 21, title: "Lab: Discord bot + slash command", format: "Offline", location: "Phòng D305", cls: "Lab-D305", host: "Lab Coach: M.A", desc: "Dựng Discord bot với discord.py, đăng ký slash command, nối API.", links: { slide: "#", zoom: "#" }, faqs: [{ q: "Chưa cài sẵn môi trường Python thì sao?", a: "Đến sớm 15 phút, Lab Coach hỗ trợ setup; hoặc làm theo hướng dẫn pin trong kênh Lab-D305." }] },
  { code: "LT-12", type: "LT", dayOffset: 3, start: 19.5, end: 21.5, title: "Human-AI interaction: HAX & PAIR", format: "Zoom", cls: "Lý thuyết chung", host: "Giảng viên khoá", desc: "Nguyên tắc thiết kế trải nghiệm AI: expectation setting, handoff, correction.", links: { zoom: "#" } },
  { code: "MD-5", type: "MD", dayOffset: 4, start: 20, end: 21.5, title: "Mentor duty tuần 5", format: "Zoom", cls: "Theo nhóm", host: "Mentor của nhóm", desc: "Review tiến độ trước hackathon. Gửi báo cáo tiến độ trước buổi làm việc.", links: { zoom: "#" } },
  { code: "Lab-11", type: "LAB", dayOffset: 5, start: 9, end: 11.5, title: "Lab bù: Eval runner & trace log", format: "Offline", location: "Phòng D302", cls: "Lab-D302", host: "Lab Coach: H.T", desc: "Buổi bù cho nhóm vắng Lab-10: viết eval runner, log trace lời gọi AI.", links: { zoom: "#" } },
  { code: "WS-3", type: "WS", dayOffset: 5, start: 20, end: 22, title: "Kinh nghiệm quản lý dự án & duy trì năng suất", format: "Zoom", cls: "Toàn khoá", host: "Diễn giả khách mời — Founder/CTO", desc: "Cách phát triển sản phẩm AI từ bài toán thực tế đến hướng triển khai; quản lý dự án, phân chia công việc, theo dõi tiến độ trong team.", links: { zoom: "#" }, faqs: [{ q: "Buổi này có record không?", a: "Có — record sẽ đăng tại #tài-nguyên trong vòng 24h và gắn vào block WS-3 này." }] },
  { code: "OH-6", type: "OH", dayOffset: 6, start: 15, end: 16.5, title: "Office hour cuối tuần", format: "Zoom", cls: "Chung", host: "TA trực: T101", desc: "Slot bổ sung cuối tuần cho các nhóm chạy nước rút hackathon.", links: { zoom: "#" } },

  // ---- Tuần sau ----
  { code: "LT-13", type: "LT", dayOffset: 8, start: 19.5, end: 21.5, title: "Ôn tập & định hướng Demo Day", format: "Zoom", cls: "Lý thuyết chung", host: "Giảng viên khoá", desc: "Tổng kết kiến thức, checklist chuẩn bị Demo Day.", links: {} },
  { code: "Lab-12", type: "LAB", dayOffset: 9, start: 18.5, end: 21, title: "Lab: Hoàn thiện prototype", format: "Offline", location: "Phòng D305", cls: "Lab-D305", host: "Lab Coach: M.A", desc: "Buổi lab tự do hoàn thiện prototype, Lab Coach hỗ trợ tại chỗ.", links: {} },
  { code: "WS-4", type: "WS", dayOffset: 12, start: 20, end: 22, title: "Pitching: kể chuyện sản phẩm trong 5 phút", format: "Zoom", cls: "Toàn khoá", host: "Diễn giả khách mời", desc: "Cấu trúc pitch, demo case lỗi một cách tự tin, xử lý Q&A giám khảo.", links: {} },
];

export const SESSIONS = RAW_SESSIONS.map((s) => {
  const date = day(s.dayOffset);
  return {
    ...s,
    date,
    timeLabel: `${hhmm(s.start)} – ${hhmm(s.end)}`,
    faqs: [...(s.faqs || []), ...(COMMON_FAQS[s.type] || [])],
    // nguồn enrich giả lập (thiết kế: từ kênh #thông-báo)
    source: { channel: "#thông-báo", updated: fmtDM(addDays(date, -1)) },
  };
});

// ---------- Tài nguyên (kênh #tài-nguyên → Session Linker gắn mã buổi) ----------
export const RESOURCE_KINDS = {
  slide: { label: "Slide", icon: "📑" },
  record: { label: "Record", icon: "🎥" },
  doc: { label: "Tài liệu", icon: "📄" },
  link: { label: "Link khác", icon: "🔗" },
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

// ---------- News (digest cộng đồng) ----------
// ⚠️ PLACEHOLDER taxonomy — bộ loại tin chính thức do nhóm thiết kế sau.
export const NEWS_CATEGORIES = [
  { id: "announce", label: "Thông báo", color: "#ef4444" },
  { id: "survey", label: "Khảo sát / Form", color: "#f59e0b" },
  { id: "qa", label: "Hỏi đáp", color: "#3b82f6" },
  { id: "share", label: "Chia sẻ kiến thức", color: "#22c55e" },
  { id: "resource", label: "Tài liệu", color: "#a855f7" },
];

export const NEWS = [
  { id: 1, cat: "announce", title: "Nhắc lịch Workshop 3 — 20:00 tối nay", summary: "Chủ đề: Kinh nghiệm quản lý dự án & duy trì năng suất phát triển sản phẩm. Online qua Zoom, diễn giả khách mời.", channel: "#thông-báo", author: "BTC", role: "BTC", hearts: 38, comments: 5, time: "2 giờ trước", url: "#" },
  { id: 2, cat: "announce", title: "Quy định mentor duty: gửi báo cáo trước buổi làm việc", summary: "Các team kiểm tra đã gửi báo cáo cho mentor chưa; gửi bổ sung để buổi làm việc tối nay hiệu quả nhất.", channel: "#thông-báo", author: "BTC", role: "BTC", hearts: 24, comments: 0, time: "5 giờ trước", url: "#" },
  { id: 3, cat: "qa", title: "QR báo lỗi / thiếu thẻ phòng lab", summary: "Bạn nào chưa có thẻ hoặc thẻ bị lỗi mở cổng/phòng học thì điền vào form này để Lab Coach xử lý.", channel: "#hỏi-đáp", author: "Lab Coach M.A", role: "Lab Coach", hearts: 22, comments: 22, time: "21 phút trước", url: "#" },
  { id: 4, cat: "qa", title: "Feedback, bug report vlearn.dev", summary: "Bất kỳ bug nào cứ nhắn team VLearn theo cú pháp: MSSV + Email + mô tả lỗi + hình (nếu có).", channel: "#hỏi-đáp", author: "Lab Coach S.", role: "Lab Coach", hearts: 12, comments: 231, time: "11 phút trước", url: "#" },
  { id: 5, cat: "qa", title: "Bảo lưu thì có được nhận trợ cấp học viên không?", summary: "Câu hỏi đang mở (Open) — chưa có câu trả lời chính thức. Đã chuyển vào hàng đợi TA phụ trách.", channel: "#hỏi-đáp", author: "Học viên T.T", role: "Học viên", hearts: 1, comments: 0, time: "29 phút trước", url: "#", open: true },
  { id: 6, cat: "survey", title: "Khảo sát trải nghiệm AI Tutor trên VLearn (2–3 phút)", summary: "Nhóm nghiên cứu cải thiện tính năng tóm tắt bài giảng của AI Tutor — điền giúp nhóm, ai điền rồi bọn mình điền lại!", channel: "Lab-D305", author: "T227", role: "Học viên", hearts: 15, comments: 3, time: "3 giờ trước", url: "#" },
  { id: 7, cat: "survey", title: "Form khảo sát hackathon: khó khăn khi làm Lab demo", summary: "Nhóm cần khảo sát về các khó khăn trong buổi thực hành, chỉ mất 1 phút. Nhóm nào cần khảo sát chéo cứ DM.", channel: "Lab-D305", author: "T087", role: "Học viên", hearts: 8, comments: 1, time: "4 giờ trước", url: "#" },
  { id: 8, cat: "share", title: "[Deep-dive] BEV — Góc nhìn “thượng đế” của xe tự hành", summary: "TL;DR: BEV (Bird's-Eye View) đưa thông tin từ camera/LiDAR về một bản đồ nhìn từ trên xuống — nền tảng của perception hiện đại.", channel: "#bài-học", author: "GR16 — T112", role: "Học viên", hearts: 3, comments: 2, time: "16 giờ trước", url: "#" },
  { id: 9, cat: "share", title: "Bạn đang “làm chủ AI” hay “lạm dụng AI”?", summary: "Suy ngẫm về ranh giới giữa dùng AI để tăng tốc và đánh mất khả năng tự giải quyết vấn đề.", channel: "#bài-học", author: "T017", role: "Học viên", hearts: 1, comments: 0, time: "4 giờ trước", url: "#" },
  { id: 10, cat: "share", title: "[Research] Gợi ý dataset cho đề tài CV thuộc track RAV", summary: "TL;DR: Không chọn dataset chỉ vì nó lớn hoặc phổ biến — chọn theo bài toán; kèm danh sách dataset đề xuất.", channel: "#bài-học", author: "GR16 — T112", role: "Học viên", hearts: 9, comments: 3, time: "20 giờ trước", url: "#" },
  { id: 11, cat: "resource", title: "Slide Workshop WS2: Problem → MVP Canvas", summary: "Slide buổi WS2 đã lên #tài-nguyên và được gắn vào block WS-2 trên trang Lịch học. Nội bộ chương trình, không public.", channel: "#tài-nguyên", author: "BTC", role: "BTC", hearts: 30, comments: 0, time: "1 ngày trước", url: "#" },
  { id: 12, cat: "resource", title: "Ngân hàng đề chính thức Build Phase Cohort 4", summary: "Truy cập ngân hàng đề thi chính thức — dùng cho mọi nhóm trong Build Phase.", channel: "#tài-nguyên", author: "BTC", role: "BTC", hearts: 61, comments: 13, time: "4 ngày trước", url: "#" },
  { id: 13, cat: "announce", title: "Đổi phòng Lab-11 sang D302 (buổi bù sáng thứ 7)", summary: "Phòng D305 bận lịch bảo trì thiết bị. Buổi bù Lab-11 chuyển sang D302, giờ giấc giữ nguyên 09:00 – 11:30.", channel: "#thông-báo", author: "BTC", role: "BTC", hearts: 17, comments: 6, time: "6 giờ trước", url: "#" },
  { id: 14, cat: "announce", title: "Chốt danh sách nhóm hackathon trước 23:59 Chủ nhật", summary: "Nhóm nào còn thiếu thành viên đăng bài vào #tìm-đội để BTC ghép. Sau hạn chốt sẽ không đổi nhóm.", channel: "#thông-báo", author: "BTC", role: "BTC", hearts: 45, comments: 19, time: "1 ngày trước", url: "#" },
  { id: 15, cat: "announce", title: "Office hour cuối tuần OH-6 mở thêm slot 15:00", summary: "Do nhu cầu tăng trước hackathon, TA trực mở thêm một slot chiều Chủ nhật. Đăng ký theo thứ tự nhắn trong kênh.", channel: "#thông-báo", author: "TA T101", role: "TA", hearts: 20, comments: 4, time: "1 ngày trước", url: "#" },
  { id: 16, cat: "qa", title: "Deadline nộp Lab-10 tính theo giờ nào?", summary: "Chốt: 23:59 cùng ngày diễn ra buổi lab, tính theo giờ hệ thống nộp bài. Nộp trễ vẫn nhận nhưng trừ điểm chuyên cần.", channel: "#hỏi-đáp", author: "Học viên T203", role: "Học viên", hearts: 14, comments: 9, time: "7 giờ trước", url: "#" },
  { id: 17, cat: "qa", title: "Vắng Lab-10 có được học bù ở Lab-11 không?", summary: "Câu hỏi đang mở (Open) — TA đang xác nhận với Lab Coach về sức chứa phòng D302.", channel: "#hỏi-đáp", author: "Học viên T145", role: "Học viên", hearts: 6, comments: 2, time: "8 giờ trước", url: "#", open: true },
  { id: 18, cat: "qa", title: "Dùng API key cá nhân hay key chung của khoá?", summary: "Ưu tiên key chung do BTC cấp để tính hạn mức; key cá nhân chỉ dùng khi key chung hết quota, nhớ không commit lên repo.", channel: "#hỏi-đáp", author: "Lab Coach H.T", role: "Lab Coach", hearts: 33, comments: 11, time: "1 ngày trước", url: "#" },
  { id: 19, cat: "qa", title: "Không vào được Zoom: báo “waiting for host”", summary: "Buổi chỉ mở phòng trước giờ học 10 phút. Nếu quá giờ mà vẫn chờ, nhắn trực tiếp TA trực để được cho vào.", channel: "#hỏi-đáp", author: "Học viên T066", role: "Học viên", hearts: 5, comments: 27, time: "2 ngày trước", url: "#" },
  { id: 20, cat: "survey", title: "Bình chọn chủ đề Workshop 4: Pitching hay Growth?", summary: "BTC lấy ý kiến để chốt nội dung WS-4. Poll đóng vào tối thứ 6, mỗi người chọn 1 phương án.", channel: "#thông-báo", author: "BTC", role: "BTC", hearts: 27, comments: 8, time: "1 ngày trước", url: "#" },
  { id: 21, cat: "survey", title: "Form đăng ký suất mentor 1-1 trước Demo Day", summary: "Mỗi nhóm được 1 slot 30 phút. Điền nguyện vọng khung giờ, BTC sẽ xếp lịch và báo lại trong tuần.", channel: "#thông-báo", author: "BTC", role: "BTC", hearts: 36, comments: 5, time: "2 ngày trước", url: "#" },
  { id: 22, cat: "survey", title: "Khảo sát nhanh: bạn kẹt nhất ở khâu nào của RAG?", summary: "Nhóm nghiên cứu tổng hợp điểm nghẽn để đề xuất buổi ôn tập bổ sung. 5 câu, khoảng 2 phút.", channel: "Lab-D305", author: "T112", role: "Học viên", hearts: 11, comments: 2, time: "3 ngày trước", url: "#" },
  { id: 23, cat: "share", title: "[Tips] Chunking bao nhiêu token là hợp lý cho tài liệu tiếng Việt?", summary: "TL;DR: tiếng Việt tốn token hơn tiếng Anh ~1.5x — chunk 300–500 token kèm overlap 15% cho kết quả retrieval ổn định nhất trong test của mình.", channel: "#bài-học", author: "GR07 — T203", role: "Học viên", hearts: 42, comments: 14, time: "1 ngày trước", url: "#" },
  { id: 24, cat: "share", title: "Bài học sau khi làm hỏng golden set của nhóm", summary: "Chia sẻ thật lòng: sửa golden set cho khớp output của model là tự lừa chính mình. Ghi lại quy trình bọn mình dùng để tránh lặp lại.", channel: "#bài-học", author: "GR11 — T088", role: "Học viên", hearts: 29, comments: 7, time: "2 ngày trước", url: "#" },
  { id: 25, cat: "resource", title: "Record LT-10: Eval & Golden set đã lên kênh", summary: "Video buổi LT-10 đã đăng ở #tài-nguyên và được gắn vào block LT-10 trên trang Lịch học. Kèm slide bản PDF.", channel: "#tài-nguyên", author: "BTC", role: "BTC", hearts: 18, comments: 1, time: "3 ngày trước", url: "#" },
];

export const isHot = (n) => n.hearts + n.comments >= 20;
