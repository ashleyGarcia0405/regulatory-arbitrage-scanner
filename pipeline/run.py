"""Orchestrator: unprocessed regulations → agent → stress test → DB."""
import json
from pathlib import Path

import anthropic

from config import ANTHROPIC_API_KEY
from db.database import get_unprocessed, get_processed, update_opportunity
from pipeline import agent
from pipeline.stress_test.runner import stress_test_hypothesis
from pipeline.stress_test.graph import ClaimGraph

OUTPUT_DIR = Path(__file__).parent.parent / "output"

_URGENCY_SCORE = {"High": 5, "Medium": 3, "Low": 1}


def run_pipeline(
    regulations: list[dict] | None = None,
    stress_test: bool = True,
    limit: int | None = None,
) -> list[dict]:
    """
    Analyze regulations and persist results.

    Args:
        regulations: list of regulation dicts. If None, fetches all unprocessed rows from DB.
        stress_test: whether to run the adversarial moat loop on each L3 hypothesis.

    Returns:
        List of analysis dicts that were successfully processed.
    """
    if regulations is None:
        regulations = get_unprocessed()

    if limit is not None:
        regulations = regulations[:limit]

    if not regulations:
        print("[Pipeline] No regulations to process.")
        return []

    OUTPUT_DIR.mkdir(exist_ok=True)

    # One shared client for all stress-test calls (avoids re-authing per hypothesis)
    st_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if stress_test else None

    results = []

    for reg in regulations:
        reg_id = reg.get("id", "unknown")
        title = reg.get("title", "")[:70]
        print(f"\n[Pipeline] Processing reg {reg_id}: {title!r}")

        # ── Agentic analysis ──────────────────────────────────────────────
        analysis = agent.analyze(reg)
        if analysis is None:
            print(f"[Pipeline] Skipping reg {reg_id} — agent returned None")
            continue

        # ── Adversarial stress test ───────────────────────────────────────
        if stress_test and analysis.get("layer3"):
            stressed_hypotheses = []
            for i, hyp in enumerate(analysis["layer3"]):
                print(f"[Pipeline]   Stress-testing hypothesis {i + 1}/{len(analysis['layer3'])}: {hyp.get('company', '')[:50]}")
                graph = ClaimGraph()
                stressed = stress_test_hypothesis(hyp, client=st_client, graph=graph)
                stressed_hypotheses.append(stressed)
            analysis["layer3"] = stressed_hypotheses

        # ── Persist ───────────────────────────────────────────────────────
        urgency = analysis.get("urgency", "Low")
        urgency_score = _URGENCY_SCORE.get(urgency, 1)

        if isinstance(reg_id, int):
            update_opportunity(reg_id, analysis, urgency_score)

        # Write debug JSON
        out_path = OUTPUT_DIR / f"{reg_id}.json"
        out_path.write_text(json.dumps(analysis, indent=2))
        print(f"[Pipeline] Saved → {out_path}")

        results.append(analysis)

    print(f"\n[Pipeline] Done. Processed {len(results)}/{len(regulations)} regulation(s).")
    return results


def run_stress_test_only(limit: int | None = None) -> list[dict]:
    """
    Re-run the adversarial stress test on already-analyzed regulations.
    Skips any that already have moat_analysis on their first L3 hypothesis.
    """
    rows = get_processed(limit=1000)

    # Only rows with L3 hypotheses that haven't been stress-tested yet
    pending = [
        r for r in rows
        if (r.get("opportunity") or {}).get("layer3")
        and not (r["opportunity"]["layer3"][0]).get("moat_analysis")
    ]

    if limit is not None:
        pending = pending[:limit]

    if not pending:
        print("[StressTest] No processed regulations need stress-testing.")
        return []

    print(f"[StressTest] Running stress test on {len(pending)} regulation(s).")
    OUTPUT_DIR.mkdir(exist_ok=True)
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    results = []

    for row in pending:
        reg_id = row.get("id", "unknown")
        title = row.get("title", "")[:70]
        analysis = row["opportunity"]
        print(f"\n[StressTest] Reg {reg_id}: {title!r}")

        stressed_hypotheses = []
        for i, hyp in enumerate(analysis["layer3"]):
            print(f"[StressTest]   Hypothesis {i + 1}/{len(analysis['layer3'])}: {hyp.get('company', '')[:50]}")
            graph = ClaimGraph()
            stressed = stress_test_hypothesis(hyp, client=client, graph=graph)
            stressed_hypotheses.append(stressed)
        analysis["layer3"] = stressed_hypotheses

        urgency_score = _URGENCY_SCORE.get(analysis.get("urgency", "Low"), 1)
        if isinstance(reg_id, int):
            update_opportunity(reg_id, analysis, urgency_score)

        out_path = OUTPUT_DIR / f"{reg_id}.json"
        out_path.write_text(json.dumps(analysis, indent=2))
        print(f"[StressTest] Saved → {out_path}")
        results.append(analysis)

    print(f"\n[StressTest] Done. Stress-tested {len(results)}/{len(pending)} regulation(s).")
    return results