"""
EUR-Lex scraper.
Uses the EU Publications Office Cellar SPARQL endpoint to query recent OJ L-series
(legislative) acts. The EUR-Lex web interface is behind AWS WAF and cannot be scraped
directly.

Cellar SPARQL endpoint: https://publications.europa.eu/webapi/rdf/sparql
CDM ontology prefix: http://publications.europa.eu/ontology/cdm#
"""

import requests
from datetime import datetime, timedelta, timezone

SOURCE = "EUR-Lex"
SPARQL_URL = "https://publications.europa.eu/webapi/rdf/sparql"
CELLAR_BASE = "http://publications.europa.eu/resource/cellar/"
EURLEX_RESOLVER = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=cellar:"


def _run_sparql(query: str, timeout: int = 20) -> list[dict]:
    try:
        resp = requests.post(
            SPARQL_URL,
            data={"query": query, "format": "application/sparql-results+json"},
            timeout=timeout,
            headers={
                "Accept": "application/sparql-results+json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        resp.raise_for_status()
        return resp.json().get("results", {}).get("bindings", [])
    except Exception as e:
        print(f"[EUR-Lex] SPARQL error: {e}")
        return []


def fetch(days_back: int = 14) -> list[dict]:
    # NOTE: The Cellar SPARQL index lags the EUR-Lex publication date by ~10-14 days,
    # so we use a 14-day window by default to ensure we always catch recent acts.
    since = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")

    # Filter to EU-level legal act types (regulation, directive, decision, recommendation)
    # and require an English work_title. Member-state national-law works are excluded
    # by the type filter.
    query = f"""
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT DISTINCT ?work ?title ?date ?type
WHERE {{
  ?work a ?type .
  VALUES ?type {{
    cdm:regulation
    cdm:directive
    cdm:decision
    cdm:recommendation
  }}
  ?work cdm:work_date_document ?date .
  ?work cdm:work_title ?title .
  FILTER(lang(?title) = 'en')
  FILTER(?date >= "{since}"^^xsd:date)
}}
ORDER BY DESC(?date)
LIMIT 200
"""

    bindings = _run_sparql(query)
    if not bindings:
        print(f"[EUR-Lex] No results from SPARQL (since {since}).")
        return []

    results = []
    seen = set()

    for b in bindings:
        work_uri = b.get("work", {}).get("value", "")
        title = b.get("title", {}).get("value", "").strip()
        date = b.get("date", {}).get("value", "")[:10]
        type_uri = b.get("type", {}).get("value", "")
        type_label = type_uri.split("#")[-1].capitalize() if type_uri else "Legislative act"

        if not title or not work_uri or work_uri in seen:
            continue
        seen.add(work_uri)

        # Build a EUR-Lex resolver URL from the Cellar URI
        cellar_id = work_uri.replace(CELLAR_BASE, "")
        if cellar_id:
            url = f"{EURLEX_RESOLVER}{cellar_id}"
        else:
            url = work_uri

        full_text = f"EUR-Lex {type_label}\nDate: {date}\nTitle: {title}"

        results.append(
            {
                "source": SOURCE,
                "title": title[:500],
                "url": url,
                "published_at": date,
                "full_text": full_text[:8000],
            }
        )

    return results


if __name__ == "__main__":
    items = fetch()
    print(f"[EUR-Lex] Found {len(items)} items")
    for item in items[:5]:
        print(f"  - [{item['published_at']}] {item['title'][:80]}")
        print(f"    {item['url']}")