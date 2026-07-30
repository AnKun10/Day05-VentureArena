"""ManifestSource — đọc manifest.json (schema v3) từ snapshot crawl Discord.

Map nguồn → kênh pipeline: sharing → chia-se · lessons → bai-hoc ·
resources (text) → tai-nguyen. Các kênh khác trong manifest (general,
questions, announcements…) không thuộc pipeline bản tin nên bỏ qua.

Đặc thù dữ liệu crawl (Selenium không thu được mọi field):
- author luôn null → "(ẩn danh)" / role "Học viên".
- reactions thường null → hearts 0.
- timestamp dạng "...Z" → normalize thành "+00:00" (Python 3.10
  fromisoformat không nhận hậu tố Z); thiếu timestamp → fallback
  FALLBACK_TS để sort/recency không vỡ.
- Message chào mừng mặc định của kênh ("Chào mừng bạn đến với #…") bị bỏ.
"""

import json
import re
from pathlib import Path

from ..models import RawComment, RawPost
from .discord_source import map_role

_FORUM_MAP = {"sharing": "chia-se", "lessons": "bai-hoc"}
_RESOURCE_SOURCE = "resources"
_ANNOUNCE_MAP = {
    "announcements": "thong-bao:all",
    "cohort_3_common_announcements": "thong-bao:3",
    "cohort_4_common_announcements": "thong-bao:4",
}
_FALLBACK_AUTHOR = "(ẩn danh)"
FALLBACK_TS = "2026-07-31T00:00:00+00:00"

# Header DOM dính đầu text_content, KHÔNG có newline:
#   "<Tên>—21:49 26/7/26lúc 21:49 Chủ Nhật, 26 tháng 7, 2026<nội dung...>"
# Tên có thể chứa " — " lẫn " - " — neo theo cấu trúc giờ/ngày nên vẫn tách đúng.
_HEADER = re.compile(
    r"^(?P<author>.{1,80}?)—(?P<h>\d{1,2}):(?P<mi>\d{2}) "
    r"(?P<d>\d{1,2})/(?P<mo>\d{1,2})/(?P<y>\d{2})"
    r"lúc \d{1,2}:\d{2} [^,]{1,20}, \d{1,2} tháng \d{1,2}, \d{4}"
)
# Biến thể ngày tương đối: "<Tên>—Hôm qua lúc 15:57lúc 15:57 Thứ Tư, 29 tháng 7, 2026"
# — ngày tuyệt đối lấy từ vế "…, d tháng m, yyyy" phía sau.
_HEADER_REL = re.compile(
    r"^(?P<author>.{1,80}?)—(?:Hôm nay|Hôm qua) lúc (?P<h>\d{1,2}):(?P<mi>\d{2})"
    r"lúc \d{1,2}:\d{2} [^,]{1,20}, (?P<d>\d{1,2}) tháng (?P<mo>\d{1,2}), (?P<y4>\d{4})"
)
# Artifact nút reaction cuối message: "...cảm ơn a1Thêm Biểu Cảm"
_REACTION_TAIL = re.compile(r"\d*Thêm Biểu Cảm\s*$")


def split_header(content: str) -> tuple[str | None, str | None, str]:
    """Tách (author, iso_ts +07:00, nội_dung_sạch) từ content crawl.

    Không thấy header → (None, None, content đã strip artifact)."""
    author = ts = None
    m = _HEADER.match(content)
    if m:
        author = m.group("author").strip()
        ts = (f"20{m.group('y')}-{int(m.group('mo')):02d}-{int(m.group('d')):02d}"
              f"T{int(m.group('h')):02d}:{m.group('mi')}:00+07:00")
        content = content[m.end():]
    else:
        m = _HEADER_REL.match(content)
        if m:
            author = m.group("author").strip()
            ts = (f"{m.group('y4')}-{int(m.group('mo')):02d}-{int(m.group('d')):02d}"
                  f"T{int(m.group('h')):02d}:{m.group('mi')}:00+07:00")
            content = content[m.end():]
    return author, ts, _REACTION_TAIL.sub("", content).strip()


def _ts(value) -> str:
    if not value:
        return FALLBACK_TS
    return value.replace("Z", "+00:00") if value.endswith("Z") else value


def _author(obj: dict | None) -> str:
    a = (obj or {}).get("author") or {}
    return a.get("display_name") or a.get("name") or _FALLBACK_AUTHOR


def _hearts(message: dict | None) -> int:
    reactions = (message or {}).get("reactions") or []
    return sum(int(r.get("count") or 0) for r in reactions if isinstance(r, dict))


class ManifestSource:
    def __init__(self, path: str):
        self.path = Path(path)

    def fetch(self, since: dict[str, int]) -> list[RawPost]:
        manifest = json.loads(self.path.read_text(encoding="utf-8"))
        posts: list[RawPost] = []
        for channel in manifest.get("channels", []):
            name = channel.get("source_name")
            if name in _FORUM_MAP:
                target = _FORUM_MAP[name]
                for post in channel.get("forum_posts") or []:
                    raw = self._forum_post(post, target)
                    if raw and int(raw.message_id) > since.get(target, 0):
                        posts.append(raw)
            elif name == _RESOURCE_SOURCE:
                for message in channel.get("messages") or []:
                    raw = self._resource_post(message)
                    if raw and int(raw.message_id) > since.get("tai-nguyen", 0):
                        posts.append(raw)
            elif name in _ANNOUNCE_MAP:
                target = _ANNOUNCE_MAP[name]
                for message in channel.get("messages") or []:
                    raw = self._announce_post(message, target)
                    if raw and int(raw.message_id) > since.get(target, 0):
                        posts.append(raw)
        return posts

    @staticmethod
    def _forum_post(post: dict, target: str) -> RawPost | None:
        starter = post.get("starter_message") or {}
        raw_content = (starter.get("content") or post.get("content") or "").strip()
        header_author, header_ts, content = split_header(raw_content)
        title = (post.get("title") or "").strip()
        if not title and not content:
            return None  # card thấy trên catalog nhưng crawler chưa đọc được gì
        comments = []
        for c in post.get("comments") or []:
            c_author, c_ts, c_content = split_header((c.get("content") or "").strip())
            if not c_content:
                continue
            author = c_author or _author(c)
            comments.append(RawComment(
                id=str(c["id"]),
                author=author,
                author_role=map_role([author]),
                content=c_content,
                created_at=c_ts or _ts(c.get("created_at")),
            ))
        author = header_author or _author(starter or post)
        return RawPost(
            message_id=str(post["id"]),
            channel=target,
            title=title or content.splitlines()[0][:120],
            content=content or title,
            author=author,
            author_role=map_role([author]),
            jump_url=starter.get("jump_url") or post.get("url") or "",
            created_at=_ts(starter.get("created_at") or post.get("created_at")) if (
                starter.get("created_at") or post.get("created_at")) else (header_ts or FALLBACK_TS),
            hearts=_hearts(starter) or _hearts(post),
            comments=comments,
        )

    @staticmethod
    def _resource_post(message: dict) -> RawPost | None:
        raw_content = (message.get("content") or "").strip()
        if not raw_content or "Chào mừng bạn đến với #" in raw_content[:80]:
            return None
        header_author, header_ts, content = split_header(raw_content)
        if not content:
            return None
        if content.startswith("@") and len(content) < 25:
            return None  # message chỉ mention (@Learner…) — không phải tài nguyên
        title = next((line.strip() for line in content.splitlines() if line.strip()), content)
        author = header_author or _author(message)
        return RawPost(
            message_id=str(message["id"]),
            channel="tai-nguyen",
            title=title[:120],
            content=content,
            author=author,
            author_role=map_role([author]),
            jump_url=message.get("jump_url") or "",
            created_at=_ts(message.get("created_at")) if message.get("created_at")
            else (header_ts or FALLBACK_TS),
            hearts=_hearts(message),
        )

    @staticmethod
    def _announce_post(message: dict, channel: str) -> RawPost | None:
        raw_content = (message.get("content") or "").strip()
        if not raw_content or "Chào mừng bạn đến với #" in raw_content[:80]:
            return None
        header_author, header_ts, content = split_header(raw_content)
        if not content:
            return None
        title = next((line.strip() for line in content.splitlines() if line.strip()), content)
        author = header_author or _author(message)
        return RawPost(
            message_id=str(message["id"]),
            channel=channel,
            title=title[:120],
            content=content,
            author=author,
            author_role=map_role([author]),
            jump_url=message.get("jump_url") or "",
            created_at=_ts(message.get("created_at")) if message.get("created_at")
            else (header_ts or FALLBACK_TS),
            hearts=_hearts(message),
        )
