import sqlite3
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "regulations.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print(f"[DB] Initialized database at {DB_PATH}")


def make_hash(url: str, title: str) -> str:
    return hashlib.sha256(f"{url}:{title}".encode()).hexdigest()


def insert_regulation(reg: dict) -> bool:
    """Insert a regulation. Returns True if inserted, False if duplicate."""
    url = reg.get("url", "")
    title = reg.get("title", "")
    h = make_hash(url, title)

    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO regulations (source, title, url, published_at, full_text, hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                reg.get("source", ""),
                title,
                url,
                reg.get("published_at", ""),
                (reg.get("full_text", "") or "")[:8000],
                h,
            ),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_unprocessed() -> list[dict]:
    """Return all regulations that haven't been analyzed yet."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM regulations WHERE processed_at IS NULL ORDER BY id ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_opportunity(reg_id: int, opportunity: dict, urgency_score: int):
    """Store analysis results back into the DB."""
    conn = get_connection()
    conn.execute(
        """
        UPDATE regulations
        SET opportunity_json = ?, urgency_score = ?, processed_at = ?
        WHERE id = ?
        """,
        (
            json.dumps(opportunity),
            urgency_score,
            datetime.now(timezone.utc).isoformat(),
            reg_id,
        ),
    )
    conn.commit()
    conn.close()


def get_processed(limit: int = 50) -> list[dict]:
    """Return processed regulations ordered by urgency_score descending."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT * FROM regulations
        WHERE opportunity_json IS NOT NULL
        ORDER BY urgency_score DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    results = []
    for r in rows:
        row = dict(r)
        if row.get("opportunity_json"):
            row["opportunity"] = json.loads(row["opportunity_json"])
        results.append(row)
    return results


if __name__ == "__main__":
    init_db()
    print("[DB] Schema created successfully.")