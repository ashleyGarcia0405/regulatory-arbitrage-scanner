"""Perplexity web search — real when PERPLEXITY_API_KEY is set, stub otherwise."""
import hashlib
import requests

from config import PERPLEXITY_API_KEY

_DEPTH_TO_MODEL = {
    "fast": "sonar",
    "standard": "sonar-pro",
    "deep": "sonar-deep-research",
}

_DEPTH_TO_TIMEOUT = {
    "fast": 30,
    "standard": 60,
    "deep": 180,
}

_cache: dict[str, str] = {}


def search(query: str, depth: str = "standard", from_date: str | None = None) -> str:
    cache_key = hashlib.sha256(f"{query}:{depth}:{from_date}".encode()).hexdigest()
    if cache_key in _cache:
        return _cache[cache_key]

    if not PERPLEXITY_API_KEY:
        result = (
            f"[STUB — PERPLEXITY_API_KEY not set] search_web called with: "
            f"query={query!r}, depth={depth!r}, from_date={from_date!r}"
        )
        _cache[cache_key] = result
        return result

    model = _DEPTH_TO_MODEL.get(depth, "sonar-pro")
    payload: dict = {
        "model": model,
        "messages": [{"role": "user", "content": query}],
    }
    if from_date:
        payload["search_after_date_filter"] = from_date

    timeout = _DEPTH_TO_TIMEOUT.get(depth, 60)
    try:
        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout,
        )
    except requests.Timeout:
        result = f"[SEARCH TIMEOUT] query={query!r} depth={depth!r} timed out after {timeout}s"
        _cache[cache_key] = result
        return result
    if not resp.ok:
        result = f"[SEARCH ERROR {resp.status_code}] {resp.text[:200]}"
        _cache[cache_key] = result
        return result
    result = resp.json()["choices"][0]["message"]["content"]
    _cache[cache_key] = result
    return result