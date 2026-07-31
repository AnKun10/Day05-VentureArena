# Template AI Spec *(spec.md — commit trước 23:59 N1 · quality bar chốt từ thời điểm nộp)*

> Cấu trúc phủ đúng "SPEC 8 phần" của chương trình: Bằng chứng (§1-§2) · Lát cắt (§4) · Canvas (đính kèm CP1) · Augment/Automate (§4) · 4 đường đi của trải nghiệm (§6) · Kiểu lỗi (§5) · Kiểm thử (§7) · Phân công (§8). Hướng dẫn viết từng mục: `02-guide.md`.

```markdown
# AI SPEC — [Tên lát cắt] · Nhóm [XX] · Zone [X]
Hướng: [ ] A — VLearn  ☑ B — Trợ lý Học viên  [ ] C — Làn mở
Loại: [ ] Tối ưu tính năng có sẵn  ☑ Tính năng mới

## §1. User & Job
- Job executor + workflow (đính kèm worksheet JTBD / ảnh sơ đồ):
**Đối tượng:** Học viên AI Thực Chiến sử dụng Discord để theo dõi thông tin khóa học.
- Core JTBD (không tên sản phẩm/AI trong câu):
> Khi bắt đầu một ngày học, học viên muốn nhanh chóng biết những thông tin liên quan đến mình để không bỏ lỡ deadline, tài liệu và các bài chia sẻ quan trọng.
- Problem statement (KHÔNG chữ AI):
Học viên mất nhiều thời gian tìm lại thông tin trên Discord và vẫn có nguy cơ bỏ lỡ những nội dung quan trọng do thông tin phân tán trên nhiều kênh.
- Evidence (chuẩn A và/hoặc B — log đầy đủ trong repo):
- Khảo sát
Khảo sát **52 học viên AI Thực Chiến**
| Kết quả | Giá trị |
|---------|---------|
| Từng hỏi lại thông tin đã có | **79,2%** |
| Từng bỏ lỡ thông báo quan trọng | **82,7%** |
| Mất 10–30 phút/ngày để kiểm tra Discord | **47,2%** |
| Bỏ sót bài chia sẻ cộng đồng | **58,5%** |
| Bỏ sót tài liệu học tập | **54,7%** |
| Bỏ sót deadline | **50,9%** |
| Đánh giá chatbot hữu ích hoặc rất hữu ích | **98,1%** |

- Insight:
  + Discord không thiếu thông tin; vấn đề là học viên khó truy xuất lại khi cần.
  + Thông báo quan trọng dễ bị chìm giữa nhiều kênh.
  + Việc theo dõi thủ công tiêu tốn thời gian mỗi ngày.
  + Nội dung giá trị từ cộng đồng thường bị bỏ sót.
  + Người dùng sẵn sàng sử dụng chatbot tổng hợp thông tin.

- Quote:
> "Thông báo bị trôi nên em phải hỏi lại."
> "Em thường biết deadline vì bạn bè nhắc."
> "Discord có quá nhiều kênh."
> "Tìm tài liệu rất mất thời gian."
> "Có khi mentor đăng rồi nhưng em không thấy."

## §2. Impact & quyết định chọn
| Pain Point | Impact | Tần suất | Quyết định |
|------------|---------|----------|------------|
| Khó tìm lại thông tin | Cao | Hằng ngày | ✅ Chọn |
| Bỏ lỡ deadline | Cao | Hằng tuần | Không chọn riêng |
| Hỏi lặp lại | Trung bình | Thường xuyên | Không chọn |
- Lý do chọn: Pain "khó tìm lại thông tin" có phạm vi rộng nhất và là nguyên nhân dẫn đến việc bỏ lỡ deadline, tài liệu và bài chia sẻ.

## §3. Giải pháp tương tự đã nghiên cứu
- [Sản phẩm 1]: flow / đáng học / đáng né / mình khác gì
- [Sản phẩm 2]: ...

## §4. Thiết kế
- Lát cắt MỘT CÂU (1 user · 1 việc · 1 quyết định AI · 1 kết quả):
- Non-goals (≥3 thứ KHÔNG build):
- Mức prototype nhắm tới: [ ] Sketch [ ] Mock [ ] Working — phần nào mock, phần nào thật:
- Automation: [ ] augment [ ] conditional [ ] automate — lý do theo cost-of-error:
- §4b. Nguyên tắc đã áp dụng (≥4 — HAX/PAIR, xem guide):
  | Nguyên tắc | Áp cụ thể vào đâu trong prototype |
  |---|---|

## §5. Kiểu lỗi — 4 lớp chỗ khó + kịch bản (≥8) [bảng theo guide §2.5]

## §6. Bốn đường đi của trải nghiệm
- Happy path: · Low-confidence (②): · Failure/không căn cứ (①): · Correction (user sửa):
- Khi bị đòi ngoài phạm vi (③): · Case đặc thù domain (④):

## §7. Kiểm thử
- Chiều chất lượng + định nghĩa kiểm chứng được:
- Golden set (≥20 case theo cơ cấu trong guide §2.6, file trong eval/):
- Quality bar (chốt từ 23:59, giữ nguyên sau đó): "Đạt khi ≥ ___% qua bộ, và ___"
- Kết quả các lượt chạy (bảng % — cập nhật đến trước CP6):

## §8. Phân công & kế hoạch
- Phân công có tên: spec / evidence / prompt / code / demo
- Willing users (≥3 tên) + kế hoạch vòng validation CP5 (3 câu hỏi, ai log):
- Multi-prototype (nếu làm): trục khác biệt của ≥2 phương án + lý do chọn:

## §9. Changelog
| Thời điểm | Đổi gì | Vì sao (trỏ về feedback/case nào) |
```
