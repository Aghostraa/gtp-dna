"""
Read chain metadata from chains/{origin_key}/main.json and output structured
info relevant for stablecoin mapping.

Usage:
    python get_chain_info.py <origin_key>

Output (JSON to stdout):
    {
        "origin_key": "arbitrum",
        "name": "Arbitrum One",
        "evm_chain_id": 42161,
        "aliases_coingecko_chain": "arbitrum-one",
        "aliases_coingecko": "arbitrum",
        "aliases_defillama": "arbitrum",
        "aliases_l2beat": "arbitrum",
        "deployed_supplyreader": "2025-09-23",
        "coingecko_ecosystem_url": "https://www.coingecko.com/en/categories/arbitrum-ecosystem",
        "defillama_stablecoins_url": "https://defillama.com/stablecoins/arbitrum",
        "l2beat_tvs_url": "https://raw.githubusercontent.com/l2beat/l2beat/main/packages/config/src/tvs/json/arbitrum.json"
    }

`aliases_coingecko_chain` is the platform key used in CoinGecko's coin detail API
(e.g. coin_data["platforms"]["arbitrum-one"]).

`deployed_supplyreader` indicates when stablecoin supply reading was set up for this
chain — null means it hasn't been configured yet.
"""

import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: get_chain_info.py <origin_key>"}))
        sys.exit(1)

    origin_key = sys.argv[1].strip().lower()

    # Resolve path relative to repo root (two levels up from this script)
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parents[3]  # scripts/ -> add-chain-.../ -> skills/ -> .claude/ -> repo root
    chain_file = repo_root / "chains" / origin_key / "main.json"

    if not chain_file.exists():
        print(json.dumps({"error": f"No chain file found at {chain_file}"}))
        sys.exit(1)

    with open(chain_file) as f:
        data = json.load(f)

    aliases_coingecko_chain = data.get("aliases_coingecko_chain") or None
    aliases_coingecko = data.get("aliases_coingecko") or None
    aliases_defillama = data.get("aliases_defillama") or None
    aliases_l2beat = data.get("aliases_l2beat") or None
    evm_chain_id = data.get("evm_chain_id") or None
    deployed_supplyreader = data.get("deployed_supplyreader") or None

    result = {
        "origin_key": data.get("origin_key", origin_key),
        "name": data.get("name", ""),
        "evm_chain_id": evm_chain_id,
        "aliases_coingecko_chain": aliases_coingecko_chain,
        "aliases_coingecko": aliases_coingecko,
        "aliases_defillama": aliases_defillama,
        "aliases_l2beat": aliases_l2beat,
        "deployed_supplyreader": deployed_supplyreader,
        "coingecko_ecosystem_url": (
            f"https://www.coingecko.com/en/categories/{aliases_coingecko}-ecosystem"
            if aliases_coingecko else None
        ),
        "defillama_stablecoins_url": (
            f"https://defillama.com/stablecoins/{aliases_defillama}"
            if aliases_defillama else None
        ),
        "l2beat_tvs_url": (
            f"https://raw.githubusercontent.com/l2beat/l2beat/main/packages/config/src/tvs/json/{aliases_l2beat}.json"
            if aliases_l2beat else None
        ),
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
