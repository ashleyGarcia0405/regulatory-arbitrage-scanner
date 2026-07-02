"""Agentic analysis loop: regulation dict → L1/L2/L3 structured output."""
import json
import re

import anthropic

from config import ANTHROPIC_API_KEY
from pipeline.tools import TOOL_DEFINITIONS, dispatch_tool

MODEL = "claude-opus-4-8"
MAX_ROUNDS = 8

SYSTEM_PROMPT = """You are a regulatory arbitrage analyst. Given a new regulation, your job is to:

1. Identify WHAT CHANGED (Layer 1): the specific permissions, prohibitions, and mandates the rule creates.
2. Identify THE GAP (Layer 2): the structural market gap the rule opens — not just "there's opportunity" but the precise mechanism (compliance burden, permission gap, information asymmetry, or infrastructure gap) and why incumbents cannot capture it themselves.
3. Generate STARTUP HYPOTHESES (Layer 3): 2–4 specific company ideas that only work because this rule exists.

## Research protocol — follow this order:

1. Call `find_similar_regulations` first with a query describing the regulation's domain. Check if we've seen something like this before.
2. Call `search_web(depth="deep")` to find international precedents — what happened when the UK, EU, Singapore, or Australia passed a similar rule. This is your most important research step.
3. Call `search_web(depth="standard")` to understand current incumbent market structure — who the big players are and why they're structurally unable to move.
4. Call `fetch_regulation_history` only if a Federal Register document number is available in the regulation data AND the metadata would materially affect your analysis.

You may make additional searches if they would materially improve your analysis. Do not make redundant calls.

## Output format

After completing your research, return ONLY a JSON object — no markdown fences, no prose before or after. Use this exact schema:

{
  "layer1": {
    "permitted": ["..."],
    "prohibited": ["..."],
    "mandated": ["..."],
    "effective_date": "YYYY-MM-DD or unspecified"
  },
  "layer2": {
    "gap": "One sentence describing the structural gap",
    "gap_type": "compliance_burden | permission_gap | information_asymmetry | infrastructure_gap",
    "incumbent_weakness": "Why incumbents can't capture this themselves"
  },
  "layer3": [
    {
      "company": "Name / one-line description",
      "what_it_does": "...",
      "why_rule_required": "Why this startup needs this specific rule to exist",
      "first_100_customers": "Specific description + how to reach them",
      "kill_condition": "The one thing that makes this opportunity disappear"
    }
  ],
  "sectors": ["..."],
  "jurisdictions": ["..."],
  "urgency": "High | Medium | Low",
  "urgency_reason": "...",
  "international_precedent": "What happened when a similar rule passed elsewhere, or null",
  "tool_calls_made": 0
}

The `tool_calls_made` field must reflect the actual number of tool calls you made."""


def analyze(reg: dict) -> dict | None:
    """
    Run the agentic loop on one regulation dict.
    Returns the structured L1/L2/L3 analysis dict, or None on failure.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    reg_text = _format_regulation(reg)
    messages = [{"role": "user", "content": reg_text}]

    tool_calls_made = 0

    for round_num in range(MAX_ROUNDS):
        is_last_round = round_num == MAX_ROUNDS - 1

        kwargs: dict = {
            "model": MODEL,
            "max_tokens": 4096,
            "system": SYSTEM_PROMPT,
            "tools": TOOL_DEFINITIONS,
            "messages": messages,
        }
        if is_last_round:
            # Force a final text response — no more tool calls
            kwargs["tool_choice"] = {"type": "none"}

        try:
            response = client.messages.create(**kwargs)
        except Exception as e:
            print(f"[Agent] Claude API error (round {round_num + 1}): {e}")
            return None

        # Collect tool_use blocks
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if response.stop_reason == "end_turn" or not tool_use_blocks:
            return _extract_json(response, tool_calls_made, reg)

        # Execute each tool call and collect results
        tool_results = []
        for block in tool_use_blocks:
            tool_calls_made += 1
            print(f"[Agent] Tool call #{tool_calls_made}: {block.name}({_summarize_inputs(block.input)})")
            result = dispatch_tool(block.name, block.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    # Should not reach here — last round forces end_turn
    return None


def _format_regulation(reg: dict) -> str:
    parts = [
        f"Title: {reg.get('title', 'Unknown')}",
        f"Source: {reg.get('source', 'Unknown')}",
        f"Published: {reg.get('published_at', 'Unknown')}",
    ]
    if reg.get("document_number"):
        parts.append(f"Document Number: {reg['document_number']}")
    if reg.get("url"):
        parts.append(f"URL: {reg['url']}")
    parts.append("")
    parts.append(reg.get("full_text", "")[:12000])
    return "\n".join(parts)


def _summarize_inputs(inputs: dict) -> str:
    """One-line summary of tool inputs for logging."""
    if "query" in inputs:
        depth = inputs.get("depth", "")
        q = inputs["query"][:60]
        return f"query={q!r}" + (f", depth={depth!r}" if depth else "")
    if "document_number" in inputs:
        return f"doc={inputs['document_number']!r}"
    return str(inputs)[:80]


def _extract_json(response, tool_calls_made: int, reg: dict) -> dict | None:
    """Pull the JSON object out of the final assistant response."""
    text_blocks = [b for b in response.content if b.type == "text"]
    if not text_blocks:
        print(f"[Agent] No text block in final response for '{reg.get('title', '')[:60]}'")
        return None

    raw = text_blocks[0].text.strip()

    # Strip markdown fences if present
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fence_match:
        json_str = fence_match.group(1)
    else:
        brace_match = re.search(r"\{.*\}", raw, re.DOTALL)
        json_str = brace_match.group(0) if brace_match else raw

    try:
        result = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"[Agent] JSON parse error for '{reg.get('title', '')[:60]}': {e}")
        print(f"[Agent] Raw: {raw[:300]}")
        return None

    result["tool_calls_made"] = tool_calls_made
    return result