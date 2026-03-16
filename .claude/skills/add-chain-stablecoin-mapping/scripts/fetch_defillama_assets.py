"""
Fetch DefiLlama coreAssets.json and extract stablecoin addresses for a chain.

Usage:
    python fetch_defillama_assets.py <aliases_defillama>

    # Example:
    python fetch_defillama_assets.py arbitrum

Output (JSON to stdout):
    {
        "chain": "arbitrum",
        "stablecoins": [
            {
                "symbol": "USDC",
                "address": "0xff970a61a04b1ca14834a43f5de4533ebddb5cc8"
            },
            {
                "symbol": "USDC_CIRCLE",
                "address": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
            },
            ...
        ]
    }

Source:
    https://raw.githubusercontent.com/DefiLlama/DefiLlama-Adapters/main/projects/helper/coreAssets.json
"""

import json
import sys
import urllib.request
import urllib.error

COREАСSETS_URL = (
    "https://raw.githubusercontent.com/DefiLlama/DefiLlama-Adapters/main"
    "/projects/helper/coreAssets.json"
)

STABLECOIN_SYMBOL_HINTS = {
    "usd", "usdc", "usdt", "dai", "usds", "usde", "frax", "lusd", "eusd",
    "eur", "eurc", "eurt", "eure", "euroc",
    "gbp", "chf", "aud", "jpy",
    "busd", "fdusd", "tusd", "usdp", "gusd", "usdx",
    "pyusd", "cusd", "susd", "xusd", "husd", "ousd",
    "mim", "ageur", "gho", "crvusd", "bold", "usdm",
    "nusd", "fusd", "musd",
}

NON_STABLE_OVERRIDES = {
    # symbols that contain stablecoin hints but are NOT stablecoins
    "susd_old",  # old sUSD — still fine to keep actually
}


def is_stablecoin_by_symbol(symbol: str) -> bool:
    s = symbol.lower()
    if s in NON_STABLE_OVERRIDES:
        return False
    if s in STABLECOIN_SYMBOL_HINTS:
        return True
    for hint in STABLECOIN_SYMBOL_HINTS:
        if hint in s:
            return True
    return False


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "gtp-dna/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {url}")


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: fetch_defillama_assets.py <aliases_defillama>"}))
        sys.exit(1)

    chain_slug = sys.argv[1].strip().lower().replace("-", "_")

    try:
        data = fetch_json(COREАСSETS_URL)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    chain_assets = data.get(chain_slug)
    if chain_assets is None:
        available = sorted(k for k in data if isinstance(data[k], dict))
        print(json.dumps({
            "error": (
                f"Chain '{chain_slug}' not found in coreAssets.json. "
                f"Available chains ({len(available)}): {available[:30]} ..."
            )
        }))
        sys.exit(1)

    stablecoins = []
    for symbol, address in chain_assets.items():
        if not isinstance(address, str):
            continue
        if is_stablecoin_by_symbol(symbol):
            stablecoins.append({
                "symbol": symbol,
                "address": address,
            })

    stablecoins.sort(key=lambda t: t["symbol"].upper())

    print(json.dumps({"chain": chain_slug, "stablecoins": stablecoins}, indent=2))


if __name__ == "__main__":
    main()
