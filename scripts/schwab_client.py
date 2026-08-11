"""
Pulls real account/position data from Schwab.

Handles refreshing the access token automatically (it expires every ~30 min)
using the refresh token saved by schwab_auth.py, so i don't have to
re-run the browser login each time.
"""

import base64
import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.environ["SCHWAB_CLIENT_ID"]
CLIENT_SECRET = os.environ["SCHWAB_CLIENT_SECRET"]
TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"
ACCOUNTS_URL = "https://api.schwabapi.com/trader/v1/accounts"
TOKEN_FILE = "tokens.json"


def load_tokens() -> dict:
    with open(TOKEN_FILE, "r") as f:
        return json.load(f)


def save_tokens(tokens: dict):
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f, indent=2)


def refresh_access_token() -> str:
    """Use the refresh token to get a new access token. Returns the new access token."""
    tokens = load_tokens()
    refresh_token = tokens["refresh_token"]

    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    response = requests.post(TOKEN_URL, headers=headers, data=payload)

    if response.status_code != 200:
        raise RuntimeError(
            f"Token refresh failed ({response.status_code}): {response.text}"
        )

    new_tokens = response.json()

    # Schwab's refresh response may or may not include a new refresh_token —
    # if it doesn't, keep using the old one rather than overwriting with nothing.
    if "refresh_token" not in new_tokens:
        new_tokens["refresh_token"] = refresh_token

    save_tokens(new_tokens)
    return new_tokens["access_token"]


def get_account_numbers(access_token: str) -> list[dict]:
    """Schwab requires resolving account numbers to encrypted 'hash values' first."""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(f"{ACCOUNTS_URL}/accountNumbers", headers=headers)

    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch account numbers ({response.status_code}): {response.text}"
        )

    return response.json()


def get_positions(access_token: str, encrypted_account_id: str) -> dict:
    """Fetch full account detail including current positions."""
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"fields": "positions"}

    response = requests.get(
        f"{ACCOUNTS_URL}/{encrypted_account_id}", headers=headers, params=params
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch positions ({response.status_code}): {response.text}"
        )

    return response.json()


if __name__ == "__main__":
    print("Refreshing access token...")
    access_token = refresh_access_token()
    print("Got a fresh access token.\n")

    print("Fetching account numbers...")
    accounts = get_account_numbers(access_token)
    print(f"Found {len(accounts)} account(s):")
    for acct in accounts:
        print(f"  {acct}")

    if accounts:
        first_account_hash = accounts[0]["hashValue"]
        print(f"\nFetching positions for first account...")
        positions_data = get_positions(access_token, first_account_hash)
        print(json.dumps(positions_data, indent=2))
