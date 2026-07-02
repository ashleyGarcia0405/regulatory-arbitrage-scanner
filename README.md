# Regulatory Arbitrage Scanner

Monitors regulatory filings from US and EU government sources and uses an agentic Claude loop to analyze each one for startup opportunity signals. Claude drives its own research using tools, produces a three-layer structured analysis, and adversarially stress-tests each opportunity hypothesis before surfacing results in a local HTML dashboard.

**Pipeline:** scrape → deduplicate → agentic analysis (Claude + tools) → adversarial stress test → dashboard

---

## How it works

1. **Scrapers** pull new regulations from four sources (Federal Register, FDA, SEC, EUR-Lex)
2. Each regulation is stored in SQLite with a SHA-256 dedup hash on `url:title`
3. **Agentic loop** (`pipeline/agent.py`) gives Claude three tools and lets it decide what to research before forming its analysis — up to 8 tool rounds, then a forced final response
4. Claude produces a **three-layer analysis**: what changed (L1) → the structural market gap (L2) → specific startup hypotheses (L3)
5. **Adversarial stress-tester** (`pipeline/stress_test/`) extracts the moat claims inside each L3 hypothesis and probes them with Perplexity searches, returning a verdict, decay score, and investment window per claim
6. Results are persisted to SQLite and written to `output/{id}.json` for debugging
7. **Dashboard** generates a self-contained `dashboard.html` with collapsible card layouts for the new structure

---

## The three-layer analysis

| Layer | What it produces |
|---|---|
| **L1 — What Changed** | Specific permissions, prohibitions, and mandates the rule creates, plus effective date |
| **L2 — The Gap** | The structural market gap the rule opens (gap type, one-sentence description, why incumbents can't capture it) |
| **L3 — Hypotheses** | 2–4 startup ideas that only work because this rule exists, each with first 100 customers and kill condition |

### Research protocol

Claude calls tools in this order before forming its analysis:

1. `find_similar_regulations` — check if we've analyzed something like this before
2. `search_web(depth="deep")` — international precedents (UK / EU / SG / AU)
3. `search_web(depth="standard")` — incumbent market structure
4. `fetch_regulation_history` — Federal Register metadata (only if document number is available and relevant)

### Adversarial stress test

For each L3 hypothesis, the stress-tester:
- Extracts 1–3 moat claims (data network effect, switching costs, distribution, regulatory, tech differentiation, brand/community)
- Generates a targeted falsification query per claim
- Searches Perplexity for counter-evidence
- Judges the evidence → `moat_holds | moat_challenged | inconclusive`
- Computes a decay score (0–1) and investment window (~6 / ~18 / ~36 months)
- Synthesizes a refined kill condition across all claims

---

## Setup

### 1. Install dependencies

Requires Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
ANTHROPIC_API_KEY=sk-ant-...       # required — used for all Claude calls

PERPLEXITY_API_KEY=pplx-...        # optional but recommended — enables real web search
                                   # without it, search calls return [STUB] strings
                                   # and the analysis still runs

SUPABASE_URL=https://...           # (SQLite used until set)
SUPABASE_SERVICE_KEY=...           
```

---

## Running

### Full pipeline (scrape → analyze → stress test → dashboard)

```bash
python main.py
```

### Skip the adversarial stress test (faster and cheaper — good for initial testing)

```bash
python main.py --no-stress-test
```

### Individual stages

```bash
python main.py --scrape-only      # fetch and store new regulations
python main.py --analyze-only     # run pipeline on unprocessed regulations
python main.py --dashboard-only   # regenerate dashboard.html from DB
```

`--no-stress-test` works with `--analyze-only`:

```bash
python main.py --analyze-only --no-stress-test
```

### Run stress test separately on already-analyzed regulations

```bash
python main.py --stress-test-only
```

Fetches all processed regulations that have L3 hypotheses but no moat analysis yet, and runs the adversarial stress tester on them. Safe to re-run — already stress-tested regulations are skipped automatically.

Combine with `--limit` to process in batches:

```bash
python main.py --analyze-only --no-stress-test --limit 10   # analyze 10 fast
python main.py --stress-test-only --limit 10                # stress-test those 10
python main.py --dashboard-only                             # regenerate dashboard
```

### Limit how many regulations are processed

```bash
python main.py --analyze-only --limit 5       # analyze 5 unprocessed regulations
python main.py --stress-test-only --limit 5   # stress-test 5 pending regulations
```

`--limit` applies after filtering, so `--stress-test-only --limit 5` means "stress-test up to 5 regulations that still need it" — not "look at 5 rows and stress-test whatever's in there."

### Continuous scheduler

```bash
python scheduler.py
```

Runs scrape + analyze every 12 hours, regenerates the dashboard every 6 hours, and runs an immediate pass on startup.

### Smoke-test individual scrapers

```bash
python -m scrapers.federal_register
python -m scrapers.fda
python -m scrapers.sec
python -m scrapers.eurlex
```

### Initialize the database manually

```bash
python -m db.database
```

---

## Project structure

```
.
├── main.py                        # CLI entrypoint and pipeline orchestrator
├── scheduler.py                   # APScheduler daemon (blocking)
├── config.py                      # Reads env vars via python-dotenv
├── requirements.txt
│
├── pipeline/
│   ├── agent.py                   # Agentic loop: Claude + tools → L1/L2/L3 JSON
│   ├── run.py                     # Orchestrator: unprocessed regs → agent → stress test → DB
│   └── tools/
│       ├── __init__.py            # TOOL_DEFINITIONS + dispatch_tool()
│       ├── search.py              # Perplexity web search (stub when key unset)
│       └── regulations.py        # Federal Register history (live) + pgvector stub
│   └── stress_test/
│       ├── taxonomy.py            # 6 moat types with falsification playbooks
│       ├── graph.py               # ClaimGraph: dedup, evidence cache, decay aggregation
│       └── runner.py              # Adversarial loop per hypothesis
│
├── scrapers/
│   ├── federal_register.py        # REST API — Rules and Proposed Rules (last 7 days)
│   ├── fda.py                     # RSS feeds — press releases and recalls
│   ├── sec.py                     # RSS feeds — proposed rules + press releases
│   └── eurlex.py                  # SPARQL against EU Publications Office Cellar endpoint
│
├── analysis/                      # Deprecated — kept for reference
│   ├── analyzer.py
│   └── prompts.py
│
├── db/
│   ├── schema.sql                 # SQLite schema
│   ├── database.py                # init, insert, get_unprocessed, update_opportunity, get_processed
│   └── regulations.db             # created on first run
│
├── delivery/
│   └── dashboard.py               # Generates dashboard.html (Tailwind CSS, no build step)
│
└── output/                        # Per-regulation debug JSON, created on first run
    └── {reg_id}.json
```

---

## Database schema

Single table: `regulations`

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | autoincrement |
| `source` | TEXT | e.g. `Federal Register`, `SEC` |
| `title` | TEXT | regulation title |
| `url` | TEXT UNIQUE | source URL |
| `published_at` | TEXT | ISO date string |
| `full_text` | TEXT | abstract/summary, truncated to 8000 chars on insert |
| `hash` | TEXT UNIQUE | SHA-256 of `url:title` — dedup key |
| `processed_at` | TEXT | ISO timestamp set after analysis |
| `opportunity_json` | TEXT | full L1/L2/L3 analysis JSON from Claude |
| `urgency_score` | INTEGER | 5 = High, 3 = Medium, 1 = Low — used for dashboard sort order |

`get_processed()` parses `opportunity_json` into an `opportunity` dict on each row.

---

## Models used

| Component | Model | Why |
|---|---|---|
| Agentic analysis loop | `claude-opus-4-8` | Main analysis — needs strongest reasoning for L1/L2/L3 |
| Stress test: claim extraction | `claude-sonnet-4-6` | Structured extraction — cheaper, fast |
| Stress test: falsification query | `claude-sonnet-4-6` | Short output, low latency |
| Stress test: evidence judging | `claude-sonnet-4-6` | Structured judgment — cheaper, fast |
| Stress test: kill condition synthesis | `claude-sonnet-4-6` | Short synthesis — cheaper, fast |

A single regulation with 3 hypotheses and 2 moat claims each makes approximately: 1 Opus call (agentic loop, up to 8 rounds) + ~21 Sonnet calls (stress test).

---

## What's stubbed vs. live

| Component | Status |
|---|---|
| Federal Register, FDA, SEC, EUR-Lex scrapers | Live |
| `fetch_regulation_history` (FR API) | Live |
| `search_web` (Perplexity) | Stub → real when `PERPLEXITY_API_KEY` is set |
| `find_similar_regulations` (pgvector) | Stub → real when Supabase is configured |
| SQLite storage | Live |
| HTML dashboard | Live |

Analysis still runs and produces useful output without a Perplexity key — the search stub returns clearly labeled `[STUB]` strings that Claude reasons around.

---

## Scraper notes

### Federal Register
- REST API at `federalregister.gov/api/v1/documents.json`
- The API's `conditions[type][]` filter silently returns zero results, so all types are fetched and filtered client-side to `Rule` and `Proposed Rule`
- Paginates up to 5 pages (100 results/page), scoped to the last 7 days

### FDA
- Parses two RSS feeds: press releases and recalls/safety alerts
- No API key required

### SEC
- Two RSS feeds: `rss/rules/proposed.xml` and `news/pressreleases.rss` (filtered by rule-related keywords)
- Sets a `User-Agent` header — EDGAR blocks requests without one

### EUR-Lex
- Queries the EU Publications Office **Cellar SPARQL endpoint** — the EUR-Lex web UI is behind AWS WAF and can't be scraped directly
- 14-day lookback window because the Cellar index lags EUR-Lex publication dates by ~10–14 days
- Filters to four CDM types: `regulation`, `directive`, `decision`, `recommendation`