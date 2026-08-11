"""
Full sync — Schwab positions -> Notion database.

Pulls real holdings from Schwab, maps them into the shape write_database.py
expects, and upserts into Notion. This replaces the fake_holdings list
that was used for Stage 3 testing.
"""

from schwab_client import refresh_access_token, get_account_numbers, get_positions
from write_database import upsert_holding

# Schwab's API doesn't return sector classification, so we maintain our own
# lookup here. Anything not in this dict falls back to "Uncategorized" —
# a real production version would pull this from a market data API instead.
SECTOR_LOOKUP = {
    "TSLA": "Consumer Discretionary",
    "VOO": "ETF - Broad Market",
    "SMH": "ETF - Semiconductors",
    "NIO": "Consumer Discretionary",
}


def get_sector(ticker: str) -> str:
    return SECTOR_LOOKUP.get(ticker, "Uncategorized")


def fetch_real_holdings() -> list[dict]:
    """Pull current positions from Schwab and map them into our Notion schema."""
    access_token = refresh_access_token()
    accounts = get_account_numbers(access_token)

    if not accounts:
        raise RuntimeError("No Schwab accounts found for this login.")

    holdings = []

    for account in accounts:
        account_hash = account["hashValue"]
        account_data = get_positions(access_token, account_hash)
        positions = account_data["securitiesAccount"].get("positions", [])

        for position in positions:
            ticker = position["instrument"]["symbol"]
            value = position["marketValue"]
            change_pct = position["currentDayProfitLossPercentage"]

            holdings.append(
                {
                    "ticker": ticker,
                    "value": round(value, 2),
                    "change_pct": round(change_pct, 2),
                    "sector": get_sector(ticker),
                }
            )

    return holdings


if __name__ == "__main__":
    print("Fetching real holdings from Schwab...")
    holdings = fetch_real_holdings()
    print(f"Found {len(holdings)} position(s).\n")

    print("Syncing to Notion...")
    for h in holdings:
        upsert_holding(h["ticker"], h["value"], h["change_pct"], h["sector"])

    print("\nSync complete.")
