#!/usr/bin/env python3
"""
Check for approved opportunities ready to build.
Outputs JSON with the top opportunity if any are approved.
"""
import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path("/home/ubuntu/opportunity-hunter/data/opportunities.db")

try:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # Count approved
    cur = conn.execute("SELECT COUNT(*) FROM opportunities WHERE status = 'approved'")
    approved_count = cur.fetchone()[0]

    # Get top approved
    cur = conn.execute("""
        SELECT name, total_score, category, url, description, current_price_usd, source_snippet
        FROM opportunities
        WHERE status = 'approved'
        ORDER BY total_score DESC
        LIMIT 1
    """)
    top = cur.fetchone()

    # Count built
    cur = conn.execute("SELECT COUNT(*) FROM opportunities WHERE status = 'built'")
    built_count = cur.fetchone()[0]

    # Count discovered
    cur = conn.execute("SELECT COUNT(*) FROM opportunities")
    total = cur.fetchone()[0]

    conn.close()

    result = {
        "total": total,
        "approved": approved_count,
        "built": built_count,
        "top": dict(top) if top else None,
    }
    print(json.dumps(result, indent=2))

except Exception as e:
    print(json.dumps({"error": str(e), "approved": 0, "built": 0, "total": 0, "top": None}))
