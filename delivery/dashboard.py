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


def _card(reg: dict) -> str:
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