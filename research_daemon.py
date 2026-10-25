#!/usr/bin/env python3
"""
Opportunity Hunter — Research Daemon
====================================
Scans the internet 24/7 for overpriced SaaS, tools, and subscriptions.
Identifies profitable opportunities where open-source alternatives can be built.

Usage:
    python3 research_daemon.py              # Run one research cycle
    python3 research_daemon.py --daemon     # Run continuously (systemd)
    python3 research_daemon.py --status     # Show current status
    python3 research_daemon.py --report     # Show recent opportunities
    python3 research_daemon.py --add "TargetName"  # Manually add a target
"""

import json
import os
import re
import sqlite3
import sys
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Configuration ──────────────────────────────────────────────
BASE_DIR = Path("/home/ubuntu/opportunity-hunter")
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
TARGETS_DIR = BASE_DIR / "targets"
LOGS_DIR = BASE_DIR / "logs"

DB_PATH = DATA_DIR / "opportunities.db"
STATUS_FILE = DATA_DIR / "status.json"
TARGETS_FILE = DATA_DIR / "targets.json"

# Telegram notification (optional)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "911845951")

# Research intervals (seconds)
RESEARCH_INTERVAL = 4 * 3600  # 4 hours between research cycles
SCORING_INTERVAL = 2 * 3600  # 2 hours between scoring cycles

# Scoring thresholds
HIGH_SCORE_THRESHOLD = 45   # Auto-approve for building
MEDIUM_SCORE_THRESHOLD = 35  # Worth investigating
MIN_SCORE_THRESHOLD = 25     # Minimum to store

# ── Search Queries ─────────────────────────────────────────────
SEARCH_QUERIES = [
    # Overpriced SaaS discovery - targeting actual products
    "site:producthunt.com \"overpriced\" OR \"too expensive\" 2025 2026",
    "saas alternatives 2026 open source",
    "best value saas alternatives 2025",
    "\"expensive\" \"saas\" \"alternative\" 2025 2026",
    "high paid plan expensive subscription software",
    # Pricing pain points
    "\"too expensive\" saas subscription software",
    "\"overpriced\" software \"cheaper alternative\"",
    "\"switched from\" \"to\" \"open source\" software",
    "\"not worth the price\" software tool",
    "\"paying too much\" for software subscription",
    # High-value categories
    "video editing software expensive alternative free",
    "design tool expensive alternative free open source",
    "project management expensive alternative free",
    "email marketing expensive alternative free open source",
    "crm expensive alternative free open source",
    "analytics tool expensive alternative free",
    "seo tool expensive alternative free open source",
    "social media management expensive alternative free",
    "form builder expensive alternative free",
    "inventory management expensive alternative free",
    "ai tool expensive alternative free open source",
    "marketing automation expensive alternative free",
    # Revenue intelligence
    "site:g2.com expensive alternative",
    "site:trustradius.com expensive alternative",
    "site:alternativeto.net \"expensive\" OR \"overpriced\"",
]

# ── Curated high-value targets (well-known overpriced tools) ───
CURATED_TARGETS = [
    # Video editing
    {"name": "Adobe Premiere Pro", "category": "video-editing", "url": "https://www.adobe.com/products/premiere.html", "price_usd": 22.99, "description": "Industry-standard video editing. Users complain about subscription model, lack of offline features. Open Source alternative: Kdenlive, DaVinci Resolve"},
    {"name": "After Effects", "category": "video-editing", "url": "https://www.adobe.com/products/aftereffects.html", "price_usd": 22.99, "description": "Professional motion graphics and VFX. Very expensive, steep learning curve. Open Source alternative: Natron, Blender"},
    # Design
    {"name": "Figma", "category": "design", "url": "https://figma.com/pricing", "price_usd": 15.0, "description": "Collaborative design tool. Getting expensive for teams. Open Source alternative: Penpot, GrapesJS"},
    {"name": "Canva Pro", "category": "design", "url": "https://www.canva.com/pricing/", "price_usd": 12.99, "description": "Popular design tool. Paid features are locked behind subscription. Open Source alternative: Pixlr, Photopea"},
    # Project Management
    {"name": "Asana", "category": "project-management", "url": "https://asana.com/pricing", "price_usd": 10.99, "description": "Project management tool. Expensive per seat for teams. Open Source alternative: Taiga, Plane"},
    {"name": "Monday.com", "category": "project-management", "url": "https://monday.com/pricing", "price_usd": 9.0, "description": "Work management platform. Very expensive at scale. Open Source alternative: Taiga, Focalboard"},
    # Email Marketing
    {"name": "Mailchimp", "category": "email-marketing", "url": "https://mailchimp.com/pricing/", "price_usd": 13.0, "description": "Email marketing platform. Pricing increases sharply with subscriber count. Open Source alternative: Mautic, Listmonk"},
    {"name": "SendGrid", "category": "email-marketing", "url": "https://sendgrid.com/pricing/", "price_usd": 20.0, "description": "Transactional email platform. Expensive for high volume. Open Source alternative: Postal, Haraka"},
    # CRM
    {"name": "Salesforce", "category": "crm", "url": "https://www.salesforce.com/products/pricing/", "price_usd": 25.0, "description": "Enterprise CRM. Extremely expensive per user per month. Open Source alternative: Odoo, SuiteCRM, EspoCRM"},
    {"name": "HubSpot CRM", "category": "crm", "url": "https://www.hubspot.com/pricing", "price_usd": 20.0, "description": "Marketing and CRM platform. Gets very expensive as you scale. Open Source alternative: Odoo, EspoCRM"},
    # Analytics
    {"name": "Google Analytics Pro", "category": "analytics", "url": "https://marketingplatform.google.com/about/analytics/", "price_usd": 500.0, "description": "Professional analytics. GA4 free has limitations. Open Source alternative: Plausible, Matomo, Umami"},
    {"name": "Mixpanel", "category": "analytics", "url": "https://mixpanel.com/pricing/", "price_usd": 20.0, "description": "Product analytics. Pricing based on events, gets expensive. Open Source alternative: PostHog, Plausible"},
    # SEO
    {"name": "Ahrefs", "category": "seo", "url": "https://ahrefs.com/pricing", "price_usd": 99.0, "description": "SEO tool suite. Very expensive for individual users. Open Source alternative: Serpstat alternative, custom scraper"},
    {"name": "SEMrush", "category": "seo", "url": "https://www.semrush.com/pricing/", "price_usd": 119.95, "description": "SEO and marketing analytics. Very expensive. Open Source alternative: Serpstat alternative"},
    # Social Media
    {"name": "Buffer Pro", "category": "social-media", "url": "https://buffer.com/pricing", "price_usd": 120.0, "description": "Social media management. Pricing per channel is very expensive. Open Source alternative: Typefully open source, Mixpost"},
    {"name": "Hootsuite", "category": "social-media", "url": "https://www.hootsuite.com/pricing", "price_usd": 49.0, "description": "Social media management. Very expensive for small teams. Open Source alternative: Mixpost, Typefully"},
    # AI Tools
    {"name": "ChatGPT Plus", "category": "ai-tools", "url": "https://openai.com/chatgpt/pricing/", "price_usd": 20.0, "description": "AI assistant. Users want free/local alternatives. Open Source alternative: Ollama + local models"},
    {"name": "Midjourney", "category": "ai-tools", "url": "https://www.midjourney.com/pricing", "price_usd": 10.0, "description": "AI image generation. Subscription only. Open Source alternative: Stable Diffusion, ComfyUI"},
    # Security
    {"name": "Vercel Pro", "category": "monitoring", "url": "https://vercel.com/pricing", "price_usd": 20.0, "description": "Frontend platform. Bandwidth and build costs can be high. Open Source alternative: Netlify alternative"},
    {"name": "Intercom", "category": "analytics", "url": "https://www.intercom.com/pricing", "price_usd": 29.0, "description": "Customer messaging. Very expensive per seat. Open Source alternative: Chatwoot"},
    # Marketing Automation
    {"name": "ActiveCampaign", "category": "marketing", "url": "https://www.activecampaign.com/pricing/", "price_usd": 15.0, "description": "Marketing automation and CRM. Gets expensive with contacts. Open Source alternative: Mautic, SendOwl"},
    {"name": "Zapier Pro", "category": "marketing", "url": "https://zapier.com/pricing", "price_usd": 19.99, "description": "Automation platform. Task-based pricing can be very expensive. Open Source alternative: n8n, Activepieces"},
    # E-commerce
    {"name": "Shopify", "category": "ecommerce", "url": "https://www.shopify.com/pricing", "price_usd": 39.0, "description": "E-commerce platform. Transaction fees on top of monthly. Open Source alternative: Medusa, Saleor, WooCommerce"},
    # Form Builder
    {"name": "Typeform Pro", "category": "form-builder", "url": "https://www.typeform.com/pricing/", "price_usd": 25.0, "description": "Form builder. Expensive for high response volume. Open Source alternative: Formbricks, HeyForm"},
    # Inventory
    {"name": "QuickBooks Online", "category": "inventory", "url": "https://quickbooks.intuit.com/pricing/", "price_usd": 35.0, "description": "Accounting software. Gets expensive for businesses. Open Source alternative: Odoo, ERPNext"},
]

# ── Opportunity Categories ─────────────────────────────────────
CATEGORIES = {
    "video-editing": {"weight": 1.2, "keywords": ["video", "edit", "film", "movie", "cutting", "vlog"]},
    "design": {"weight": 1.3, "keywords": ["design", "graphic", "illustration", "vector", "ux", "ui"]},
    "analytics": {"weight": 1.1, "keywords": ["analytics", "analytics", "data", "metrics", "dashboard"]},
    "crm": {"weight": 1.2, "keywords": ["crm", "customer", "relationship", "sales"]},
    "email-marketing": {"weight": 1.0, "keywords": ["email", "marketing", "campaign", "newsletter"]},
    "project-management": {"weight": 1.0, "keywords": ["project", "task", "kanban", "agile", "scrum"]},
    "social-media": {"weight": 1.1, "keywords": ["social", "instagram", "facebook", "twitter", "tiktok"]},
    "seo": {"weight": 1.1, "keywords": ["seo", "search", "ranking", "keyword"]},
    "ecommerce": {"weight": 1.0, "keywords": ["ecommerce", "shop", "store", "product"]},
    "form-builder": {"weight": 0.9, "keywords": ["form", "survey", "questionnaire"]},
    "inventory": {"weight": 0.9, "keywords": ["inventory", "stock", "warehouse"]},
    "marketing": {"weight": 1.2, "keywords": ["marketing", "ads", "advertising", "campaign"]},
    "ai-tools": {"weight": 1.4, "keywords": ["ai", "gpt", "chatbot", "automation", "agent"]},
    "security": {"weight": 1.1, "keywords": ["security", "scanner", "audit", "pentest"]},
    "monitoring": {"weight": 1.0, "keywords": ["monitor", "uptime", "status", "alert"]},
}

# ── Logging ────────────────────────────────────────────────────
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "research.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("research")

# ── Database ──────────────────────────────────────────────────
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS opportunities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT,
        url TEXT,
        current_price TEXT,
        current_price_usd REAL,
        description TEXT,
        pain_points TEXT,
        search_volume INTEGER DEFAULT 0,
        user_count INTEGER DEFAULT 0,
        open_source_alternatives INTEGER DEFAULT 0,
        market_gap_score REAL DEFAULT 0,
        build_effort_score REAL DEFAULT 0,
        revenue_potential_score REAL DEFAULT 0,
        total_score REAL DEFAULT 0,
        status TEXT DEFAULT 'discovered',
        source_query TEXT,
        source_url TEXT,
        source_snippet TEXT,
        discovered_at TEXT,
        updated_at TEXT,
        research_notes TEXT,
        built_at TEXT,
        repo_url TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_opportunity_score ON opportunities(total_score DESC);
    CREATE INDEX IF NOT EXISTS idx_opportunity_status ON opportunities(status);
    CREATE TABLE IF NOT EXISTS research_cycles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT,
        completed_at TEXT,
        queries_run INTEGER DEFAULT 0,
        results_found INTEGER DEFAULT 0,
        new_opportunities INTEGER DEFAULT 0,
        errors TEXT
    );
    CREATE TABLE IF NOT EXISTS targets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        url TEXT,
        added_at TEXT,
        notes TEXT,
        status TEXT DEFAULT 'queued'
    );
    """)
    conn.commit()
    conn.close()


def upsert_opportunity(name: str, category: str, url: str, description: str,
                       source_query: str, source_url: str, source_snippet: str,
                       price_usd: Optional[float] = None):
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    try:
        # Check if exists
        cur = conn.execute("SELECT id FROM opportunities WHERE name = ? AND url = ?", (name, url))
        row = cur.fetchone()
        if row:
            conn.execute("""
                UPDATE opportunities SET
                    updated_at = ?,
                    category = ?,
                    description = ?,
                    source_snippet = ?,
                    current_price_usd = COALESCE(?, current_price_usd)
                WHERE id = ?
            """, (now, category, description, source_snippet, price_usd, row["id"]))
            log.info(f"Updated: {name}")
        else:
            conn.execute("""
                INSERT INTO opportunities
                    (name, category, url, description, source_query, source_url,
                     source_snippet, current_price_usd, discovered_at, updated_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'discovered')
            """, (name, category, url, description, source_query, source_url,
                  source_snippet, price_usd, now, now))
            log.info(f"New: {name} (score pending)")
        conn.commit()
    finally:
        conn.close()


def score_opportunity(opp: dict) -> float:
    """Score an opportunity 0-100."""
    score = 0.0

    # 1. Price pain (higher price = more opportunity) - 20 pts
    if opp.get("current_price_usd"):
        price = opp["current_price_usd"]
        if price >= 200:
            score += 20
        elif price >= 100:
            score += 16
        elif price >= 50:
            score += 12
        elif price >= 25:
            score += 9
        elif price >= 10:
            score += 6
        else:
            score += 3
    else:
        score += 3  # Unknown price = some opportunity

    # 2. Category weight - 15 pts
    cat = opp.get("category", "")
    for key, info in CATEGORIES.items():
        if key in cat:
            score += 15 * info["weight"]
            break
    else:
        score += 10  # Default

    # 3. User/pain signals from snippet - 20 pts
    snippet = (opp.get("source_snippet", "") + " " + opp.get("description", "")).lower()
    pain_keywords = ["expensive", "too expensive", "overpriced", "frustrating",
                     "switched", "alternative", "cheaper", "waste", "rip off",
                     "not worth", "overpay", "painful", "annoying"]
    pain_count = sum(1 for kw in pain_keywords if kw in snippet)
    score += min(pain_count * 5, 20)

    # 4. Open source gap (fewer alternatives = more opportunity) - 15 pts
    oss_count = opp.get("open_source_alternatives", 0)
    if oss_count == 0:
        score += 15
    elif oss_count == 1:
        score += 10
    elif oss_count == 2:
        score += 5

    # 5. Search volume proxy (mentions = demand) - 10 pts
    mentions = opp.get("search_volume", 0)
    score += min(mentions * 2, 10)

    # 6. Buildability - 15 pts (simpler = higher score)
    # We estimate based on category complexity
    simple_cats = ["form-builder", "inventory", "monitoring", "seo"]
    if cat in simple_cats:
        score += 15
    elif cat in ["ai-tools", "marketing"]:
        score += 10
    else:
        score += 8

    return min(score, 100)


def update_opportunity_scores():
    conn = get_db()
    cur = conn.execute("""
        SELECT * FROM opportunities
        WHERE status IN ('discovered', 'researched')
    """)
    updated = 0
    for row in cur:
        opp = dict(row)
        score = score_opportunity(opp)
        opp["total_score"] = score
        new_status = "discovered"
        if score >= HIGH_SCORE_THRESHOLD:
            new_status = "approved"
        elif score >= MEDIUM_SCORE_THRESHOLD:
            new_status = "researched"

        conn.execute("""
            UPDATE opportunities SET
                total_score = ?,
                status = CASE
                    WHEN ? >= ? THEN 'approved'
                    WHEN ? >= ? THEN 'researched'
                    ELSE 'discovered'
                END
            WHERE id = ?
        """, (score, score, HIGH_SCORE_THRESHOLD, score, MEDIUM_SCORE_THRESHOLD, opp["id"]))
        if new_status != "discovered":
            updated += 1
            log.info(f"Scored: {opp['name']} = {score:.1f} -> {new_status}")
    conn.commit()
    conn.close()
    return updated


# ── Search ─────────────────────────────────────────────────────
def search_web(query: str, max_results: int = 10) -> list:
    """Search the web using DuckDuckGo."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return results
    except Exception as e:
        log.warning(f"Search failed for '{query}': {e}")
        return []


def extract_price(text: str) -> Optional[float]:
    """Extract price in USD from text."""
    # Match patterns like $49/mo, $299/year, 49 USD, ₹499
    patterns = [
        r'\$(\d+[\d.]*)\s*(?:/?\s*(?:mo|month|monthly|year|annual|yr))?',
        r'(\d+[\d.]*)\s*(?:USD|usd)',
        r'₹\s*(\d+[\d.]*)',  # Indian Rupees
        r'\$\s*(\d+[\d.]*)',
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            try:
                return float(m.group(1))
            except (ValueError, IndexError):
                continue
    return None


def categorize(text: str) -> str:
    """Categorize based on keywords."""
    text_lower = text.lower()
    scores = {}
    for key, info in CATEGORIES.items():
        score = sum(1 for kw in info["keywords"] if kw in text_lower)
        if score > 0:
            scores[key] = score
    if scores:
        return max(scores, key=scores.get)
    return "general"


# ── URL filter: skip non-product URLs ─────────────────────────
SKIP_URL_PATTERNS = [
    r'\.gov', r'\.edu', r'\.mil', r'\.int',
    r'wikipedia', r'dictionary', r'thesis', r'blog',
    r'linkedin\.com', r'instagram\.com', r'youtube\.com',
    r'facebook\.com', r'twitter\.com', r'news\.com',
    r'\.app', r'\.dev', r'\.me',
    r'alternativeto\.net', r'alternative\.me',
    r'howto', r'tutorial', r'learn',
    r'reddit\.com',
]

SKIP_TITLE_PATTERNS = [
    r'(?i)\b(help|guide|tutorial|learn|how to|what is|definition|synonym)',
    r'(?i)\b(cancel|subscribe|login|sign in|faq)\b',
    r'(?i)\b(apps|all apps|categories|pricing)\b',
    r'(?i)\b[0-9]+\s(moved|error|page|result)',
]


def is_valid_product(url: str, title: str, snippet: str) -> bool:
    """Filter out non-product results."""
    # URL filter
    for pattern in SKIP_URL_PATTERNS:
        if re.search(pattern, url, re.I):
            return False

    # Title filter
    for pattern in SKIP_TITLE_PATTERNS:
        if re.search(pattern, title, re.I):
            return False

    # Title too short or looks like a generic page
    if len(title) < 3 or len(title) > 80:
        return False

    # Must have some product-like signal
    product_signals = [
        r'\b(app|tool|software|platform|service|solution)\b',
        r'\b(pricing|plans|subscription|free|trial|pro)\b',
        r'\$(\d+)', r'free', r'open source',
        r'saas', r'cloud', r'online',
    ]
    text = f"{title} {snippet}".lower()
    has_signal = any(re.search(p, text, re.I) for p in product_signals)

    return has_signal


def parse_search_results(query: str, results: list):
    """Parse search results into opportunities with filtering."""
    new_count = 0
    for result in results:
        title = result.get("title", "")
        url = result.get("href", "")
        snippet = result.get("body", "")

        # Filter
        if not is_valid_product(url, title, snippet):
            continue

        # Extract potential tool name from title
        name = title[:100] if title else "Unknown"
        # Clean up common patterns
        name = re.sub(r'\s*[-|:]\s*.*$', '', name).strip()
        name = re.sub(r'\s*\([^)]*\)', '', name).strip()
        # Remove common prefixes
        name = re.sub(r'(?i)^(top\s+\d+\s+|best\s+\d+\s+)', '', name).strip()

        if not name or len(name) < 3:
            continue

        # Extract price from snippet + title
        price_text = f"{title} {snippet}"
        price = extract_price(price_text)

        # Categorize
        category = categorize(f"{title} {snippet}")

        # Check for open source alternatives mention
        oss_count = len(re.findall(r'open source|alternativeto|github\.com', snippet, re.I))

        description = snippet[:500]

        upsert_opportunity(
            name=name,
            category=category,
            url=url,
            description=description,
            source_query=query,
            source_url=url,
            source_snippet=snippet[:300],
            price_usd=price,
        )
        new_count += 1

    return new_count


def load_curated_targets():
    """Load curated high-value targets into the database."""
    conn = get_db()
    count = 0
    for target in CURATED_TARGETS:
        upsert_opportunity(
            name=target["name"],
            category=target["category"],
            url=target["url"],
            description=target["description"],
            source_query="curated",
            source_url=target["url"],
            source_snippet=target["description"][:300],
            price_usd=target["price_usd"],
        )
        count += 1
    conn.close()
    log.info(f"Loaded {count} curated targets")


def run_research_cycle():
    """Run one full research cycle."""
    log.info("=" * 60)
    log.info("Starting research cycle")
    log.info("=" * 60)

    # Load curated targets first
    load_curated_targets()

    cycle_id = None
    conn = get_db()
    cur = conn.execute("""
        INSERT INTO research_cycles (started_at) VALUES (?)
    """, (datetime.now(timezone.utc).isoformat(),))
    cycle_id = cur.lastrowid
    conn.commit()
    conn.close()

    total_results = 0
    new_opps = 0
    errors = []

    for i, query in enumerate(SEARCH_QUERIES):
        try:
            log.info(f"[{i+1}/{len(SEARCH_QUERIES)}] Searching: {query[:80]}")
            results = search_web(query, max_results=8)
            total_results += len(results)

            if results:
                new_count = parse_search_results(query, results)
                new_opps += new_count

            # Rate limiting
            time.sleep(2)

        except Exception as e:
            error_msg = f"Query '{query[:50]}': {str(e)}"
            log.error(error_msg)
            errors.append(error_msg)

    # Score all unscored opportunities
    log.info("Scoring opportunities...")
    update_opportunity_scores()

    # Update cycle
    conn = get_db()
    conn.execute("""
        UPDATE research_cycles SET
            completed_at = ?,
            queries_run = ?,
            results_found = ?,
            new_opportunities = ?,
            errors = ?
        WHERE id = ?
    """, (datetime.now(timezone.utc).isoformat(), len(SEARCH_QUERIES),
          total_results, new_opps, json.dumps(errors), cycle_id))
    conn.commit()
    conn.close()

    # Update status file
    status = {
        "last_cycle": datetime.now(timezone.utc).isoformat(),
        "cycle_id": cycle_id,
        "total_results": total_results,
        "new_opportunities": new_opps,
        "errors": errors,
    }
    STATUS_FILE.write_text(json.dumps(status, indent=2))

    log.info(f"Cycle complete: {new_opps} new opportunities from {total_results} results")

    # Notify about high-score opportunities
    notify_high_score()

    return new_opps


def notify_high_score():
    """Send Telegram notification for high-score opportunities."""
    conn = get_db()
    cur = conn.execute("""
        SELECT name, total_score, category, url, current_price_usd
        FROM opportunities
        WHERE status = 'approved'
        ORDER BY total_score DESC
        LIMIT 5
    """)
    approved = [dict(row) for row in cur]
    conn.close()

    if not approved:
        return

    if not TELEGRAM_BOT_TOKEN:
        log.info(f"Would notify about {len(approved)} approved opportunities")
        return

    import urllib.request
    lines = ["🎯 *New High-Score Opportunities Found!*\n"]
    for opp in approved:
        price_str = f"${opp['current_price_usd']:.0f}" if opp.get("current_price_usd") else "?"
        lines.append(
            f"🏆 *{opp['name']}*\n"
            f"Score: {opp['total_score']:.0f}/100 | Category: {opp['category']}\n"
            f"Price: {price_str} | [Details]({opp['url']})\n"
        )
    lines.append("\n*These are auto-approved for building.*")

    message = "\n".join(lines)
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = json.dumps({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
        }).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        log.info(f"Notified about {len(approved)} opportunities")
    except Exception as e:
        log.warning(f"Telegram notification failed: {e}")


def get_status():
    """Show current status."""
    conn = get_db()

    counts = {}
    for status in ['discovered', 'researched', 'approved', 'building', 'built']:
        cur = conn.execute(f"SELECT COUNT(*) FROM opportunities WHERE status = ?", (status,))
        counts[status] = cur.fetchone()[0]

    top = conn.execute("""
        SELECT name, total_score, category, status, current_price_usd
        FROM opportunities ORDER BY total_score DESC LIMIT 10
    """).fetchall()

    last_cycle = conn.execute("""
        SELECT * FROM research_cycles ORDER BY id DESC LIMIT 1
    """).fetchone()

    conn.close()

    print("=" * 50)
    print("OPPORTUNITY HUNTER — STATUS")
    print("=" * 50)
    print(f"Total: {sum(counts.values())} opportunities")
    for s, c in counts.items():
        if c > 0:
            print(f"  {s.capitalize()}: {c}")

    print(f"\nLast cycle: {last_cycle['completed_at'] if last_cycle else 'Never'}")
    if last_cycle:
        print(f"  Queries: {last_cycle['queries_run']}, Results: {last_cycle['results_found']}")
        print(f"  New opportunities: {last_cycle['new_opportunities']}")

    if top:
        print(f"\n{'='*50}")
        print("TOP OPPORTUNITIES")
        print("=" * 50)
        for opp in top:
            price = f"${opp['current_price_usd']:.0f}" if opp['current_price_usd'] else "?"
            print(f"  {opp['total_score']:5.1f} | {opp['status']:10s} | {opp['name'][:40]:40s} | {price}")


def show_report():
    """Show detailed report of top opportunities."""
    conn = get_db()
    cur = conn.execute("""
        SELECT * FROM opportunities
        WHERE total_score >= 30
        ORDER BY total_score DESC
        LIMIT 20
    """)
    opps = [dict(row) for row in cur]
    conn.close()

    if not opps:
        print("No opportunities scored yet. Run a research cycle first.")
        return

    print("=" * 60)
    print("OPPORTUNITY REPORT")
    print("=" * 60)

    for opp in opps:
        price = f"${opp['current_price_usd']:.0f}" if opp['current_price_usd'] else "unknown"
        print(f"\n{'─'*60}")
        print(f"🏆 {opp['name']}")
        print(f"   Score: {opp['total_score']:.0f}/100 | Status: {opp['status']}")
        print(f"   Category: {opp['category']}")
        print(f"   Current Price: {price}")
        print(f"   Source: {opp['source_url']}")
        print(f"   Discovered: {opp['discovered_at']}")
        if opp.get('description'):
            print(f"   Description: {opp['description'][:200]}")
        print(f"{'─'*60}")


# ── Main ──────────────────────────────────────────────────────
def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    init_db()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "--status":
            get_status()
            return
        elif cmd == "--report":
            show_report()
            return
        elif cmd == "--add" and len(sys.argv) > 2:
            name = sys.argv[2]
            conn = get_db()
            try:
                conn.execute("""
                    INSERT INTO targets (name, added_at, status)
                    VALUES (?, ?, 'queued')
                """, (name, datetime.now(timezone.utc).isoformat()))
                conn.commit()
                print(f"Target '{name}' added to queue")
            except sqlite3.IntegrityError:
                print(f"Target '{name}' already exists")
            conn.close()
            return
        elif cmd == "--daemon":
            print("Running in daemon mode (Ctrl+C to stop)")
            while True:
                try:
                    run_research_cycle()
                    print(f"Next cycle in {RESEARCH_INTERVAL // 3600}h...")
                    time.sleep(RESEARCH_INTERVAL)
                except KeyboardInterrupt:
                    print("\nDaemon stopped")
                    break
                except Exception as e:
                    log.error(f"Daemon error: {e}")
                    time.sleep(60)
            return

    # Default: run one cycle
    run_research_cycle()
    print("\nDone. Use --status to see results.")


if __name__ == "__main__":
    main()
