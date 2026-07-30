from datetime import datetime, timezone
import json
from pathlib import Path
import os
import tempfile


def atomic_write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file: json.dump(value, file, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def read_records(path):
    try: return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError: return []


def merge_records(existing, incoming, limit=None, replace_existing=False):
    seen = {(record.get("channel_id"), record.get("message_id")) for record in existing}
    incoming = list(incoming)
    if replace_existing:
        replacements = {(record.get("channel_id"), record.get("message_id")): record for record in incoming}
        result = [replacements.pop((record.get("channel_id"), record.get("message_id")), record) for record in existing]
        incoming = replacements.values()
        seen = {(record.get("channel_id"), record.get("message_id")) for record in result}
    else:
        result = list(existing)
    for record in incoming:
        key = record.get("channel_id"), record.get("message_id")
        if key not in seen: result.append(record); seen.add(key)
        if limit and len(result) >= limit: break
    return result


class Checkpoint:
    def __init__(self, path, data=None):
        self.path, self.data = Path(path), data or {"collected_message_ids": {}, "completed": [], "current_target": None, "last_save_time": None}
    @classmethod
    def load(cls, path):
        try: return cls(path, json.loads(Path(path).read_text(encoding="utf-8")))
        except FileNotFoundError: return cls(path)
    @property
    def completed(self): return set(self.data["completed"])
    def has(self, channel_id, message_id): return message_id in self.data["collected_message_ids"].get(channel_id, [])
    def add(self, channel_id, message_id):
        ids = self.data["collected_message_ids"].setdefault(channel_id, [])
        if message_id not in ids: ids.append(message_id)
        return self
    def complete(self, target): self.data["completed"] = sorted(self.completed | {target}); return self
    def reopen(self, target): self.data["completed"] = sorted(self.completed - {target}); return self
    def target(self, target): self.data["current_target"] = target; return self
    def save(self): self.data["last_save_time"] = datetime.now(timezone.utc).isoformat(); atomic_write_json(self.path, self.data); return self
