"""
Fetch a token's deployment addresses across all chains from CoinGecko.

Usage:
    python fetch_coingecko_token.py <coingecko_id>

    # Examples:
    python fetch_coingecko_token.py usd-coin
    python fetch_coingecko_token.py frax-usd
    python fetch_coingecko_token.py lumi-finance-luausd

Output (JSON to stdout):
    {
        "coingecko_id": "usd-coin",
        "symbol": "USDC",
        "name": "USD Coin",
        "logo": "https://...",
        "deployments": [
            {
                "platform": "ethereum",
                "address": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
                "decimals": 6
            },
            {
                "platform": "arbitrum-one",
                "address": "0xaf88d065e77c8cc2239327c5edb3a432268e5831",
                "decimals": 6
            },
            ...
        ]
    }

The `platform` field matches the `aliases_coingecko_chain` values in chains/*/main.json.
Use `get_chain_info.py <origin_key>` to look up which platform key maps to which chain.

Notes:
- Set COINGECKO_API_KEY env var to use the Pro API.
- Only platforms with a non-empty contract_address are included.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urlencode


def load_dotenv():
    """Load .env file from repo root into os.environ (does not overwrite existing vars)."""
    script_dir = Path(__file__).resolve().parent
    for parent in [script_dir, *script_dir.parents]:
        env_file = parent / ".env"
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value
            break


load_dotenv()


def make_headers() -> dict:
    api_key = os.environ.get("COINGECKO_API_KEY")
    headers = {"User-Agent": "gtp-dna/1.0", "Accept": "application/json"}
    if api_key:
        headers["x-cg-pro-api-key"] = api_key
    return headers


def base_url() -> str:
    if os.environ.get("COINGECKO_API_KEY"):
        return "https://pro-api.coingecko.com/api/v3"
    return "https://api.coingecko.com/api/v3"


def fetch_json(url: str, retries: int = 4) -> dict | list:
    headers = make_headers()
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 15 * (2 ** attempt)  # 15s, 30s, 60s, 120s
                print(f"[rate limit] waiting {wait}s ...", file=sys.stderr)
                time.sleep(wait)
                continue
            raise
    raise RuntimeError(f"Failed after {retries} attempts: {url}")


def fetch_coin_detail(coin_id: str) -> dict:
    params = urlencode({
        "localization": "false",
        "tickers": "false",
        "market_data": "false",
        "community_data": "false",
        "developer_data": "false",
        "sparkline": "false",
    })
    url = f"{base_url()}/coins/{coin_id}?{params}"
    return fetch_json(url)


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: fetch_coingecko_token.py <coingecko_id>"}))
        sys.exit(1)

    coin_id = sys.argv[1].strip().lower()
    print(f"[info] fetching coin detail for: {coin_id}", file=sys.stderr)

    try:
        detail = fetch_coin_detail(coin_id)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(json.dumps({
                "error": f"CoinGecko coin '{coin_id}' not found. Check the ID at https://www.coingecko.com"
            }))
            sys.exit(1)
        raise

    symbol = (detail.get("symbol") or "").upper()
    name = detail.get("name") or ""
    logo = (detail.get("image") or {}).get("large")

    platforms = detail.get("detail_platforms") or {}
    deployments = []
    for platform, data in sorted(platforms.items()):
        address = (data or {}).get("contract_address") or ""
        decimals = (data or {}).get("decimal_place")
        if address:
            deployments.append({
                "platform": platform,
                "address": address.lower(),
                "decimals": decimals,
            })

    print(f"[info] found {len(deployments)} deployments across platforms", file=sys.stderr)

    print(json.dumps({
        "coingecko_id": coin_id,
        "symbol": symbol,
        "name": name,
        "logo": logo,
        "deployments": deployments,
    }, indent=2))


if __name__ == "__main__":
    main()
