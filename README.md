# Notion Portfolio Sync

A personal use pipeline that pulls my Charles Schwab brokerage holdings and syncs them into a Notion database. Inside my personal Notion, there is filtered views to see sector and performance. Claude is also used to generate a daily portfolio summary, running automatically in the cloud via GitHub Actions.

Brokerage holdings and daily performance logs are ingested into separate Notion databases, combining both components onto a unified dashboard using linked database views

## What it does

1.  **Authenticates with Schwab** using OAuth 2.0 (authorization code flow), with automatic access token refresh so it can run unattended.
2.  **Pulls current positions** (ticker, market value, today's % change) from the Schwab Trader API.
3.  **Syncs to a Notion database**, using an upsert pattern (update existing rows by ticker rather than creating duplicates on every run).
4.  **Three views, built directly in Notion** on top of that same database — no code involved, just Notion's native grouping/filtering:
    - **Portfolio** — the base table
    - **By Sector** — grouped with a Sum rollup on market value per sector
    - **Top Movers** — filtered/sorted by daily % change
5.  **Generates a daily AI summary** — sends the current holdings to Claude (Haiku), which writes a short, factual 3–4 sentence summary of the day's performance. That summary is logged as a new row in a separate Notion database (Date / Total Value / Summary), so history stays sortable and filterable instead of one long scrolling page.
6.  **Runs on a schedule** via GitHub Actions, every weekday shortly after market close — no local machine required.

## Update frequency
 
Both the holdings sync and the AI summary run **once per weekday**, shortly after US market close (~4:30 PM ET / 8:30 PM UTC). This is a deliberate scoping decision, not a limitation of the architecture — the two scripts are independent and callable on any schedule, so adding a second run (e.g., at market open) would just mean adding a second cron entry to the GitHub Actions workflow.
 
Practically, this means the **Portfolio** table shows values and daily % change as of the most recent close, not a live intraday feed. If you view the page mid-day, you're seeing yesterday's closing snapshot until that day's run completes.


## Architecture
 
```
Schwab API (OAuth 2.0)
   │  positions, market values, daily % change
   ▼
sync_schwab_to_notion.py  ──upsert──▶  Notion: Portfolio (database)
                                            │
                                            ▼
                                    Views (built manually in Notion):
                                    By Sector, Top Movers
                                            │
                                            ▼
generate_ai_summary.py  ──Claude API──▶  Notion: Portfolio Log (database)
 
Both scripts run daily via GitHub Actions (.github/workflows/daily-sync.yml)
```
 
## Tech stack
 
- **Python** — `requests`, `notion-client`, `anthropic`, `python-dotenv`
- **Notion API** — database queries, upserts, property mapping (title, number, select, date, rich_text)
- **Schwab Trader API** — OAuth 2.0 authorization code flow, token refresh, account/positions endpoints
- **Claude API** (Haiku) — AI-generated portfolio commentary
- **GitHub Actions** — scheduled automation, secrets management
## Repo structure
 
```
scripts/
├── schwab_auth.py            # One-time OAuth login, saves tokens.json
├── schwab_client.py          # Token refresh + Schwab API calls
├── sync_schwab_to_notion.py  # Full sync: Schwab positions -> Notion (upsert)
├── read_database.py          # Simple Notion read (proof of concept)
├── write_database.py         # Simple Notion write/upsert (proof of concept)
└── generate_ai_summary.py    # Claude-generated daily summary -> Notion log
 
.github/workflows/
└── daily-sync.yml            # Scheduled automation (weekdays, post-market-close)
```

## Notable design decisions

- **Upsert over append** — the sync checks for an existing row by ticker before writing, so re-running the script doesn't create duplicate holdings. This was a real bug I hit and fixed early on.
- **Manual sector lookup** — Schwab's position data doesn't include sector classification, so this is currently a small hardcoded dictionary.
- **Separate log database over appending to one page** — early versions of the AI summary feature wrote to a single growing page. Switched to a proper database (Date / Total Value / Summary) so history is sortable and filterable instead of requiring endless scrolling.
- **Known limitation: refresh token rotation.** The GitHub Actions workflow currently restores a static Schwab refresh token from a repository secret. If Schwab rotates the refresh token on use (common for OAuth providers), the automation will eventually need re-authentication.

## Setup
 
Requires a Notion integration, a Schwab Developer account with an approved app (Accounts and Trading Production), and an Anthropic API key.
 
```bash
pip install -r requirements.txt
cp .env.example .env  # fill in your own credentials
python scripts/schwab_auth.py  # one-time browser login, saves tokens.json
python scripts/sync_schwab_to_notion.py
python scripts/generate_ai_summary.py
```
 
For automated daily runs, see `.github/workflows/daily-sync.yml` — requires the same credentials added as GitHub repository secrets.