"""
Federal Register scraper.
Uses the public API: https://www.federalregister.gov/api/v1/documents.json
Filters for Rules and Proposed Rules published in the last 7 days.
"""

import requests
from datetime import datetime, timedelta, timezone

SOURCE = "Federal Register"
BASE_URL = "https://www.federalregister.gov/api/v1/documents.json"
MAX_PAGES = 5


ALLOWED_TYPES = {"Rule", "Proposed Rule"}


def fetch(days_back: int = 7) -> list[dict]:
    results = []
    since = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")

    # NOTE: The FR API's conditions[type][] filter silently returns 0 results,
    # so we fetch all doc types and filter client-side.
    base_params = [
        ("fields[]", "title"),
        ("fields[]", "abstract"),
        ("fields[]", "html_url"),
        ("fields[]", "publication_date"),
        ("fields[]", "agencies"),
        ("fields[]", "type"),
        ("conditions[publication_date][gte]", since),
        ("per_page", 100),
        ("order", "newest"),
    ]

    page = 1
    while page <= MAX_PAGES:
        params = base_params + [("page", page)]
        try:
            resp = requests.get(BASE_URL, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[Federal Register] Error on page {page}: {e}")
            break

        documents = data.get("results", [])
        if not documents:
            break

        for doc in documents:
            doc_type = doc.get("type", "")
            if doc_type not in ALLOWED_TYPES:
                continue

            agencies = doc.get("agencies") or []
            agency_names = ", ".join(
                a.get("name", "") for a in agencies if isinstance(a, dict)
            )
            full_text = doc.get("abstract") or ""
            if agency_names:
                full_text = f"Agencies: {agency_names}\n\n{full_text}"

            results.append(
                {
                    "source": SOURCE,
                    "title": doc.get("title", "").strip(),
                    "url": doc.get("html_url", ""),
                    "published_at": doc.get("publication_date", ""),
                    "full_text": full_text[:8000],
                }
            )

        total_pages = data.get("total_pages", 1)
        if page >= total_pages:
            break
        page += 1

    return results


if __name__ == "__main__":
    items = fetch(days_back=7)
    print(f"[Federal Register] Found {len(items)} rules/proposed rules")
    for item in items[:5]:
        print(f"  - [{item['published_at']}] {item['title'][:80]}")
        print(f"    {item['url']}")