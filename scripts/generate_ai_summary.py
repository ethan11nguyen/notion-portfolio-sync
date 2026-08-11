"""
AI-generated portfolio commentary.

Reads current holdings from the Notion database, sends them to Claude
with a prompt asking for a short plain-English summary, and appends
that summary as a new dated entry on the Portfolio Log page.
"""

import os
from datetime import datetime

import anthropic
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

NOTION_API_KEY = os.environ["NOTION_API_KEY"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]
NOTION_LOG_DATABASE_ID = os.environ["NOTION_LOG_DATABASE_ID"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

notion = Client(auth=NOTION_API_KEY)
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def read_holdings() -> list[dict]:
    """Pull all current holdings from the Notion database."""
    response = notion.databases.query(database_id=DATABASE_ID)
    holdings = []

    for row in response["results"]:
        props = row["properties"]

        ticker_list = props["Ticker"]["title"]
        ticker = ticker_list[0]["plain_text"] if ticker_list else "(unknown)"

        value = props["Value"]["number"]
        change_pct = props["Change %"]["number"]
        sector_obj = props["Sector"]["select"]
        sector = sector_obj["name"] if sector_obj else "Uncategorized"

        holdings.append(
            {
                "ticker": ticker,
                "value": value,
                "change_pct": change_pct,
                "sector": sector,
            }
        )

    return holdings


def generate_summary(holdings: list[dict]) -> tuple[str, float]:
    """Ask Claude for a short plain-English summary of today's holdings.
    Returns (summary_text, total_portfolio_value)."""
    holdings_text = "\n".join(
        f"- {h['ticker']} ({h['sector']}): ${h['value']:.2f}, {h['change_pct']:+.2f}% today"
        for h in holdings
    )

    total_value = sum(h["value"] for h in holdings)

    prompt = f"""Here is today's portfolio snapshot:

{holdings_text}

Total portfolio value: ${total_value:.2f}

Write a short (3-4 sentence) plain-English summary of today's portfolio
performance. Mention the biggest mover (up or down), note any sector-level
pattern if one exists, and keep the tone neutral and factual — this is a
personal tracking log, not investment advice.

Do not use markdown formatting (no headers, no bold, no bullet points) —
write plain sentences only, since this will be inserted directly as
plain text into a Notion page."""

    response = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text, total_value


def create_log_row(summary: str, total_value: float):
    """Add a new row to the Portfolio Log database for today's summary."""
    now = datetime.now()
    today_iso = now.date().isoformat()  # Notion's Date property expects ISO format
    timestamp_readable = now.strftime("%B %d, %Y – %I:%M %p")

    notion.pages.create(
        parent={"database_id": NOTION_LOG_DATABASE_ID},
        properties={
            # "Name" is the default title property Notion creates for every
            # new database — every database needs exactly one title property.
            "Name": {"title": [{"type": "text", "text": {"content": timestamp_readable}}]},
            "Date": {"date": {"start": today_iso}},
            "Summary": {
                "rich_text": [{"type": "text", "text": {"content": summary}}]
            },
            "Total Value": {"number": round(total_value, 2)},
        },
    )


if __name__ == "__main__":
    print("Reading holdings from Notion...")
    holdings = read_holdings()
    print(f"Found {len(holdings)} holding(s).\n")

    print("Generating summary with Claude...")
    summary, total_value = generate_summary(holdings)
    print(f"\nSummary:\n{summary}\n")

    print("Adding row to Portfolio Log database...")
    create_log_row(summary, total_value)
    print("Done.")