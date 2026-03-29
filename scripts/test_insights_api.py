#!/usr/bin/env python3
"""
Test script to verify Instagram Insights API works with session cookies.

Usage:
    python scripts/test_insights_api.py <media_pk>
    python scripts/test_insights_api.py  # Uses first post from the DB

Fetches insights for a single post and prints the parsed data.
Requires INSTAGRAM_SESSION_ID and INSTAGRAM_CSRF_TOKEN in .env.
"""
import json
import os
import sys
from pathlib import Path

import httpx

# Load .env
PROJECT_ROOT = Path(__file__).parent.parent
for line in (PROJECT_ROOT / ".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())

SESSION_ID = os.environ.get("INSTAGRAM_SESSION_ID", "")
CSRF_TOKEN = os.environ.get("INSTAGRAM_CSRF_TOKEN", "")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "admin123")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8001")
IG_APP_ID = "936619743392459"


def get_cookies():
    return {
        "sessionid": SESSION_ID,
        "csrftoken": CSRF_TOKEN,
        "ds_user_id": SESSION_ID.split("%3A")[0] if "%3A" in SESSION_ID else "",
    }


def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "X-CSRFToken": CSRF_TOKEN,
        "X-IG-App-ID": IG_APP_ID,
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "*/*",
        "Referer": "https://www.instagram.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }


def fetch_insights(media_pk: str) -> dict | None:
    """Fetch insights for a specific media post."""
    url = f"https://www.instagram.com/api/v1/insights/media_organic_insights/{media_pk}/"
    r = httpx.get(
        url,
        params={"ig_filters": "{}"},
        headers=get_headers(),
        cookies=get_cookies(),
        timeout=15,
        follow_redirects=True,
    )
    print(f"\nHTTP {r.status_code} for {url}")

    if r.status_code != 200:
        print(f"Error: {r.text[:500]}")
        return None

    return r.json()


def get_first_post_pk() -> str | None:
    """Get the first post's platform_post_id from the backend."""
    r = httpx.get(
        f"{BACKEND_URL}/api/accounts",
        headers={"X-App-Password": APP_PASSWORD},
    )
    if r.status_code != 200:
        print(f"Backend error: {r.status_code}")
        return None

    accounts = r.json()
    ig_accounts = [a for a in accounts if a["platform"] == "instagram"]
    if not ig_accounts:
        print("No Instagram accounts found")
        return None

    account_id = ig_accounts[0]["id"]
    r = httpx.get(
        f"{BACKEND_URL}/api/accounts/{account_id}/posts",
        headers={"X-App-Password": APP_PASSWORD},
        params={"limit": 1},
    )
    posts = r.json()
    if not posts:
        print("No posts found")
        return None

    return posts[0].get("platform_post_id")


def main():
    if not SESSION_ID or not CSRF_TOKEN:
        print("ERROR: Set INSTAGRAM_SESSION_ID and INSTAGRAM_CSRF_TOKEN in .env")
        sys.exit(1)

    # Get media PK
    if len(sys.argv) > 1:
        media_pk = sys.argv[1]
    else:
        print("No media_pk provided, fetching first post from backend...")
        media_pk = get_first_post_pk()
        if not media_pk:
            print("Could not find a post to test with")
            sys.exit(1)

    print(f"\nTesting insights for media_pk={media_pk}")

    # Fetch raw response
    raw = fetch_insights(media_pk)
    if not raw:
        print("No insights data returned")
        sys.exit(1)

    print("\n=== RAW RESPONSE ===")
    print(json.dumps(raw, indent=2)[:3000])

    # Parse using the same logic as the scraper
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    from ig_sync import parse_insights_response
    parsed = parse_insights_response(raw)

    if parsed:
        print("\n=== PARSED INSIGHTS ===")
        print(json.dumps(parsed, indent=2))
    else:
        print("\nParsing returned None — no meaningful data extracted")


if __name__ == "__main__":
    main()
