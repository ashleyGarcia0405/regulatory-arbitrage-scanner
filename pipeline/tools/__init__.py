"""Tool schemas and dispatcher for the agentic analysis loop."""
from pipeline.tools.search import search
from pipeline.tools.regulations import fetch_regulation_history, find_similar_regulations

TOOL_DEFINITIONS = [
    {
        "name": "search_web",
        "description": (
            "Search the web for information about regulations, market structure, "
            "and international precedents. Use depth='deep' for thorough research "
            "and 'fast' for quick fact checks."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query.",
                },
                "depth": {
                    "type": "string",
                    "enum": ["fast", "standard", "deep"],
                    "description": "Search depth. 'deep' is most thorough but slower.",
                },
                "reason": {
                    "type": "string",
                    "description": "Why you are running this search (for audit logging).",
                },
                "from_date": {
                    "type": "string",
                    "description": "ISO date (YYYY-MM-DD) to filter results to after this date. Optional.",
                },
            },
            "required": ["query", "depth", "reason"],
        },
    },
    {
        "name": "fetch_regulation_history",
        "description": (
            "Fetch full metadata for a Federal Register document by its document number "
            "(e.g. '2024-01234'). Returns publication date, agencies, action text, abstract, "
            "docket IDs, and RINs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "document_number": {
                    "type": "string",
                    "description": "The Federal Register document number (e.g. '2024-01234').",
                },
            },
            "required": ["document_number"],
        },
    },
    {
        "name": "find_similar_regulations",
        "description": (
            "Search the database of previously analyzed regulations for ones similar to a "
            "given query using vector similarity. Use this first to check if we've already "
            "analyzed something like this regulation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language description of what to search for.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return. Defaults to 5.",
                },
            },
            "required": ["query"],
        },
    },
]


def dispatch_tool(name: str, inputs: dict) -> str:
    if name == "search_web":
        return search(
            query=inputs["query"],
            depth=inputs.get("depth", "standard"),
            from_date=inputs.get("from_date"),
        )
    if name == "fetch_regulation_history":
        return fetch_regulation_history(inputs["document_number"])
    if name == "find_similar_regulations":
        return find_similar_regulations(
            query=inputs["query"],
            limit=inputs.get("limit", 5),
        )
    return f"[ERROR] Unknown tool: {name!r}"