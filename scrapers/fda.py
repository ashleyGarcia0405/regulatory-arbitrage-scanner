"""
FDA scraper.
Parses two FDA RSS feeds:
  - Food safety: https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/food/rss.xml
  - MedWatch safety alerts: https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/medwatch-safety-alerts/rss.xml
"""

import feedparser
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

SOURCE = "FDA"

FEEDS = [
    {
        "url": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml",
        "label": "FDA Press Releases",
    },
    {
        "url": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/recalls/rss.xml",
        "label": "FDA Recalls & Safety Alerts",
    },
]


def _parse_date(entry) -> str:
    for attr in ("published", "updated"):
        raw = getattr(entry, attr, None)
        if raw:
            try:
                return parsedate_to_datetime(raw).date().isoformat()
            except Exception:
                return raw
    return ""


def fetch() -> list[dict]:
    results = []

    for feed_meta in FEEDS:
        url = feed_meta["url"]
        label = feed_meta["label"]
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"[FDA] Error fetching {label}: {e}")
            continue

        if feed.bozo and feed.bozo_exception:
            print(f"[FDA] Warning parsing {label}: {feed.bozo_exception}")

        for entry in feed.entries:
            title = (entry.get("title") or "").strip()
            link = entry.get("link") or ""
            summary = entry.get("summary") or entry.get("description") or ""

            if not title or not link:
                continue

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
    print(f"[FDA] Found {len(items)} items")
    for item in items[:5]:
        print(f"  - [{item['published_at']}] {item['title'][:80]}")
        print(f"    {item['url']}")