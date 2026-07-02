"""
Dashboard generator: renders all analyzed regulations as a self-contained HTML file.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from db.database import get_processed

OUTPUT_PATH = Path(__file__).parent.parent / "dashboard.html"

URGENCY_COLORS = {
    "High": "bg-red-100 text-red-800 border-red-200",
    "Medium": "bg-yellow-100 text-yellow-800 border-yellow-200",
    "Low": "bg-green-100 text-green-800 border-green-200",
}

SCORE_BADGE = "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-100 text-indigo-800"

GAP_TYPE_COLORS = {
    "compliance_burden":     "bg-blue-100 text-blue-800",
    "permission_gap":        "bg-purple-100 text-purple-800",
    "information_asymmetry": "bg-amber-100 text-amber-800",
    "infrastructure_gap":    "bg-orange-100 text-orange-800",
}

VERDICT_COLORS = {
    "moat_holds":      "bg-green-100 text-green-800",
    "moat_challenged": "bg-red-100 text-red-800",
    "inconclusive":    "bg-gray-100 text-gray-600",
}


def _score_bar(score: int, max_score: int = 20) -> str:
    pct = min(100, int(score / max_score * 100))
    color = "bg-red-500" if pct >= 75 else "bg-yellow-500" if pct >= 50 else "bg-green-500"
    return f"""
    <div class="flex items-center gap-2">
      <div class="flex-1 bg-gray-200 rounded-full h-2">
        <div class="{color} h-2 rounded-full" style="width:{pct}%"></div>
      </div>
      <span class="text-sm font-semibold text-gray-700">{score}/20</span>
    </div>"""


def _sector_badges(sectors: list) -> str:
    badges = []
    colors = [
        "bg-blue-100 text-blue-800",
        "bg-purple-100 text-purple-800",
        "bg-pink-100 text-pink-800",
        "bg-teal-100 text-teal-800",
        "bg-orange-100 text-orange-800",
    ]
    for i, s in enumerate(sectors or []):
        c = colors[i % len(colors)]
        badges.append(
            f'<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {c}">{s}</span>'
        )
    return " ".join(badges)


def _card_legacy(reg: dict) -> str:
    opp = reg.get("opportunity") or {}
    urgency = opp.get("urgency", "Low")
    urgency_cls = URGENCY_COLORS.get(urgency, URGENCY_COLORS["Low"])
    sectors_html = _sector_badges(opp.get("sectors", []))
    total_score = opp.get("total_score", 0)
    score_bar = _score_bar(total_score)

    sub_scores = ""
    for key, label in [
        ("urgency_score", "Urgency"),
        ("market_size_score", "Market Size"),
        ("defensibility_score", "Defensibility"),
        ("regulatory_certainty_score", "Reg. Certainty"),
    ]:
        val = opp.get(key, 0)
        sub_scores += f'<span class="{SCORE_BADGE}">{label}: {val}/5</span> '

    source_link = (
        f'<a href="{reg["url"]}" target="_blank" rel="noopener" '
        f'class="text-indigo-600 hover:text-indigo-800 text-sm font-medium underline">'
        f'View Source →</a>'
    ) if reg.get("url") else ""

    return f"""
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
      <div class="flex items-start justify-between gap-4 mb-3">
        <div class="flex-1">
          <div class="flex items-center gap-2 mb-1">
            <span class="text-xs font-medium text-gray-400 uppercase tracking-wide">{reg.get('source', '')}</span>
            <span class="text-xs text-gray-400">·</span>
            <span class="text-xs text-gray-400">{reg.get('published_at', '')}</span>
          </div>
          <h2 class="text-base font-semibold text-gray-900 leading-snug">{reg.get('title', '')}</h2>
        </div>
        <span class="shrink-0 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border {urgency_cls}">
          {urgency}
        </span>
      </div>

      <div class="mb-3 flex flex-wrap gap-1">{sectors_html}</div>

      <p class="text-sm text-gray-700 mb-3">
        <span class="font-medium text-gray-900">Summary:</span> {opp.get('rule_summary', '')}
      </p>

      <div class="bg-indigo-50 border border-indigo-100 rounded-lg p-3 mb-3">
        <p class="text-sm font-medium text-indigo-900 mb-1">Opportunity Hypothesis</p>
        <p class="text-sm text-indigo-800">{opp.get('opportunity_hypothesis', '')}</p>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3 text-sm">
        <div class="bg-gray-50 rounded-lg p-3">
          <p class="font-medium text-gray-700 mb-1">Who Wins</p>
          <p class="text-gray-600">{opp.get('who_wins', '')}</p>
        </div>
        <div class="bg-gray-50 rounded-lg p-3">
          <p class="font-medium text-gray-700 mb-1">Historical Precedent</p>
          <p class="text-gray-600">{opp.get('historical_precedent', '')}</p>
        </div>
      </div>

      <div class="bg-amber-50 border border-amber-100 rounded-lg p-3 mb-4">
        <p class="text-sm font-medium text-amber-900 mb-1">Compliance Product Opportunity</p>
        <p class="text-sm text-amber-800">{opp.get('compliance_product_opportunity', '')}</p>
      </div>

      <div class="mb-3">
        <p class="text-xs font-medium text-gray-500 mb-1">URGENCY REASON</p>
        <p class="text-sm text-gray-600 italic">{opp.get('urgency_reason', '')}</p>
      </div>

      <div class="border-t border-gray-100 pt-3">
        <div class="mb-2">
          <p class="text-xs font-medium text-gray-500 mb-1">TOTAL OPPORTUNITY SCORE</p>
          {score_bar}
        </div>
        <div class="flex flex-wrap gap-1 mb-3">{sub_scores}</div>
        {source_link}
      </div>
    </div>"""


def _badge(text: str, cls: str) -> str:
    return f'<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {cls}">{text}</span>'


def _moat_row(m: dict) -> str:
    verdict_cls = VERDICT_COLORS.get(m.get("verdict", ""), "bg-gray-100 text-gray-600")
    verdict_label = m.get("verdict", "").replace("_", " ")
    decay = m.get("decay_score", 0)
    window = m.get("investment_window", "")
    moat_type = m.get("moat_type", "").replace("_", " ")
    summary = m.get("evidence_summary", "")
    return f"""
      <div class="flex flex-wrap items-start gap-2 py-1.5 border-b border-gray-100 last:border-0 text-xs">
        <span class="font-medium text-gray-500 w-36 shrink-0">{moat_type}</span>
        {_badge(verdict_label, verdict_cls)}
        <span class="text-gray-400">decay {decay}</span>
        <span class="text-gray-400">{window}</span>
        {f'<span class="text-gray-500 italic">{summary}</span>' if summary else ''}
      </div>"""


def _hypothesis_block(hyp: dict, index: int, total: int) -> str:
    moat_rows = "".join(_moat_row(m) for m in hyp.get("moat_analysis", []))
    moat_section = f"""
      <div class="mt-2 border border-gray-100 rounded-lg p-2 bg-gray-50">
        <p class="text-xs font-medium text-gray-500 mb-1">Moat Analysis</p>
        {moat_rows if moat_rows else '<p class="text-xs text-gray-400 italic">No moat data</p>'}
      </div>""" if hyp.get("moat_analysis") else ""

    kill = hyp.get("overall_kill_condition") or hyp.get("kill_condition", "")

    return f"""
    <div class="mt-4 border-t border-dashed border-gray-200 pt-4">
      <p class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
        Hypothesis {index} of {total}
      </p>
      <p class="text-sm font-semibold text-gray-900 mb-1">{hyp.get('company', '')}</p>
      <p class="text-sm text-gray-600 mb-1">{hyp.get('what_it_does', '')}</p>
      <p class="text-xs text-gray-500 mb-1">
        <span class="font-medium">First 100 customers:</span> {hyp.get('first_100_customers', '')}
      </p>
      {moat_section}
      {f'<p class="text-xs text-red-700 mt-2"><span class="font-medium">Kill condition:</span> {kill}</p>' if kill else ''}
    </div>"""


def _card_new(reg: dict) -> str:
    opp = reg.get("opportunity") or {}
    urgency = opp.get("urgency", "Low")
    urgency_cls = URGENCY_COLORS.get(urgency, URGENCY_COLORS["Low"])

    # Sectors + jurisdictions
    sector_badges = _sector_badges(opp.get("sectors", []))
    jurisdiction_badges = " ".join(
        _badge(j, "bg-gray-100 text-gray-700") for j in (opp.get("jurisdictions") or [])
    )

    # Layer 2 — The Gap
    l2 = opp.get("layer2") or {}
    gap_type = l2.get("gap_type", "")
    gap_type_cls = GAP_TYPE_COLORS.get(gap_type, "bg-gray-100 text-gray-600")
    gap_type_label = gap_type.replace("_", " ")

    # Layer 1 — What Changed (collapsible)
    l1 = opp.get("layer1") or {}
    permitted = ", ".join(l1.get("permitted") or []) or "—"
    prohibited = ", ".join(l1.get("prohibited") or []) or "—"
    mandated = ", ".join(l1.get("mandated") or []) or "—"
    effective = l1.get("effective_date", "unspecified")

    # International precedent (collapsible)
    precedent = opp.get("international_precedent")
    precedent_section = ""
    if precedent:
        precedent_section = f"""
      <details class="mt-2">
        <summary class="text-sm font-medium text-gray-600 cursor-pointer select-none hover:text-gray-900">
          International Precedent
        </summary>
        <p class="mt-1 text-sm text-gray-600 italic pl-4">{precedent}</p>
      </details>"""

    # Hypotheses
    hypotheses = opp.get("layer3") or []
    hyp_blocks = "".join(
        _hypothesis_block(h, i + 1, len(hypotheses))
        for i, h in enumerate(hypotheses)
    )

    # Footer
    source_link = (
        f'<a href="{reg["url"]}" target="_blank" rel="noopener" '
        f'class="text-indigo-600 hover:text-indigo-800 text-sm font-medium underline">'
        f'View Source →</a>'
    ) if reg.get("url") else ""
    tool_calls = opp.get("tool_calls_made", 0)

    return f"""
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">

      <!-- Header -->
      <div class="flex items-start justify-between gap-4 mb-3">
        <div class="flex-1">
          <div class="flex items-center gap-2 mb-1">
            <span class="text-xs font-medium text-gray-400 uppercase tracking-wide">{reg.get('source', '')}</span>
            <span class="text-xs text-gray-400">·</span>
            <span class="text-xs text-gray-400">{reg.get('published_at', '')}</span>
          </div>
          <h2 class="text-base font-semibold text-gray-900 leading-snug">{reg.get('title', '')}</h2>
        </div>
        <span class="shrink-0 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border {urgency_cls}">
          {urgency}
        </span>
      </div>

      <!-- Sectors + Jurisdictions -->
      <div class="flex flex-wrap gap-1 mb-4">
        {sector_badges}
        {jurisdiction_badges}
      </div>

      <!-- The Gap -->
      <div class="bg-indigo-50 border border-indigo-200 rounded-lg p-4 mb-4">
        <p class="text-xs font-semibold text-indigo-400 uppercase tracking-wide mb-1">The Gap</p>
        <p class="text-sm font-medium text-indigo-900 mb-2">{l2.get('gap', '')}</p>
        <div class="flex flex-wrap gap-2 text-xs text-indigo-700">
          {_badge(gap_type_label, gap_type_cls)}
          <span class="text-indigo-600"><span class="font-medium">Incumbents:</span> {l2.get('incumbent_weakness', '')}</span>
        </div>
      </div>

      <!-- What Changed -->
      <details class="mb-3">
        <summary class="text-sm font-medium text-gray-600 cursor-pointer select-none hover:text-gray-900">
          What Changed (Layer 1)
        </summary>
        <div class="mt-2 pl-4 text-sm text-gray-600 space-y-1">
          <p><span class="font-medium text-green-700">Permitted:</span> {permitted}</p>
          <p><span class="font-medium text-red-700">Prohibited:</span> {prohibited}</p>
          <p><span class="font-medium text-blue-700">Mandated:</span> {mandated}</p>
          <p><span class="font-medium text-gray-700">Effective:</span> {effective}</p>
        </div>
      </details>

      <!-- International Precedent -->
      {precedent_section}

      <!-- Hypotheses -->
      {hyp_blocks}

      <!-- Footer -->
      <div class="mt-4 pt-3 border-t border-gray-100 flex items-center gap-4 text-xs text-gray-400">
        {source_link}
        <span>Tool calls: {tool_calls}</span>
        <span class="ml-auto">{urgency} urgency</span>
      </div>
    </div>"""


def _card(reg: dict) -> str:
    opp = reg.get("opportunity") or {}
    if opp.get("layer2"):
        return _card_new(reg)
    return _card_legacy(reg)


def generate_dashboard(limit: int = 100):
    regulations = get_processed(limit=limit)
    generated_at = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

    if regulations:
        cards_html = "\n".join(_card(r) for r in regulations)
        empty_state = ""
    else:
        cards_html = ""
        empty_state = """
        <div class="text-center py-20 text-gray-400">
          <p class="text-4xl mb-3">📋</p>
          <p class="text-lg font-medium">No briefs yet</p>
          <p class="text-sm">Run the scraper and analyzer to generate regulatory briefs.</p>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Regulatory Arbitrage Scanner</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" />
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
    .card-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(540px, 1fr)); gap: 1.5rem; }}
    @media (max-width: 600px) {{ .card-grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body class="bg-gray-50 min-h-screen">
  <header class="bg-white border-b border-gray-200 sticky top-0 z-10">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
      <div>
        <h1 class="text-xl font-bold text-gray-900">Regulatory Arbitrage Scanner</h1>
        <p class="text-sm text-gray-500">New law → new market briefs</p>
      </div>
      <div class="text-right">
        <p class="text-xs text-gray-400">Generated</p>
        <p class="text-sm font-medium text-gray-600">{generated_at}</p>
      </div>
    </div>
  </header>

  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <div class="mb-6 flex items-center justify-between">
      <p class="text-sm text-gray-500">{len(regulations)} brief{"s" if len(regulations) != 1 else ""} · sorted by opportunity score</p>
    </div>

    {empty_state}
    <div class="card-grid">
      {cards_html}
    </div>
  </main>

  <footer class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 text-center text-xs text-gray-400">
    Regulatory Arbitrage Scanner · Powered by Claude · {generated_at}
  </footer>
</body>
</html>"""

    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"[Dashboard] Generated {OUTPUT_PATH} with {len(regulations)} briefs.")
    return str(OUTPUT_PATH)


if __name__ == "__main__":
    generate_dashboard()