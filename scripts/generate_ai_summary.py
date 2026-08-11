"""
AI-generated portfolio commentary.

Reads current holdings from the Notion database, sends them to Claude
with a prompt asking for a short plain-English summary, and appends
that summary as a new dated entry on the Portfolio Log page.
"""

import os
from datetime import date

import anthropic
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

NOTION_API_KEY = os.environ["NOTION_API_KEY"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]
LOG_PAGE_ID = os.environ["NOTION_LOG_PAGE_ID"]
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


def generate_summary(holdings: list[dict]) -> str:
    """Ask Claude for a short plain-English summary of today's holdings."""
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

    return response.content[0].text


def create_log_subpage(summary: str):
    """Create a new dated subpage under the Portfolio Log page for this run."""
    today = date.today().strftime("%B %d, %Y")

    notion.pages.create(
        parent={"page_id": LOG_PAGE_ID},
        properties={
            "title": [{"type": "text", "text": {"content": today}}],
        },
        children=[
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": summary}}]
                },
            },
        ],
    )


if __name__ == "__main__":
    print("Reading holdings from Notion...")
    holdings = read_holdings()
    print(f"Found {len(holdings)} holding(s).\n")

    print("Generating summary with Claude...")
    summary = generate_summary(holdings)
    print(f"\nSummary:\n{summary}\n")

    print("Creating log entry in Notion...")
    create_log_subpage(summary)
    print("Done.")