import os
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

NOTION_API_KEY = os.environ["NOTION_API_KEY"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]

notion = Client(auth=NOTION_API_KEY)


def read_portfolio_database():
    """Query the database and print every row's Ticker + Value."""
    response = notion.databases.query(database_id=DATABASE_ID)

    rows = response["results"]
    print(f"Found {len(rows)} row(s) in the database.\n")

    for row in rows:
        props = row["properties"]

        # Title properties are stored as a list of rich text objects —
        # this is the fussy part of the Notion API mentioned earlier.
        ticker_list = props["Ticker"]["title"]
        ticker = ticker_list[0]["plain_text"] if ticker_list else "(empty)"

        value = props["Value"]["number"]

        print(f"  {ticker}: {value}")


if __name__ == "__main__":
    read_portfolio_database()
