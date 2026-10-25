#!/usr/bin/env python3
"""
Opportunity Builder — Builds open-source alternatives for approved opportunities.
Uses REA for reverse engineering and subagents for building.

Usage:
    python3 build_opportunities.py --check      # Check for approved opportunities
    python3 build_opportunities.py --build NAME # Build a specific opportunity
    python3 build_opportunities.py --status     # Show build status
    python3 build_opportunities.py --auto       # Auto-build highest scored opportunity
"""

import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path("/home/ubuntu/opportunity-hunter")
DATA_DIR = BASE_DIR / "data"
TARGETS_DIR = BASE_DIR / "targets"
LOGS_DIR = BASE_DIR / "logs"
BUILD_LOG = LOGS_DIR / "build.log"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

DB_PATH = DATA_DIR / "opportunities.db"


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def check_approved():
    """Check for approved opportunities ready to build."""
    conn = get_db()
    cur = conn.execute("""
        SELECT * FROM opportunities
        WHERE status = 'approved'
        ORDER BY total_score DESC
    """)
    approved = [dict(row) for row in cur]
    conn.close()
    return approved


def get_build_status():
    """Show build status."""
    conn = get_db()

    counts = {}
    for status in ['approved', 'building', 'built']:
        cur = conn.execute(f"SELECT COUNT(*) FROM opportunities WHERE status = ?", (status,))
        counts[status] = cur.fetchone()[0]

    recent = conn.execute("""
        SELECT name, total_score, status, built_at, repo_url
        FROM opportunities
        WHERE status IN ('building', 'built')
        ORDER BY updated_at DESC
        LIMIT 10
    """).fetchall()

    conn.close()

    print("=" * 50)
    print("OPPORTUNITY BUILDER — STATUS")
    print("=" * 50)
    print(f"Approved (ready to build): {counts['approved']}")
    print(f"Building: {counts['building']}")
    print(f"Built: {counts['built']}")

    if recent:
        print(f"\n{'='*50}")
        print("RECENT BUILDS")
        print("=" * 50)
        for row in recent:
            d = dict(row)
            print(f"  [{d['status']}] {d['name']} (score: {d['total_score']:.0f})")
            if d.get('repo_url'):
                print(f"    Repo: {d['repo_url']}")
            if d.get('built_at'):
                print(f"    Built: {d['built_at']}")


def mark_building(name: str):
    """Mark an opportunity as building."""
    conn = get_db()
    conn.execute("""
        UPDATE opportunities SET status = 'building', updated_at = ?
        WHERE name = ?
    """, (datetime.now(timezone.utc).isoformat(), name))
    conn.commit()
    conn.close()


def mark_built(name: str, repo_url: str):
    """Mark an opportunity as built."""
    conn = get_db()
    conn.execute("""
        UPDATE opportunities SET
            status = 'built',
            built_at = ?,
            repo_url = ?,
            updated_at = ?
        WHERE name = ?
    """, (datetime.now(timezone.utc).isoformat(), repo_url,
          datetime.now(timezone.utc).isoformat(), name))
    conn.commit()
    conn.close()


def analyze_with_rea(target_name: str, target_url: str) -> str:
    """Analyze a target using REA. Returns analysis summary."""
    # REA can analyze JavaScript applications, web bundles, etc.
    # For now, this is a placeholder that would call REA's analyze command
    analysis_dir = TARGETS_DIR / target_name.replace(" ", "_").lower()
    analysis_dir.mkdir(parents=True, exist_ok=True)

    analysis = {
        "target": target_name,
        "url": target_url,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
        "notes": f"Target '{target_name}' queued for REA analysis",
    }

    # Write analysis request
    (analysis_dir / "analysis_request.json").write_text(json.dumps(analysis, indent=2))

    return str(analysis_dir)


def create_build_plan(opp: dict) -> dict:
    """Create a build plan for an opportunity."""
    return {
        "name": opp["name"],
        "category": opp.get("category", "general"),
        "description": opp.get("description", ""),
        "score": opp.get("total_score", 0),
        "price_usd": opp.get("current_price_usd"),
        "source_url": opp.get("source_url"),
        "source_snippet": opp.get("source_snippet", ""),
        "steps": [
            {"step": 1, "name": "Research", "description": "Deep research on the target tool"},
            {"step": 2, "name": "Reverse Engineer", "description": "Analyze with REA if available"},
            {"step": 3, "name": "Design", "description": "Architecture and feature planning"},
            {"step": 4, "name": "Build", "description": "Implement the alternative"},
            {"step": 5, "name": "Publish", "description": "Push to GitHub with docs"},
        ],
    }


def auto_build():
    """Auto-build the highest scored approved opportunity."""
    approved = check_approved()
    if not approved:
        print("No approved opportunities to build.")
        return

    opp = approved[0]
    print(f"\n{'='*60}")
    print(f"AUTO-BUILD: {opp['name']}")
    print(f"Score: {opp['total_score']:.0f}/100")
    print(f"Category: {opp.get('category', 'unknown')}")
    print(f"{'='*60}\n")

    # Mark as building
    mark_building(opp['name'])

    # Create analysis request
    analysis_path = analyze_with_rea(opp['name'], opp.get('source_url', ''))

    # Create build plan
    plan = create_build_plan(opp)
    plan_path = TARGETS_DIR / opp['name'].replace(" ", "_").lower() / "build_plan.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan, indent=2))

    print(f"Build plan created: {plan_path}")
    print(f"Analysis request: {analysis_path}")
    print(f"\nNext: Use Hermes to dispatch a subagent to build this opportunity.")
    print(f"Subagent goal: Build open-source alternative to '{opp['name']}'")
    print(f"Target: {opp.get('source_url', 'N/A')}")
    print(f"Category: {opp.get('category', 'general')}")


def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "--check":
            approved = check_approved()
            print(f"Approved opportunities: {len(approved)}")
            for opp in approved:
                print(f"  [{opp['total_score']:.0f}] {opp['name']} ({opp.get('category', '?')})")
            return
        elif cmd == "--status":
            get_build_status()
            return
        elif cmd == "--auto":
            auto_build()
            return
        elif cmd == "--build" and len(sys.argv) > 2:
            name = " ".join(sys.argv[2:])
            mark_building(name)
            print(f"Marked '{name}' as building")
            print("Use Hermes to dispatch a subagent for the actual build.")
            return

    print(__doc__)


if __name__ == "__main__":
    main()
