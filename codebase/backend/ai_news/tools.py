"""Tool cho Daily AI News: crawl (Tavily) + verify source (httpx). Thuần I/O."""

import httpx

_UA = {"User-Agent": "Mozilla/5.0 (compatible; CompanionBot/1.0)"}


def tavily_news_search(query: str, api_key: str, max_results: int = 6) -> list[dict]:
    """Tìm tin/bài AI mới qua Tavily (topic=news). Trả [{title, url, content}]."""
    if not api_key:
        return []
    try:
        resp = httpx.post("https://api.tavily.com/search", timeout=20.0, json={
            "api_key": api_key, "query": query, "topic": "news", "days": 14,
            "max_results": max_results, "include_answer": False,
        })
        resp.raise_for_status()
        return [{"title": r.get("title") or "", "url": r.get("url") or "",
                 "content": (r.get("content") or "")[:400]}
                for r in resp.json().get("results", []) if r.get("url")]
    except httpx.HTTPError:
        return []


def verify_url(url: str, timeout: float = 8.0) -> tuple[bool, int, str]:
    """GET url, xác nhận truy cập được (2xx). Trả (ok, status, trích nội dung)."""
    try:
        resp = httpx.get(url, timeout=timeout, follow_redirects=True, headers=_UA)
        ok = 200 <= resp.status_code < 300
        return ok, resp.status_code, (resp.text[:2000] if ok else "")
    except httpx.HTTPError:
        return False, 0, ""
