"""Adversarial stress-tester: probes moat claims in each L3 hypothesis."""
import json
import re

import anthropic

from config import ANTHROPIC_API_KEY
from pipeline.tools.search import search
from pipeline.stress_test.graph import ClaimGraph, ClaimNode
from pipeline.stress_test.taxonomy import MOAT_TAXONOMY, VALID_MOAT_TYPES

MODEL = "claude-sonnet-4-6"


def stress_test_hypothesis(
    hypothesis: dict,
    client: anthropic.Anthropic | None = None,
    graph: ClaimGraph | None = None,
) -> dict:
    """
    Enrich one L3 hypothesis with adversarial moat analysis.
    Returns the hypothesis dict extended with moat_analysis, overall_kill_condition, claim_graph.
    """
    if client is None:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    if graph is None:
        graph = ClaimGraph()

    # 1. Extract moat claims
    claims = _extract_claims(hypothesis, client)
    print(f"[StressTest] Extracted {len(claims)} moat claim(s) for '{hypothesis.get('company', '')[:50]}'")

    # 2. Adversarially probe each claim
    moat_analysis = []
    for claim in claims:
        node_id = graph.add_claim(claim["text"], claim["moat_type"], depth=0)
        _adversarial_loop(node_id, graph, client, depth=0)
        node = graph.nodes[node_id]
        effective_decay = graph.aggregate_decay(node_id)
        moat_analysis.append({
            "moat_type": claim["moat_type"],
            "claim": claim["text"],
            "verdict": node.verdict,
            "decay_score": round(effective_decay, 2),
            "investment_window": _decay_to_window(effective_decay),
            "evidence_summary": node.evidence_summary,
        })

    # 3. Synthesize overall kill condition
    overall_kill_condition = _synthesize_kill_condition(hypothesis, moat_analysis, client)

    return {
        **hypothesis,
        "moat_analysis": moat_analysis,
        "overall_kill_condition": overall_kill_condition,
        "claim_graph": graph.serialize(),
    }


# ── Internal helpers ──────────────────────────────────────────────────────────

def _adversarial_loop(node_id: str, graph: ClaimGraph, client: anthropic.Anthropic, depth: int) -> None:
    node = graph.nodes[node_id]
    max_depth = MOAT_TAXONOMY[node.moat_type]["max_depth"]

    if depth >= max_depth:
        node.status = "judged"
        node.verdict = "inconclusive"
        node.decay_score = 0.3
        return

    # Generate falsification query
    node.status = "searching"
    query = _generate_falsification_query(node, client)
    node.search_query = query
    print(f"[StressTest]   depth={depth} query={query[:70]!r}")

    # Search with cache
    search_depth = "standard" if depth == 0 else "fast"
    evidence = graph.get_cached_evidence(query, depth)
    if evidence is None:
        evidence = search(query=query, depth=search_depth)
        graph.cache_evidence(query, depth, evidence)

    # Judge the evidence
    judgment = _judge_evidence(node, evidence, client)
    node.status = "judged"
    node.evidence_summary = judgment.get("summary", "")

    if judgment.get("strength") == "strong":
        node.verdict = "moat_challenged"
        node.decay_score = 0.8
    else:
        sub_claims = judgment.get("sub_claims", [])
        if sub_claims:
            sub_text = sub_claims[0]
            sub_id = graph.add_claim(sub_text, node.moat_type, depth + 1, parent_id=node_id)
            _adversarial_loop(sub_id, graph, client, depth + 1)
        node.verdict = "moat_holds"
        node.decay_score = 0.1


def _extract_claims(hypothesis: dict, client: anthropic.Anthropic) -> list[dict]:
    """1 Claude call → list of {text, moat_type} dicts."""
    moat_list = "\n".join(f"- {k}: {v['description']}" for k, v in MOAT_TAXONOMY.items())
    prompt = f"""You are analyzing the competitive moat of a startup hypothesis.

Hypothesis:
Company: {hypothesis.get('company', '')}
What it does: {hypothesis.get('what_it_does', '')}
Why the rule is required: {hypothesis.get('why_rule_required', '')}
Kill condition: {hypothesis.get('kill_condition', '')}

Moat types:
{moat_list}

Extract 1–3 specific, falsifiable moat claims from this hypothesis. Each claim should be a concrete statement about WHY this startup will be hard to displace.

Return ONLY a JSON array, no prose:
[
  {{"text": "Claim text here", "moat_type": "one of the moat type keys above"}},
  ...
]"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    claims = _parse_json_list(raw)

    # Filter to valid moat types only
    return [c for c in claims if c.get("moat_type") in VALID_MOAT_TYPES and c.get("text")]


def _generate_falsification_query(node: ClaimNode, client: anthropic.Anthropic) -> str:
    """1 Claude call → a Perplexity search query designed to falsify the claim."""
    templates = MOAT_TAXONOMY[node.moat_type]["search_templates"]
    threat_signals = MOAT_TAXONOMY[node.moat_type]["threat_signals"]

    prompt = f"""You are designing a search query to adversarially challenge this moat claim.

Claim: {node.claim_text}
Moat type: {node.moat_type}

Typical threat signals for this moat type:
{chr(10).join(f'- {s}' for s in threat_signals)}

Query template examples:
{chr(10).join(f'- {t}' for t in templates)}

Write ONE specific, targeted search query (max 15 words) that would find the strongest evidence that this moat is weaker than it appears. Return only the query, no explanation."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=64,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip().strip('"')


def _judge_evidence(node: ClaimNode, evidence: str, client: anthropic.Anthropic) -> dict:
    """1 Claude call → {strength, sub_claims, summary}."""
    prompt = f"""You are judging whether evidence challenges a moat claim.

Moat claim: {node.claim_text}
Moat type: {node.moat_type}

Evidence found:
{evidence[:3000]}

Evaluate:
1. Does this evidence strongly challenge the moat claim? (strong = clear threat exists; weak = moat looks intact; mixed = partial threat)
2. Are there sub-claims that need deeper investigation?
3. Summarize in 1–2 sentences.

Return ONLY JSON, no prose:
{{
  "strength": "strong | weak | mixed",
  "sub_claims": ["specific sub-claim to probe further if any, else empty array"],
  "summary": "1-2 sentence summary of what the evidence shows"
}}"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    result = _parse_json_object(raw)
    if "strength" not in result:
        result["strength"] = "mixed"
    return result


def _synthesize_kill_condition(
    hypothesis: dict,
    moat_analysis: list[dict],
    client: anthropic.Anthropic,
) -> str:
    """1 Claude call → a refined kill condition string."""
    moat_summary = "\n".join(
        f"- [{m['moat_type']}] {m['verdict']} (decay={m['decay_score']}, window={m['investment_window']}): {m['evidence_summary']}"
        for m in moat_analysis
    )
    prompt = f"""Based on the adversarial moat analysis below, write a single precise kill condition sentence for this startup hypothesis.

Company: {hypothesis.get('company', '')}
Original kill condition: {hypothesis.get('kill_condition', '')}

Moat analysis results:
{moat_summary}

The kill condition should name the single most plausible event or development that would make this opportunity disappear. Be specific — name actors, timeframes, or mechanisms where possible. Return only the sentence."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=128,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def _decay_to_window(decay: float) -> str:
    if decay >= 0.7:
        return "~6 months"
    if decay >= 0.4:
        return "~18 months"
    return "~36 months"


# ── JSON parsing helpers ──────────────────────────────────────────────────────

def _parse_json_list(raw: str) -> list:
    text = _strip_fences(raw)
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        text = match.group(0)
    try:
        result = json.loads(text)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        return []


def _parse_json_object(raw: str) -> dict:
    text = _strip_fences(raw)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    try:
        result = json.loads(text)
        return result if isinstance(result, dict) else {}
    except json.JSONDecodeError:
        return {}


def _strip_fences(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    return match.group(1) if match else text