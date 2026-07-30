import json
from pathlib import Path

from ..models import RawPost


class SeedSource:
    def __init__(self, path: str):
        self.path = Path(path)

    def fetch(self, since: dict[str, int]) -> list[RawPost]:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        posts = [RawPost(**item) for item in data]
        return [p for p in posts
                if int(p.message_id) > since.get(p.channel, 0)]
