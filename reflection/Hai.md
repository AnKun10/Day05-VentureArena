# Reflection cá nhân — Hải

> **Vai trò:** Frontend / UI & Design System · chốt contract `/api/ask` · branch `dev/Hai`

## 1. Vai trò của mình

Mình phụ trách toàn bộ phần **người dùng nhìn thấy** của **Companion**: web UI 3 trang
(Lịch học · Tài nguyên · Bản tin) mà bot gửi link tới khi user gõ `/hub`, và **chat widget** —
mặt tiền của quyết định AI trung tâm. Ngoài code UI, việc mình cho là quan trọng nhất là
**chốt contract `/api/ask` trước** rồi mới đi làm giao diện, để ba mảnh (UI · backend · bot)
có một hình dạng dữ liệu chung mà nói chuyện.

**Nói trước cho minh bạch:** phần lớn UI dưới đây nằm ở nhánh `dev/Hai` (commit `901345d`) và
**chưa được merge vào `main`** — `main` cuối cùng đi theo bản UI dựng lại trên shadcn/ui, nối
API thật. `ChatWidget.jsx` và `TopBar.jsx` của mình hiện không có trong `main`. Vì sao lại thành
ra như vậy, mình viết ở mục 4 — đó là bài học lớn nhất của mình.

## 2. Phần mình làm (chỉ được tận file — để bảo vệ ở CP5/CP6)

Tất cả ở branch `dev/Hai`.

**a) Chat widget — 4 đường trải nghiệm R3** — `codebase/ui/src/components/ChatWidget.jsx`
Mỗi `action` render thành **một loại card nhìn khác hẳn**, để phân biệt được quyết định của AI
từ xa (quan trọng khi demo trên máy chiếu):

| `action` | Card | Đường trải nghiệm |
|---|---|---|
| `answer` | viền xanh · badge `✓ Có nguồn` · citation chip bấm được + ngày cập nhật | Happy |
| `clarify` | viền vàng · badge `? Cần làm rõ` · nút chọn sẵn, hỏi lại **tối đa 1 lần** | Mơ hồ |
| `refuse` (`escalated_to: null`) | viền xám · badge `⛔ Ngoài phạm vi` | Ngoài thẩm quyền |
| `refuse` + `escalated_to` | viền đỏ · badge `→ Đã chuyển TA` · nêu rõ TA nào, lớp nào | Failure |

Mọi card đều có nút **⚠ Báo sai** và hiện `action · confidence · latency · trace_id` — để giám khảo
thấy đây là **lời gọi AI thật, không hardcode**. Áp 5 nguyên tắc HAX: nói rõ phạm vi · trích nguồn ·
báo sai được · bàn giao cho người · hiện ngày cập nhật nguồn.

**b) Contract `/api/ask`** — `codebase/ui/README.md` § Contract, `codebase/ui/src/api/client.js`
Mình viết trước phần JSON schema (`action / answer / confidence / citations[] / clarify_options /
escalated_to / trace_id`), quy ước **field nào chưa có thì trả `null` / `[]` — UI vẫn render được**,
rồi mới dựng giao diện quanh nó. Đây là phần duy nhất của mình **sống sót vào `main`**: backend giữ
nguyên xương sống `action + citations + trace`, chỉ thêm `no_info` và rút gọn citation thành URL.

**c) Mock adapter đổi được bằng 1 biến môi trường** — `src/api/mockAsk.js`, `src/api/client.js`
`VITE_USE_MOCK=false` là chuyển sang backend thật, **không sửa một dòng UI nào**. 4 kịch bản mock =
đúng 4 đường trải nghiệm ở trên. Mục đích kép: dev được khi backend chưa lên, và làm **phương án B**
nếu hết credit lúc demo (MASTERPLAN.md §9).

**d) Design system** — `src/index.css`
Thang chữ **7 bậc cố định** (không dùng cỡ tuỳ ý ngoài danh sách), 3 tầng màu chữ, **2 bậc đổ bóng**,
gradient **chỉ dùng cho logo mark**. Lý do: bản trước dùng gradient ở 6 chỗ và cỡ chữ tuỳ hứng nên mọi
thứ trông "gần giống nhau" → mắt không phân được tầng thông tin. Thêm **focus ring dùng chung** (bản
cũ không có focus visible ở bất kỳ đâu, nghĩa là không thao tác được bằng bàn phím) và
`prefers-reduced-motion`. Font Be Vietnam Pro **self-host** để demo không phụ thuộc mạng.

**e) Khung app một nguồn sự thật** — `src/config.js`, `src/components/TopBar.jsx`
Tiêu đề / mô tả / placeholder tìm kiếm của 3 trang gom về một chỗ. Trước đó mỗi page tự đặt tiêu đề
cỡ 24 / 22 / 26px nên **3 trang trông như 3 sản phẩm khác nhau**.

**f) 3 trang nội dung** — `pages/CalendarPage.jsx` (lịch tuần, block xếp cạnh nhau khi trùng giờ),
`pages/ResourcesPage.jsx`, `pages/NewsPage.jsx` (phân loại theo taxonomy của An + mục Hot trend),
`components/SessionModal.jsx` (chi tiết buổi + tài liệu + nút "Hỏi Companion về buổi này" mồi thẳng
câu hỏi vào chat widget).

## 3. AI hỗ trợ mình thế nào

Mình dùng Claude Code chủ yếu cho **phần cơ bắp của UI**: dựng component, chuyển layout, sinh bộ icon
inline SVG, viết mock data. Chỗ nó giúp nhiều nhất không phải là "viết hộ", mà là **dựng nhanh nhiều
phương án để mình nhìn tận mắt rồi chọn** — với giao diện thì mô tả bằng lời gần như vô dụng, phải thấy
mới quyết được.

Phần mình giữ cho mình: **quy tắc thiết kế** (thang chữ 7 bậc, gradient chỉ cho logo, mỗi action một
hình dạng card) và **contract API**. AI rất sẵn lòng thêm một cỡ chữ mới hoặc một màu mới mỗi lần được
nhờ sửa — nếu không có luật viết sẵn trong `index.css` thì sau 10 lần nhờ, design system sẽ tan rã. Nên
mình viết luật **kèm lý do** ngay trong comment của file, để lần sau cả mình lẫn AI đều không phá.

## 4. Bài học từ case fail của chính mình

### Fail lớn nhất: một commit tên "UI" — không ai merge nổi

Toàn bộ phần việc của mình vào repo bằng **đúng một commit tên `UI`**: 17 file, +2245 / −419 dòng,
push lên `dev/Hai` rồi thôi. Cùng lúc đó `main` chạy tiếp 109 commit theo hướng khác (dựng lại UI trên
shadcn/ui, nối API thật). Kết quả: hai bản UI đụng nhau ở gần như mọi file chung — `App.jsx`,
`index.css`, `NewsPage`, `CalendarPage`, `ResourcesPage`, `SessionModal`, `Sidebar` — và merge trở
thành việc phải ngồi xử tay từng file. Trong sự kiện 1,5 ngày thì không ai có thời gian đó, nên
bản của mình đứng ngoài `main`.

**Bài học:** *commit lớn không phải là "làm xong nhiều", nó là "khoá cửa không cho ai vào".* Nếu mình
chia thành các commit nhỏ theo từng phần (design system → khung app → chat widget → từng trang) và mở
PR ngay sau phần đầu tiên, nhóm đã có thể lấy dần từng mảnh — ít nhất `ChatWidget` là thứ **không ai
làm trùng**, lẽ ra vào `main` được mà không đụng ai. Mình đã đánh đổi khả năng bàn giao lấy tốc độ
code, và mất cả hai.

### Điều làm đúng: contract sống lâu hơn code

Đối lập với việc trên, thứ duy nhất của mình đi được vào `main` lại là thứ mình **không viết bằng
code UI** — schema `/api/ask` viết trong README. Minh dựa vào chính contract đó để đưa logic quyết
định về backend cho bot và UI dùng chung; backend cuối cùng vẫn giữ `action + citations + trace_id`.
Rút ra: trong một nhóm 5 người làm song song, **một trang contract chốt sớm có giá trị hơn nhiều
trăm dòng code hoàn hảo chốt muộn** — code là của một người, contract là của cả nhóm.

### Fail nhỏ: mock quá tốt nên quên mất việc nối thật

Mình đầu tư khá nhiều vào `mockAsk.js` (4 kịch bản khớp theo regex, có độ trễ giả, có citation) tới
mức UI chạy mượt hoàn toàn bằng mock và mình **trì hoãn việc cắm backend thật**. Mock là phương án B
tốt, nhưng nó cũng che mất những thứ chỉ lộ ra khi gọi thật: CORS, base URL có dấu `/` thừa, độ trễ
thật của agent, câu trả lời dài quá khung card. Lần sau: **nối API thật ngay khi có endpoint rỗng đầu
tiên**, rồi mới quay lại đắp mock — chứ không làm ngược lại.