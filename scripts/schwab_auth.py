"""
Schwab OAuth authorization code flow.

Runs once to get an initial access token + refresh token.
Tokens are saved to tokens.json (gitignored) so don't have to
repeat the browser login every time — schwab_client.py will use
the refresh token to get new access tokens automatically.
"""

import base64
import json
import os
import webbrowser
from urllib.parse import urlparse, parse_qs

import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.environ["SCHWAB_CLIENT_ID"]
CLIENT_SECRET = os.environ["SCHWAB_CLIENT_SECRET"]
REDIRECT_URI = os.environ["SCHWAB_REDIRECT_URI"]

AUTH_URL = (
    "https://api.schwabapi.com/v1/oauth/authorize"
    f"?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}"
)
TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"
TOKEN_FILE = "tokens.json"


def get_authorization_code() -> str:
    """Open the Schwab login page and prompt the user to paste back the redirect URL."""
    print("Opening Schwab login in your browser...\n")
    webbrowser.open(AUTH_URL)

    print("After logging in, your browser will redirect to a URL that")
    print("looks broken ('this site can't be reached') — that's expected.")
    print("Copy the FULL URL from your browser's address bar and paste it below.\n")

    redirected_url = input("Paste the full redirect URL here: ").strip()

    parsed = urlparse(redirected_url)
    query_params = parse_qs(parsed.query)

    if "code" not in query_params:
        raise ValueError(
            "No 'code' parameter found in that URL. Make sure you copied "
            "the full address bar contents after being redirected."
        )

    # Schwab's code comes back URL-encoded in a way that needs the raw value.
    return query_params["code"][0]


def exchange_code_for_tokens(auth_code: str) -> dict:
    """Trade the authorization code for an access token + refresh token."""
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
    }

    response = requests.post(TOKEN_URL, headers=headers, data=payload)

    if response.status_code != 200:
        raise RuntimeError(
            f"Token exchange failed ({response.status_code}): {response.text}"
        )

    return response.json()


def save_tokens(tokens: dict):
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f, indent=2)
    print(f"\nTokens saved to {TOKEN_FILE}")


if __name__ == "__main__":
    code = get_authorization_code()
    tokens = exchange_code_for_tokens(code)
    save_tokens(tokens)
    print("\nSuccess. You now have an access token and refresh token.")
    print("Access tokens expire in ~30 min — the refresh token lets us")
    print("get new ones without repeating this browser login step.")
