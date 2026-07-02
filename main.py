"""
Regulatory Arbitrage Scanner — main orchestrator.

Usage:
  python main.py                  # full run: scrape → pipeline → dashboard
  python main.py --scrape-only    # only scrape and store new regulations
  python main.py --analyze-only   # only run pipeline on unprocessed regulations
  python main.py --dashboard-only # only regenerate dashboard.html
  python main.py --no-stress-test # skip adversarial moat loop (faster, cheaper)
"""

import argparse
from dotenv import load_dotenv

load_dotenv()

from db.database import init_db, insert_regulation, get_unprocessed, get_processed
from db.database import update_opportunity
from delivery.dashboard import generate_dashboard
from pipeline.run import run_pipeline, run_stress_test_only


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


# ── Pipeline ──────────────────────────────────────────────────────────────────

def run_analyzer(stress_test: bool = True, limit: int | None = None) -> list[dict]:
    """Run agentic pipeline on all unprocessed regulations."""
    return run_pipeline(stress_test=stress_test, limit=limit)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Regulatory Arbitrage Scanner")
    parser.add_argument("--scrape-only", action="store_true")
    parser.add_argument("--analyze-only", action="store_true")
    parser.add_argument("--dashboard-only", action="store_true")
    parser.add_argument("--no-stress-test", action="store_true", help="Skip adversarial moat loop")
    parser.add_argument("--stress-test-only", action="store_true", help="Stress-test already-analyzed regulations")
    parser.add_argument("--limit", type=int, default=None, help="Max regulations to analyze")
    args = parser.parse_args()

    stress_test = not args.no_stress_test

    init_db()

    if args.scrape_only:
        run_scrapers()
        return

    if args.stress_test_only:
        run_stress_test_only(limit=args.limit)
        return

    if args.analyze_only:
        run_analyzer(stress_test=stress_test, limit=args.limit)
        return

    if args.dashboard_only:
        generate_dashboard()
        return

    # Full run
    run_scrapers()
    run_analyzer(stress_test=stress_test, limit=args.limit)
    generate_dashboard()
    print("[Main] Done.")


if __name__ == "__main__":
    main()