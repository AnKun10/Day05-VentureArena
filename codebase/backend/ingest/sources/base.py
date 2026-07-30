from typing import Protocol

from ..models import RawPost


class Source(Protocol):
    def fetch(self, since: dict[str, int]) -> list[RawPost]: ...
