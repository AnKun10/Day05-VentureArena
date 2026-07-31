// ============================================================
// CẤU HÌNH KHUNG APP — một nguồn sự thật cho tiêu đề trang, mô tả và
// placeholder tìm kiếm. Trước đây mỗi page tự đặt tiêu đề với cỡ chữ
// khác nhau (24 / 22 / 26px) nên 3 trang trông như 3 sản phẩm.
// ============================================================

// Lớp học của user — "personalized" ở mức lọc theo lựa chọn trên UI,
// đúng phạm vi non-goal #3 (MASTERPLAN.md §2): không đăng nhập, không hồ sơ sâu.
export const CLASSES = ["Lab-D305", "Lab-D302", "Lý thuyết chung"];

// Buổi thuộc các nhóm này dành cho tất cả mọi người → không bao giờ bị
// bộ lọc lớp ẩn đi.
export const SHARED_CLASSES = ["Chung", "Toàn khoá", "Theo nhóm", "Lý thuyết chung"];

export const PAGES = {
  news: {
    label: "Bản tin",
    title: "Bản tin cộng đồng",
    desc: "Tổng hợp từ các kênh Discord của khoá, đã phân loại theo chủ đề",
    searchHint: "Tìm trong bản tin: tiêu đề, kênh, người đăng…",
  },
  calendar: {
    label: "Lịch học",
    title: "Lịch học",
    desc: "Lịch tuần theo buổi — bấm vào một buổi để xem chi tiết và tài liệu",
    searchHint: "Tìm buổi học: mã buổi, tên buổi, giảng viên…",
  },
  resources: {
    label: "Tài nguyên",
    title: "Tài nguyên",
    desc: "Slide, record và tài liệu từ #tài-nguyên, tự động gắn vào buổi học tương ứng",
    searchHint: "Tìm tài nguyên: tên tài liệu hoặc mã buổi...",
  },
};
