"""
Regulatory Arbitrage Scanner — main orchestrator.

Usage:
  python main.py                  # full run: scrape → analyze → dashboard → email (if High urgency)
  python main.py --scrape-only    # only scrape and store new regulations
  python main.py --analyze-only   # only analyze unprocessed regulations
  python main.py --dashboard-only # only regenerate dashboard.html
  python main.py --email-only     # only send email digest (top 5)
"""

import argparse
import sys
from dotenv import load_dotenv

load_dotenv()

from db.database import init_db, insert_regulation, get_unprocessed, get_processed
from analysis.analyzer import analyze_regulation
from db.database import update_opportunity
from delivery.dashboard import generate_dashboard
from delivery.email import send_digest


# ── Scrapers ──────────────────────────────────────────────────────────────────

def run_scrapers() -> int:
    """Run all scrapers, insert new records. Returns count of new items inserted."""
    from scrapers.federal_register import fetch as fetch_fr
    from scrapers.fda import fetch as fetch_fda
    from scrapers.sec import fetch as fetch_sec
    from scrapers.eurlex import fetch as fetch_eurlex

    all_regs = []

    print("[Scraper] Running Federal Register...")
    try:
        items = fetch_fr(days_back=7)
        print(f"[Federal Register] Found {len(items)} rules/proposed rules")
        all_regs.extend(items)
    except Exception as e:
        print(f"[Federal Register] Scraper error: {e}")

    print("[Scraper] Running FDA...")
    try:
        items = fetch_fda()
        print(f"[FDA] Found {len(items)} items")
        all_regs.extend(items)
    except Exception as e:
        print(f"[FDA] Scraper error: {e}")

    print("[Scraper] Running SEC/EDGAR...")
    try:
        items = fetch_sec(days_back=7)
        print(f"[SEC] Found {len(items)} filings")
        all_regs.extend(items)
    except Exception as e:
        print(f"[SEC] Scraper error: {e}")

    print("[Scraper] Running EUR-Lex...")
    try:
        items = fetch_eurlex(days_back=7)
        print(f"[EUR-Lex] Found {len(items)} items")
        all_regs.extend(items)
    except Exception as e:
        print(f"[EUR-Lex] Scraper error: {e}")

    inserted = 0
    for reg in all_regs:
        if not reg.get("title") or not reg.get("url"):
            continue
        if insert_regulation(reg):
            inserted += 1

    print(f"[Scraper] Inserted {inserted} new regulations (of {len(all_regs)} found).")
    return inserted


# ── Analyzer ──────────────────────────────────────────────────────────────────

def run_analyzer() -> list[dict]:
    """Analyze all unprocessed regulations. Returns list of newly processed records."""
    unprocessed = get_unprocessed()
    print(f"[Analyzer] {len(unprocessed)} regulations to analyze.")

    newly_processed = []
    for reg in unprocessed:
        print(f"[Analyzer] Analyzing: {reg['title'][:70]}...")
        opportunity = analyze_regulation(reg)
        if opportunity is None:
            print(f"[Analyzer] Skipping (analysis failed).")
            continue

        urgency_score = opportunity.get("urgency_score", 0)
        update_opportunity(reg["id"], opportunity, urgency_score)
        reg["opportunity"] = opportunity
        newly_processed.append(reg)
        print(
            f"[Analyzer] Done — urgency={opportunity.get('urgency', '?')} "
            f"score={opportunity.get('total_score', 0)}/20"
        )

    print(f"[Analyzer] Processed {len(newly_processed)} regulations.")
    return newly_processed


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Regulatory Arbitrage Scanner")
    parser.add_argument("--scrape-only", action="store_true")
    parser.add_argument("--analyze-only", action="store_true")
    parser.add_argument("--dashboard-only", action="store_true")
    parser.add_argument("--email-only", action="store_true")
    args = parser.parse_args()

    init_db()

    if args.scrape_only:
        run_scrapers()
        return

    if args.analyze_only:
        run_analyzer()
        return

    if args.dashboard_only:
        generate_dashboard()
        return

    if args.email_only:
        processed = get_processed(limit=50)
        send_digest(processed, top_n=5)
        return

    # Full run
    run_scrapers()
    newly_processed = run_analyzer()
    generate_dashboard()

    # Send email only if any newly processed records are High urgency
    high_urgency = [
        r for r in newly_processed
        if (r.get("opportunity") or {}).get("urgency") == "High"
    ]
    if high_urgency:
        print(f"[Main] {len(high_urgency)} High-urgency items found — sending email digest.")
        all_processed = get_processed(limit=50)
        send_digest(all_processed, top_n=5)
    else:
        print("[Main] No High-urgency items this run — skipping email.")

    print("[Main] Done.")


if __name__ == "__main__":
    main()