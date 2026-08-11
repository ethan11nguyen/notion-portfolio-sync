"""
Stage 1, step 2: Prove we can write to the Notion database.

This is the trickier part: instead of always creating new rows
(which would leave stale duplicates every time the script runs),
we UPSERT — update the row if the ticker already exists, otherwise
create a new one. This is the "debug why it's wrong" muscle in
action: forgetting this step is the most common bug in a sync script.
"""

import os
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

NOTION_API_KEY = os.environ["NOTION_API_KEY"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]

notion = Client(auth=NOTION_API_KEY)


def find_existing_row(ticker: str):
    """Search the database for a row matching this ticker. Returns the row ID or None."""
    response = notion.databases.query(
        database_id=DATABASE_ID,
        filter={
            "property": "Ticker",
            "title": {"equals": ticker},
        },
    )
    results = response["results"]
    return results[0]["id"] if results else None


def upsert_holding(ticker: str, value: float, change_pct: float, sector: str):
    """Create or update a single holding row."""
    properties = {
        "Ticker": {"title": [{"text": {"content": ticker}}]},
        "Value": {"number": value},
        "Change %": {"number": change_pct},
        "Sector": {"select": {"name": sector}},
    }

    existing_id = find_existing_row(ticker)

    if existing_id:
        notion.pages.update(page_id=existing_id, properties=properties)
        print(f"  Updated {ticker}")
    else:
        notion.pages.create(
            parent={"database_id": DATABASE_ID},
            properties=properties,
        )
        print(f"  Created {ticker}")


if __name__ == "__main__":
    # Fake data for now — Stage 2 replaces this with real Schwab API pulls.
    fake_holdings = [
        {"ticker": "AAPL", "value": 1500.00, "change_pct": 1.2, "sector": "Tech"},
        {"ticker": "JPM", "value": 800.00, "change_pct": -0.5, "sector": "Finance"},
    ]

    for h in fake_holdings:
        upsert_holding(h["ticker"], h["value"], h["change_pct"], h["sector"])
