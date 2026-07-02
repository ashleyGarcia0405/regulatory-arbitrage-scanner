"""
SEC scraper.
Uses two SEC RSS feeds:
  - Proposed rules: https://www.sec.gov/rss/rules/proposed.xml
  - Press releases (filtered for final rules): https://www.sec.gov/news/pressreleases.rss

The EDGAR EFTS full-text endpoint is intentionally not used — it searches financial
filings (exhibits, earnings releases) rather than regulatory rulemaking documents.
"""

import feedparser
import requests
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

SOURCE = "SEC"
HEADERS = {"User-Agent": "RegulatoryArbitrageScanner contact@example.com"}

FEEDS = [
    {
        "url": "https://www.sec.gov/rss/rules/proposed.xml",
        "label": "SEC Proposed Rules",
        "filter_keywords": None,  # take all
    },
    {
        "url": "https://www.sec.gov/news/pressreleases.rss",
        "label": "SEC Press Releases",
        "filter_keywords": ["rule", "regulation", "rulemaking", "adopt", "amend", "final"],
    },
]

RULE_KEYWORDS = {"rule", "rules", "regulation", "rulemaking", "adopt", "amend", "final", "proposed"}


def _parse_date(entry) -> str:
    for attr in ("published", "updated"):
        raw = getattr(entry, attr, None)
        if raw:
            try:
                return parsedate_to_datetime(raw).date().isoformat()
            except Exception:
                return raw[:10] if raw else ""
    return ""


def _matches_keywords(text: str, keywords: list[str]) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


def fetch(days_back: int = 7) -> list[dict]:
    results = []
    seen_urls = set()

    for feed_meta in FEEDS:
        url = feed_meta["url"]
        label = feed_meta["label"]
        filter_kw = feed_meta.get("filter_keywords")

        try:
            resp = requests.get(url, timeout=20, headers=HEADERS)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as e:
            print(f"[SEC] Error fetching {label}: {e}")
            continue

        if feed.bozo and feed.bozo_exception:
            print(f"[SEC] Warning parsing {label}: {feed.bozo_exception}")

        for entry in feed.entries:
            title = (entry.get("title") or "").strip()
            link = entry.get("link") or ""
            summary = entry.get("summary") or entry.get("description") or ""

            if not title or not link or link in seen_urls:
                continue

            # Apply keyword filter if set
            if filter_kw and not _matches_keywords(title + " " + summary, filter_kw):
                continue

            seen_urls.add(link)
            results.append(
                {
                    "source": f"{SOURCE} ({label})",
                    "title": title,
                    "url": link,
                    "published_at": _parse_date(entry),
                    "full_text": summary[:8000],
                }
            )

    return results


if __name__ == "__main__":
    items = fetch()
    print(f"[SEC] Found {len(items)} items")
    for item in items[:5]:
        print(f"  - [{item['published_at']}] {item['title'][:80]}")
        print(f"    {item['url']}")