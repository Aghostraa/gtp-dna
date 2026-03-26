"""
Fetch stablecoin addresses for a chain by querying the CoinGecko ecosystem
category and then looking up each stablecoin's contract address on the chain.

Usage:
    python fetch_coingecko_ecosystem.py <aliases_coingecko_chain>

    # Example:
    python fetch_coingecko_ecosystem.py arbitrum-one
    python fetch_coingecko_ecosystem.py plume-network

Arguments:
    aliases_coingecko_chain  CoinGecko platform key (e.g. "arbitrum-one").
                             The ecosystem category is derived by appending "-ecosystem"
                             (e.g. "plume-network" → "plume-network-ecosystem").

Output (JSON to stdout):
    {
        "category": "arbitrum-ecosystem",
        "platform": "arbitrum-one",
        "stablecoins": [
            {
                "symbol": "USDC",
                "name": "USD Coin",
                "coingecko_id": "usd-coin",
                "address": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
                "decimals": 6,
                "price_usd": 1.0,
                "logo": "https://assets.coingecko.com/coins/images/6319/large/usdc.png"
            },
            ...
        ]
    }

Notes:
- Set COINGECKO_API_KEY env var to use the Pro API and skip rate limiting.
- The category endpoint returns up to 250 coins per page; stablecoins are
  filtered by symbol heuristics.
- `no_address_found` lists stablecoins where CoinGecko has no contract address
  for the requested platform — verify manually via block explorer.
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

STABLECOIN_SYMBOL_HINTS = {
    "usd", "usdc", "usdt", "dai", "usds", "usde", "frax", "lusd", "eusd",
    "eur", "eurc", "eurt", "eure", "euroc",
    "gbp", "chf", "aud", "jpy",
    "busd", "fdusd", "tusd", "usdp", "gusd", "usdx",
    "pyusd", "cusd", "susd", "xusd", "husd", "ousd",
    "mim", "ageur", "gho", "crvusd", "bold", "usdm",
    "nusd", "fusd", "musd",
}

# Symbols that contain stablecoin hints but are NOT stablecoins
NON_STABLE_OVERRIDES = {
    "wusdm",  # wrapped yield token, not a stablecoin
}

# Minimum market cap (USD) to bother looking up — filters noise/dead tokens.
# Uses global market cap from CoinGecko markets endpoint (not chain-specific).
# For stablecoin tracking we only care about tokens with meaningful supply.
# Set to 0 to disable (not recommended on free tier — too many API calls).
MIN_MARKET_CAP = 1_000_000


def is_stablecoin_by_symbol(symbol: str) -> bool:
    s = symbol.lower()
    if s in NON_STABLE_OVERRIDES:
        return False
    for hint in STABLECOIN_SYMBOL_HINTS:
        if hint in s:
            return True
    return False


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


def fetch_ecosystem_coins(category: str) -> list[dict]:
    """Return all coins in the CoinGecko category, up to 250."""
    params = urlencode({
        "vs_currency": "usd",
        "category": category,
        "order": "market_cap_desc",
        "per_page": 250,
        "page": 1,
        "sparkline": "false",
    })
    url = f"{base_url()}/coins/markets?{params}"
    return fetch_json(url)


def fetch_coin_detail(coin_id: str) -> dict:
    """Return coin detail including detail_platforms for contract addresses."""
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
        print(json.dumps({
            "error": "Usage: fetch_coingecko_ecosystem.py <aliases_coingecko_chain>"
        }))
        sys.exit(1)

    aliases_coingecko_chain = sys.argv[1].strip().lower()
    category = f"{aliases_coingecko_chain}-ecosystem"

    print(f"[info] fetching category: {category}", file=sys.stderr)

    try:
        coins = fetch_ecosystem_coins(category)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(json.dumps({
                "error": (
                    f"CoinGecko category '{category}' not found. "
                    "Try browsing https://www.coingecko.com/en/categories to find the right slug."
                )
            }))
            sys.exit(1)
        raise

    if not isinstance(coins, list):
        print(json.dumps({"error": f"Unexpected response: {coins}"}))
        sys.exit(1)

    # Filter to stablecoins by symbol, optionally by min market cap
    stablecoin_candidates = [
        c for c in coins
        if is_stablecoin_by_symbol(c.get("symbol", ""))
        and (MIN_MARKET_CAP == 0 or (c.get("market_cap") or 0) >= MIN_MARKET_CAP)
    ]

    print(
        f"[info] {len(coins)} coins in category, "
        f"{len(stablecoin_candidates)} stablecoin candidates "
        f"(market_cap >= ${MIN_MARKET_CAP:,})",
        file=sys.stderr,
    )

    stablecoins = []

    for coin in stablecoin_candidates:
        coin_id = coin["id"]
        symbol = coin.get("symbol", "").upper()
        name = coin.get("name", "")
        price = coin.get("current_price")

        print(f"[info] looking up {symbol} ({coin_id})", file=sys.stderr)

        try:
            detail = fetch_coin_detail(coin_id)
        except Exception as e:
            print(f"[warn] could not fetch {coin_id}: {e}", file=sys.stderr)
            continue

        platforms = detail.get("detail_platforms") or {}
        platform_data = platforms.get(aliases_coingecko_chain)

        if platform_data and platform_data.get("contract_address"):
            stablecoins.append({
                "symbol": symbol,
                "name": name,
                "coingecko_id": coin_id,
                "address": platform_data["contract_address"],
                "decimals": platform_data.get("decimal_place"),
                "price_usd": price,
                "logo": coin.get("image"),
            })

    stablecoins.sort(key=lambda t: t["symbol"].upper())

    print(json.dumps({
        "category": category,
        "platform": aliases_coingecko_chain,
        "stablecoins": stablecoins,
    }, indent=2))


if __name__ == "__main__":
    main()
