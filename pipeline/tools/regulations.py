"""Federal Register history (live) and pgvector similarity (stub)."""
import requests


_FR_BASE = "https://www.federalregister.gov/api/v1/documents"

_FR_FIELDS = [
    "document_number",
    "title",
    "type",
    "agencies",
    "publication_date",
    "effective_on",
    "action",
    "abstract",
    "docket_ids",
    "regulation_id_numbers",
    "html_url",
]


def fetch_regulation_history(document_number: str) -> str:
    url = f"{_FR_BASE}/{document_number}.json"
    params = {"fields[]": _FR_FIELDS}
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
    except requests.HTTPError as e:
        return f"[ERROR] Federal Register returned {e.response.status_code} for {document_number}"
    except requests.RequestException as e:
        return f"[ERROR] Could not reach Federal Register: {e}"

    doc = resp.json()
    agencies = ", ".join(
        a.get("name", "") for a in doc.get("agencies", [])
    )
    dockets = ", ".join(doc.get("docket_ids") or [])
    rins = ", ".join(doc.get("regulation_id_numbers") or [])

    lines = [
        f"Document: {doc.get('document_number')}",
        f"Type: {doc.get('type')}",
        f"Title: {doc.get('title')}",
        f"Agencies: {agencies}",
        f"Published: {doc.get('publication_date')}",
        f"Effective: {doc.get('effective_on') or 'not specified'}",
        f"Action: {doc.get('action') or 'not specified'}",
        f"Abstract: {doc.get('abstract') or 'not provided'}",
        f"Dockets: {dockets or 'none'}",
        f"RINs: {rins or 'none'}",
        f"URL: {doc.get('html_url')}",
    ]
    return "\n".join(lines)


def find_similar_regulations(query: str, limit: int = 5) -> str:
    return (
        f"[STUB — pgvector not configured] find_similar_regulations called with: "
        f"query={query!r}, limit={limit}"
    )