import httpx

_BAD_SUFFIXES = (".svg", ".ico", ".gif")


def pick_image(images: list[str]) -> str | None:
    for url in images:
        low = url.lower()
        if low.startswith("https://") and not low.endswith(_BAD_SUFFIXES) \
                and "logo" not in low and "favicon" not in low:
            return url
    return None


def tavily_images(query: str, api_key: str) -> list[str]:
    if not api_key:
        return []
    try:
        resp = httpx.post("https://api.tavily.com/search", timeout=10.0, json={
            "api_key": api_key, "query": query,
            "include_images": True, "max_results": 3,
        })
        resp.raise_for_status()
        return resp.json().get("images", [])
    except httpx.HTTPError:
        return []
