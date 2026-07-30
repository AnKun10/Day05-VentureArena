# Hướng dẫn đọc dữ liệu Discord đã crawl và đã chuyển đổi

Thư mục `data/discord_crawl/` chứa dữ liệu được đọc từ giao diện Discord bằng phiên Edge/Selenium đã đăng nhập. Nó không dùng Discord Bot API cho server nguồn và không tải file attachment về máy.

## Hai lớp dữ liệu

| Lớp | File | Mục đích |
|---|---|---|
| Raw crawl | `<source>.json`, `<forum>/<thread_id>.json` | Bản ghi sát với DOM được Selenium đọc tại thời điểm crawl. Dùng để kiểm tra, crawl lại, hoặc tái tạo manifest. |
| Forum catalog | `<forum>/posts.json` | Danh sách card Forum đã thấy, kể cả post chưa lấy được message. |
| Manifest chuyển đổi | `manifest.json` | Schema thống nhất cho phân tích hoặc replay bằng Bot API ở server đích. Đây là file nên dùng làm đầu vào chính. |
| Trạng thái vận hành | `checkpoint.json`, `<forum>/scan-report.json` | Resume và bằng chứng quét; không dùng làm dữ liệu phân tích. |

`manifest.json` được tạo lại từ raw crawl. Nó không xóa raw file và không thay đổi dữ liệu nguồn.

## Raw crawl: cách đọc

### Text channel

Ví dụ: `data/discord_crawl/cohort_3_common_announcements.json`.

Mỗi phần tử là một message. Các field thường dùng:

```json
{
  "message_id": "...",
  "channel_id": "...",
  "channel_name": "cohort_3_common_announcements",
  "author_display_name": "...",
  "author_id": null,
  "timestamp": "2026-07-30T10:20:33.451Z",
  "text_content": "Nội dung giữ nguyên xuống dòng\nhttps://example.test",
  "content_urls": ["https://example.test"],
  "jump_url": "https://discord.com/channels/<guild>/<channel>/<message>",
  "reply_to_message_id": null,
  "attachments": [],
  "embeds": [],
  "reactions": []
}
```

`text_content` là plaintext để phân tích hoặc replay. `content_urls` là URL được tách riêng; không thay thế hoặc loại bỏ URL trong `text_content`.

### Forum

Ví dụ:

```text
data/discord_crawl/questions/posts.json
data/discord_crawl/questions/<thread_id>.json
```

- `posts.json` cho biết post nào đã xuất hiện trong catalog, với `thread_id`, `title`, và URL post.
- Mỗi `<thread_id>.json` chứa các message của một post/thread. `post_thread_id`, `post_title`, và `post_url` liên kết message với Forum post cha.
- Một post vẫn hợp lệ khi có trong `posts.json` nhưng chưa có file thread hoặc file thread rỗng: khi đó crawler nhìn thấy card nhưng chưa đọc được nội dung.

## Manifest chuyển đổi: cách đọc

`data/discord_crawl/manifest.json` có `schema_version: 3` và tách thành `channels[]`.

### Text channel trong manifest

```json
{
  "source_name": "cohort_3_common_announcements",
  "type": "text",
  "id": "<source_channel_id>",
  "url": "https://discord.com/channels/<guild>/<channel>",
  "messages": [
    {
      "id": "<source_message_id>",
      "content": "...",
      "content_urls": [],
      "author": {"id": null, "display_name": null, "roles": null},
      "created_at": "...",
      "jump_url": "...",
      "attachments": [],
      "reference": null
    }
  ]
}
```

### Forum trong manifest

```json
{
  "source_name": "questions",
  "type": "forum",
  "forum_scan": {},
  "forum_posts": [
    {
      "id": "<source_thread_id>",
      "title": "...",
      "url": "https://discord.com/channels/<guild>/<forum>/<thread>",
      "starter_message": null,
      "comments": [],
      "messages": []
    }
  ]
}
```

- `starter_message` là message sớm nhất theo `created_at`.
- `comments` là các message còn lại theo thời gian.
- `messages` giữ toàn bộ danh sách theo thời gian và là nguồn tương thích cho rebuild.
- Không dùng `id` của manifest để giả định ID sẽ được giữ nguyên ở server đích. Rebuild luôn tạo Discord message/channel ID mới.

## Mapping raw sang manifest

| Raw crawl | Manifest | Ghi chú |
|---|---|---|
| `message_id` | `id` | Giữ ID nguồn để tham chiếu nội bộ. |
| `text_content` | `content` | Giữ plaintext và xuống dòng khi raw còn giữ được. |
| `timestamp` | `created_at` | Timestamp nguồn, không phải timestamp replay. |
| `jump_url` | `jump_url`, `location.message_url` | Link message nguồn. |
| `author_display_name`, `author_id` | `author.display_name`, `author.id` | Selenium có thể không đọc được ID/tên ở một số DOM. |
| `attachments` | `attachments` | Chỉ metadata/URL; không có file binary. |
| `reply_to_message_id` | `reference.message_id` | Chỉ có khi DOM cung cấp được. |
| `post_thread_id`, `post_title` | `forum_posts[].id`, `title` | Dùng để nhóm raw thread thành Forum post. |

## `null`, `[]`, và dữ liệu thiếu

- `null`: không quan sát hoặc không thể xác định đáng tin cậy. Không được thay bằng giá trị đoán.
- `[]`: crawler quan sát được field nhưng không thấy phần tử nào.
- `data_availability` và `author.role_snapshot_status` nói rõ các dữ liệu Selenium không thu thập được, như role, embed Discord gốc, reaction, pin, tên category hoặc permission overwrite.

Đặc biệt, attachment URL có thể hết hạn hoặc mất quyền truy cập sau này. Không coi URL là bản sao file.

## Kiểm tra độ đầy đủ Forum

`<forum>/scan-report.json` ghi kết quả theo kiểu sắp xếp `recent activity` của Discord:

```json
{
  "sorts": {
    "sort-and-view-sort-by-recent-activity": {
      "passes": 2,
      "new_post_counts": [31, 0],
      "converged": true
    }
  },
  "converged": true
}
```

`converged: true` chỉ có nghĩa là card ID ổn định qua hai pass của sort `recent activity`. Nó không chứng minh Discord đã hiển thị mọi post archived, hidden, deleted, hoặc post chưa được giao diện tải. Chỉ xem dataset là hoàn chỉnh khi số post khớp với kiểm tra trực quan của người vận hành.

## Lệnh đọc nhanh (PowerShell)

```powershell
$manifest = Get-Content -Raw data/discord_crawl/manifest.json | ConvertFrom-Json

# Đếm message text và Forum post theo source
$manifest.channels | ForEach-Object {
  [pscustomobject]@{
    source = $_.source_name
    type = $_.type
    messages = @($_.messages).Count
    forum_posts = @($_.forum_posts).Count
  }
}

# Xem post Forum chưa có nội dung crawl
$manifest.channels |
  Where-Object type -eq forum |
  ForEach-Object { $_.forum_posts } |
  Where-Object { $null -eq $_.starter_message }

# Xem một message đã chuyển đổi, gồm content, URL, attachment và link nguồn
$manifest.channels |
  Where-Object source_name -eq cohort_3_common_announcements |
  Select-Object -ExpandProperty messages |
  Select-Object -First 1 |
  ConvertTo-Json -Depth 8
```

Không dùng `checkpoint.json` để thống kê message hoặc post: nó chỉ đánh dấu tiến độ để tránh crawl/replay trùng.

## Dùng cho replay và phân tích

- Phân tích/dataset: đọc `manifest.json`, sau đó truy ngược raw file khi cần xác minh một record.
- Rebuild: dùng manifest và mapping state của destination; không gửi gì trở lại source guild.
- Visual replay: giữ `content` nguyên vẹn, để Discord tự unfurl URL; metadata nguồn vẫn nằm ở manifest, không nhất thiết phải hiển thị trong message đích.
- Không thể khôi phục message ID, thời gian gửi, hay danh tính Discord gốc ở server đích.
