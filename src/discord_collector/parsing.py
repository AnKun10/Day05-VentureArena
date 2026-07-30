from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlparse
import re


class Node:
    def __init__(self, tag="", attrs=None, parent=None): self.tag, self.attrs, self.parent, self.children = tag, dict(attrs or ()), parent, []
    def text(self): return self.render().strip("\n")
    def render(self):
        if self.tag == "br": return "\n"
        parts = []
        for child in self.children:
            value = child if isinstance(child, str) else child.render()
            if isinstance(child, Node) and child.tag in {"div", "p", "li", "ol", "ul", "blockquote", "pre"}:
                if parts and not parts[-1].endswith("\n"): parts.append("\n")
                parts.append(value)
                if value and not value.endswith("\n"): parts.append("\n")
            else:
                parts.append(value)
        value = "".join(parts)
        href = self.attrs.get("href") if self.tag == "a" else None
        if href and href.startswith(("http://", "https://")) and href not in value:
            value += ("" if not value or value[-1].isspace() else " ") + href
        return value
    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Node): yield from child.walk()


class Tree(HTMLParser):
    def __init__(self): super().__init__(); self.root = Node(); self.stack = [self.root]
    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.stack[-1]); self.stack[-1].children.append(node)
        if tag not in {"br", "img", "input", "meta", "link"}: self.stack.append(node)
    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag: self.stack = self.stack[:index]; break
    def handle_data(self, data): self.stack[-1].children.append(data)


def _tree(html): parser = Tree(); parser.feed(html); return parser.root
def _classes(node): return set(node.attrs.get("class", "").split())
def _first(node, predicate): return next((child for child in node.walk() if predicate(child)), None)
def _content(node):
    by_id = _first(node, lambda child: re.fullmatch(r"message-content-\d+", child.attrs.get("id", "")) is not None)
    if by_id: return by_id
    return _first(node, lambda child: bool(_classes(child) & {"message-content", "messageContent"}))
def _timestamp(node):
    time = _first(node, lambda child: child.tag == "time")
    return time.attrs.get("datetime") if time else None
def _id(node):
    raw = node.attrs.get("data-list-item-id", node.attrs.get("id", ""))
    if raw.startswith("chat-messages___"):
        return None
    match = re.fullmatch(r"chat-messages-(?:\d+-)?(\d+)", raw)
    return match.group(1) if match else None
def _raw_text(node): return "".join(child if isinstance(child, str) else _raw_text(child) for child in node.children)
def _attachments(node):
    return [{"filename": _raw_text(link).strip() or None, "url": link.attrs.get("href"), "content_type": link.attrs.get("data-content-type"), "size": link.attrs.get("data-size")} for link in node.walk() if link.tag == "a" and link.attrs.get("href", "").startswith(("https://cdn.discordapp.com/", "https://media.discordapp.net/"))]


def _urls(node):
    return [link.attrs["href"] for link in node.walk() if link.tag == "a" and link.attrs.get("href", "").startswith(("http://", "https://"))]


def parse_text_messages(html, channel_name, channel_id, guild_id=None, collected_at=None):
    collected_at = collected_at or datetime.now(timezone.utc).isoformat()
    records, last_author, last_timestamp = [], None, None
    for node in _tree(html).walk():
        message_id = _id(node)
        if not message_id: continue
        author = _first(node, lambda child: bool(_classes(child) & {"username", "headerText", "messageUsername"}))
        content = _content(node)
        last_author = author.text() if author else last_author
        last_timestamp = _timestamp(node) or last_timestamp
        reply = _first(node, lambda child: "reply" in child.attrs.get("data-list-item-id", "").lower())
        # Do not fall back to the whole message node: it contains Discord UI chrome,
        # unfurl cards, reactions, and author/time headers rather than plaintext.
        text = content.text() if content else None
        records.append({"message_id": message_id, "channel_id": channel_id, "channel_name": channel_name, "post_thread_id": None, "post_title": None, "author_display_name": last_author, "author_id": node.attrs.get("data-author-id"), "timestamp": last_timestamp, "text_content": text, "content_urls": _urls(content or node), "jump_url": f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}" if guild_id else None, "reply_to_message_id": _id(reply) if reply else None, "attachments": _attachments(node), "embeds": [], "reactions": [], "pinned": "pinned" in node.text().lower(), "edited": "edited" in node.text().lower(), "collected_at": collected_at})
    return records


def parse_forum_posts(html, limit):
    posts = []
    for node in _tree(html).walk():
        href = node.attrs.get("href", "")
        parts = urlparse(href).path.strip("/").split("/")
        current_forum = re.fullmatch(r"forum-channel-list-\d+___(\d+)", node.attrs.get("data-list-item-id", ""))
        thread_id = node.attrs.get("data-thread-id") or (parts[3] if node.tag == "a" and len(parts) >= 4 and parts[:1] == ["channels"] else None) or (current_forum.group(1) if current_forum else None)
        if not thread_id: continue
        title = _first(node, lambda child: "title" in _classes(child))
        label = node.attrs.get("aria-label", "")
        fallback = re.sub(r"^Bài đăng\s+|,\s*\d+\s+tin nhắn$", "", label).strip() or None
        posts.append({"thread_id": thread_id, "title": title.text() if title else node.text() or fallback, "url": href, "timestamp": _timestamp(node)})
    unique = {post["thread_id"]: post for post in posts}
    return sorted(unique.values(), key=lambda post: post["timestamp"] or "", reverse=True)[:limit]
