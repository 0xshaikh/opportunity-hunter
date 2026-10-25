#!/usr/bin/env python3
"""Mark an opportunity as built."""
import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path("/home/ubuntu/opportunity-hunter/data/opportunities.db")
name = sys.argv[1] if len(sys.argv) > 1 else ""
repo_url = sys.argv[2] if len(sys.argv) > 2 else ""

if not name:
    print(json.dumps({"error": "Usage: mark_built.py NAME [REPO_URL]"}))
    sys.exit(1)

conn = sqlite3.connect(str(DB_PATH))
conn.execute("""
    UPDATE opportunities SET status='built', repo_url=?, updated_at=datetime('now') WHERE name=?
""", (repo_url, name))
conn.commit()
count = conn.total_changes
conn.close()
print(json.dumps({"ok": True, "updated": count}))
