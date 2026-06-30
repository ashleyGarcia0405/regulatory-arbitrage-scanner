"""
Analyzer: sends regulation text to Claude and parses the opportunity JSON.
"""

import json
import os
import re
from dotenv import load_dotenv
import anthropic

from analysis.prompts import OPPORTUNITY_PROMPT

load_dotenv()

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024


def analyze_regulation(reg: dict) -> dict | None:
    """
    Takes a regulation dict (from DB row), calls Claude, returns enriched dict.
    Returns None on failure.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = OPPORTUNITY_PROMPT.format(
        title=reg.get("title", ""),
        source=reg.get("source", ""),
        published_at=reg.get("published_at", ""),
        text=(reg.get("full_text") or "")[:8000],
    )

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        print(f"[Analyzer] Claude API error for '{reg.get('title', '')[:60]}': {e}")
        return None

    raw = message.content[0].text.strip()

    # Extract JSON — handle cases where Claude wraps it in markdown fences
    json_str = raw
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fence_match:
        json_str = fence_match.group(1)
    else:
        # Try to find the outermost { ... }
        brace_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if brace_match:
            json_str = brace_match.group(0)

    try:
        opportunity = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"[Analyzer] JSON parse error for '{reg.get('title', '')[:60]}': {e}")
        print(f"[Analyzer] Raw response: {raw[:200]}")
        return None

    # Compute total_score from the four integer score fields
    score_keys = [
        "urgency_score",
        "market_size_score",
        "defensibility_score",
        "regulatory_certainty_score",
    ]
    total_score = sum(int(opportunity.get(k, 0)) for k in score_keys)
    opportunity["total_score"] = total_score

    return opportunity


if __name__ == "__main__":
    # Quick smoke test with a dummy regulation
    test_reg = {
        "id": 0,
        "source": "Federal Register",
        "title": "Final Rule: Mandatory Safety Standards for Lithium-Ion Batteries in Consumer Products",
        "published_at": "2026-04-10",
        "full_text": (
            "This final rule establishes mandatory safety standards for lithium-ion batteries "
            "used in consumer products, requiring manufacturers to comply with UL 9540 and "
            "IEC 62619 standards by January 2027. Products not meeting these standards will "
            "be banned from import and sale in the United States."
        ),
    }

    result = analyze_regulation(test_reg)
    if result:
        print(json.dumps(result, indent=2))
    else:
        print("[Analyzer] Test failed — check API key and connectivity.")