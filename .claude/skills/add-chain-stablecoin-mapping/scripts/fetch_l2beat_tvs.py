"""
Fetch the L2Beat TVS token list for a chain and extract stablecoin entries,
differentiating between natively tracked tokens (local L2 address available)
and bridged tokens tracked via L1 escrow (no L2 address in L2Beat).

Usage:
    python fetch_l2beat_tvs.py <aliases_l2beat>

    # Example:
    python fetch_l2beat_tvs.py arbitrum

Output (JSON to stdout):
    {
        "chain": "arbitrum",
        "native": [
            {
                "symbol": "USDT",
                "name": "Tether USD",
                "address": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
                "decimals": 6,
                "category": "stablecoin",
                "bridged_using": ["Layer Zero v2 OFT"]
            }
        ],
        "bridged_via_l1_escrow": [
            {
                "symbol": "USDC",
                "name": "USD Coin",
                "l1_token_address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                "escrow_addresses": ["0xcEe284F754E854890e311e3280b767F80797180d"],
                "decimals": 6,
                "category": "stablecoin"
            }
        ]
    }

native:
    amount.type == "totalSupply" with amount.chain == target chain.
    The address IS the local L2 token — ready to put in address_mapping.
    bridged_using is populated if the token arrived via a bridge (e.g. LayerZero OFT)
    even though it is tracked as a total supply on L2.

bridged_via_l1_escrow:
    amount.type == "balanceOfEscrow" (or a "calculation" sum of escrow balances)
    with chain == "ethereum". L2Beat tracks the L1 escrow balance.
    l1_token_address is the canonical token on Ethereum.
    No L2 address is available from L2Beat — find it via CoinGecko or block explorer.

Source JSON:
    https://raw.githubusercontent.com/l2beat/l2beat/main/packages/config/src/tvs/json/{slug}.json
"""

import json
import sys
import urllib.request
import urllib.error

STABLECOIN_SYMBOL_HINTS = {
    "usd", "usdc", "usdt", "dai", "usds", "usde", "frax", "lusd", "eusd",
    "eur", "eurc", "eurt", "eure", "euroc",
    "gbp", "chf", "aud", "jpy", "cny",
    "busd", "fdusd", "tusd", "usdp", "gusd", "usdx",
    "pyusd", "cusd", "susd", "xusd", "husd", "ousd",
    "mim", "ageur", "gho", "crvusd", "bold",
}

STABLECOIN_CATEGORIES = {"stablecoin", "stablecoins"}


def is_stablecoin_by_symbol(symbol: str) -> bool:
    s = symbol.lower()
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
        if e.code == 404:
            raise FileNotFoundError(f"404 Not Found: {url}")
        raise


def get_bridge_names(token: dict) -> list[str]:
    """Extract bridge names from bridgedUsing field."""
    bridged_using = token.get("bridgedUsing") or {}
    bridges = bridged_using.get("bridges") or []
    return [b["name"] for b in bridges if b.get("name")]


def collect_escrow_info(arguments: list[dict]) -> tuple[str | None, list[str], int | None]:
    """
    From a list of balanceOfEscrow arguments, collect:
    - l1_token_address (should be the same across arguments)
    - escrow_addresses (unique list)
    - decimals
    """
    l1_token_address = None
    escrow_addresses = []
    decimals = None

    for arg in arguments:
        if arg.get("type") != "balanceOfEscrow":
            continue
        if arg.get("chain") != "ethereum":
            continue
        l1_token_address = arg.get("address") or l1_token_address
        decimals = arg.get("decimals") if decimals is None else decimals
        escrow = arg.get("escrowAddress")
        if escrow and escrow not in escrow_addresses:
            escrow_addresses.append(escrow)

    return l1_token_address, escrow_addresses, decimals


def categorize_token(token: dict, target_chain: str) -> tuple[str, dict]:
    """
    Returns (category, info_dict) where category is one of:
    - "native"                 local L2 address available
    - "bridged_via_l1_escrow"  only L1 escrow info available
    - "skip"                   can't determine / irrelevant
    """
    amount = token.get("amount") or {}
    amount_type = amount.get("type")
    symbol = token.get("symbol", "")
    name = token.get("name", "")
    category = (token.get("category") or "").lower()

    if amount_type == "totalSupply":
        if amount.get("chain") == target_chain:
            return "native", {
                "symbol": symbol,
                "name": name,
                "address": amount.get("address"),
                "decimals": amount.get("decimals"),
                "category": category,
                "bridged_using": get_bridge_names(token) or None,
            }
        return "skip", {}

    if amount_type == "balanceOfEscrow":
        if amount.get("chain") == "ethereum":
            return "bridged_via_l1_escrow", {
                "symbol": symbol,
                "name": name,
                "l1_token_address": amount.get("address"),
                "escrow_addresses": [amount["escrowAddress"]] if amount.get("escrowAddress") else [],
                "decimals": amount.get("decimals"),
                "category": category,
            }
        return "skip", {}

    if amount_type == "calculation":
        arguments = amount.get("arguments") or []

        # Check if any argument is a totalSupply on the target chain
        for arg in arguments:
            if arg.get("type") == "totalSupply" and arg.get("chain") == target_chain:
                return "native", {
                    "symbol": symbol,
                    "name": name,
                    "address": arg.get("address"),
                    "decimals": arg.get("decimals"),
                    "category": category,
                    "bridged_using": get_bridge_names(token) or None,
                }

        # Otherwise check for L1 escrow arguments
        l1_token_address, escrow_addresses, decimals = collect_escrow_info(arguments)
        if escrow_addresses:
            return "bridged_via_l1_escrow", {
                "symbol": symbol,
                "name": name,
                "l1_token_address": l1_token_address,
                "escrow_addresses": escrow_addresses,
                "decimals": decimals,
                "category": category,
            }

    return "skip", {}


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: fetch_l2beat_tvs.py <aliases_l2beat>"}))
        sys.exit(1)

    slug = sys.argv[1].strip().lower()
    url = f"https://raw.githubusercontent.com/l2beat/l2beat/main/packages/config/src/tvs/json/{slug}.json"

    try:
        data = fetch_json(url)
    except FileNotFoundError:
        print(json.dumps({
            "error": (
                f"No L2Beat TVS JSON found for '{slug}'. "
                "Try the project list at: "
                "https://api.github.com/repos/l2beat/l2beat/contents/packages/config/src/tvs/json"
            )
        }))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    tokens = data.get("tokens") or []

    native = []
    bridged = []
    seen_native = set()
    seen_bridged = set()

    for token in tokens:
        symbol = token.get("symbol", "")
        category = (token.get("category") or "").lower()

        is_stable = category in STABLECOIN_CATEGORIES or is_stablecoin_by_symbol(symbol)
        if not is_stable:
            continue

        bucket, info = categorize_token(token, slug)

        if bucket == "native":
            key = (symbol.lower(), (info.get("address") or "").lower())
            if key not in seen_native:
                seen_native.add(key)
                info.pop("category", None)
                native.append(info)

        elif bucket == "bridged_via_l1_escrow":
            key = (symbol.lower(), (info.get("l1_token_address") or "").lower())
            if key not in seen_bridged:
                seen_bridged.add(key)
                info.pop("category", None)
                bridged.append(info)

    native.sort(key=lambda t: t["symbol"].upper())
    bridged.sort(key=lambda t: t["symbol"].upper())

    result = {
        "chain": slug,
        "native": native,
        "bridged_via_l1_escrow": bridged,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
