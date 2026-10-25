# 🔍 Opportunity Hunter

**24/7 Automated Research & Build System for Open-Source Alternatives**

[![Status](https://img.shields.io/badge/status-running-green)]() [![Python](https://img.shields.io/badge/Python-3.12-blue)]()

## 🚀 What is Opportunity Hunter?

Opportunity Hunter is an automated system that:

1. **Researches 24/7** — Scans the internet for overpriced SaaS, tools, and subscriptions
2. **Scores Opportunities** — Scores each opportunity 0-100 based on price, demand, pain points
3. **Auto-Approves** — Opportunities above 45/100 are auto-approved for building
4. **Builds Alternatives** — Dispatches AI subagents to build open-source alternatives
5. **Publishes to GitHub** — All builds pushed under `0xshaikh` org

**No manual research needed. No idea selection needed. Just run it.**

## 📊 Current Status

| Metric | Count |
|--------|-------|
| Total Opportunities | 128+ |
| Approved (Ready to Build) | 61+ |
| Built | 0+ (first build pending) |
| Research Cycles | Running every 4 hours |
| Build Checks | Every 2 hours |

### Top Approved Opportunities

| # | Tool | Category | Price | Score |
|---|------|----------|-------|-------|
| 1 | SEMrush | SEO | $120/mo | 72.5 |
| 2 | Ahrefs | SEO | $99/mo | 68.5 |
| 3 | Buffer Pro | Social Media | $120/mo | 65.5 |
| 4 | Google Analytics Pro | Analytics | $500/mo | 64.5 |
| 5 | Typeform Pro | Form Builder | $25/mo | 62.5 |
| 6 | QuickBooks Online | Accounting | $35/mo | 62.5 |
| 7 | Salesforce | CRM | $25/user/mo | 60.0 |
| 8 | ActiveCampaign | Marketing | $15/mo | 59.0 |
| 9 | Zapier Pro | Automation | $20/mo | 59.0 |
| 10 | Figma | Design | $15/mo | 58.5 |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Research Daemon (systemd)                │
│  DuckDuckGo Search → Parse → Filter → Score → Store        │
│  Runs every 4 hours, 25 targeted queries                    │
└────────────────────────┬────────────────────────────────────┘
                         │ SQLite Database
┌────────────────────────▼────────────────────────────────────┐
│                    Opportunity Database                       │
│  128+ opportunities scored 0-100                            │
│  61+ approved (score >= 45)                                 │
└────────────────────────┬────────────────────────────────────┘
                         │ Hermes Cron (every 2h)
┌────────────────────────▼────────────────────────────────────┐
│                    Opportunity Builder                         │
│  Check approved → Dispatch Subagent → Build → Push GitHub   │
└────────────────────────┬────────────────────────────────────┘
                         │ Subagent
┌────────────────────────▼────────────────────────────────────┐
│                    REA (Reverse Engineer Anything)            │
│  Analyze target tool → Extract features → Guide build        │
└─────────────────────────────────────────────────────────────┘
```

## 🛠️ Components

### 1. Research Daemon (`research_daemon.py`)
- Runs as systemd service + timer
- Searches 25 targeted queries every 4 hours
- Filters non-product results (articles, blogs, etc.)
- Scores opportunities 0-100
- Loads curated list of 24 known overpriced tools
- Stores in SQLite database

### 2. Opportunity Builder (`build_opportunities.py`)
- Checks for approved opportunities every 2 hours
- Dispatches Hermes subagents to build alternatives
- Tracks build status
- Pushes to GitHub

### 3. REA Integration (`/home/ubuntu/rea`)
- Reverse engineering engine for analyzing target tools
- Can analyze JavaScript apps, web bundles, Electron apps
- Provides feature extraction and architecture insights

## 🔧 Setup

### Prerequisites
- Python 3.12+
- Node.js 24.22+ (for REA)
- Git

### Installation

```bash
# Clone the project
cd /home/ubuntu
git clone https://github.com/0xshaikh/opportunity-hunter.git

# Setup Python venv
cd opportunity-hunter
python3 -m venv venv
./venv/bin/pip install duckduckgo_search beautifulsoup4 lxml requests requests-cache

# Install REA (Reverse Engineer Anything)
cd /home/ubuntu
git clone https://github.com/morluto/rea.git
cd rea
npm install
npm run build:cached
npx rea-agents setup

# Start the research daemon
sudo systemctl enable --now opportunity-hunter.service
sudo systemctl enable --now opportunity-hunter.timer

# Verify
cd /home/ubuntu/opportunity-hunter
./venv/bin/python3 research_daemon.py --status
```

## 📁 Project Structure

```
opportunity-hunter/
├── research_daemon.py       # Main research daemon
├── build_opportunities.py   # Opportunity builder
├── check_opportunities.py   # Status checker (cron script)
├── mark_built.py            # Mark opportunity as built
├── data/
│   └── opportunities.db     # SQLite database
├── targets/                  # Analysis targets
├── logs/                     # Logs
├── reports/                  # Reports
└── venv/                     # Python virtual environment
```

## 📊 Scoring System

Opportunities are scored 0-100 based on:

| Factor | Points | Criteria |
|--------|--------|----------|
| Price Pain | 20 | Higher price = more opportunity |
| Category Weight | 15 | AI tools, marketing, design = higher weight |
| Pain Signals | 20 | Mentions of "expensive", "frustrating", "switched" |
| Open Source Gap | 15 | Fewer alternatives = more opportunity |
| Demand | 10 | Search volume proxy |
| Buildability | 15 | Simpler categories = higher score |

**Thresholds:**
- **45+** = Auto-approved for building
- **35-44** = Worth investigating
- **25-34** = Stored, low priority
- **<25** = Discarded

## 🎯 Categories Tracked

| Category | Weight | Examples |
|----------|--------|----------|
| AI Tools | 1.4 | ChatGPT, Midjourney, DALL-E |
| Design | 1.3 | Figma, Canva, Adobe Creative |
| Video Editing | 1.2 | Premiere Pro, After Effects |
| CRM | 1.2 | Salesforce, HubSpot |
| Marketing | 1.2 | ActiveCampaign, Zapier |
| Social Media | 1.1 | Buffer, Hootsuite |
| SEO | 1.1 | Ahrefs, SEMrush |
| Analytics | 1.1 | Google Analytics, Mixpanel |
| Security | 1.1 | Vercel, Intercom |
| Project Management | 1.0 | Asana, Monday.com |
| Email Marketing | 1.0 | Mailchimp, SendGrid |
| Monitoring | 1.0 | Vercel Pro |

## 🔌 API / CLI Commands

```bash
# Check status
./venv/bin/python3 research_daemon.py --status

# Show detailed report
./venv/bin/python3 research_daemon.py --report

# Run one research cycle manually
./venv/bin/python3 research_daemon.py

# Check approved opportunities
./venv/bin/python3 build_opportunities.py --check

# Check build status
./venv/bin/python3 build_opportunities.py --status

# Auto-build highest scored opportunity
./venv/bin/python3 build_opportunities.py --auto

# Add manual target
./venv/bin/python3 research_daemon.py --add "Tool Name"
```

## 📅 Schedules

| Component | Schedule | Description |
|-----------|----------|-------------|
| Research Daemon | Every 4 hours | Scan internet for new opportunities |
| Opportunity Builder | Every 2 hours | Check for approved, dispatch builds |
| Scoring | After each cycle | Re-score all opportunities |

## 🔔 Notifications

- Telegram notifications for high-score opportunities
- Build progress reports
- Error alerts

## 🤝 Contributing

1. Add new curated targets to `CURATED_TARGETS`
2. Improve search queries for better results
3. Add new categories and weights
4. Improve the scoring algorithm

## 📄 License

MIT

---

**Built by [0xshaikh](https://github.com/0xshaikh)** · Powered by [Hermes Agent](https://hermes-agent.nousresearch.com/)
