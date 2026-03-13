"""
Read chain metadata from chains/{origin_key}/main.json and output structured
info for the add-chain-economics-mapping skill.

Usage:
    python get_chain_info.py <origin_key>

Output (JSON to stdout):
    {
        "origin_key": "arbitrum",
        "name": "Arbitrum One",
        "metadata_da_layer": "Ethereum (blobs)",
        "suggested_layers": ["l1", "beacon"],
        "note": "...",
        "aliases_l2beat": "arbitrum",
        "chain_bucket": "OP Stack",
        "recommended_dune_query_id": 6819777
    }

`chain_bucket` is the raw bucket value from main.json (e.g. "OP Stack", "Elastic Chain", null).
`recommended_dune_query_id` is automatically set to 6823319 for Elastic Chain chains and
6819777 for all others. Elastic zkStack chains use query 6823319 which also returns
`chain_address` (the diamond address identifying the specific chain within the shared
zkStack contracts).


Note: `aliases_l2beat` is the correct identifier to use when looking up a chain in the
L2Beat GitHub repository (packages/config/src/projects/<aliases_l2beat>/). It is NOT
always the same as `aliases_l2beat_slug` — e.g. for Derive: aliases_l2beat='lyra',
slug='derive'. Always use `aliases_l2beat` for the GitHub path.
"""

import json
import sys
from pathlib import Path

# DA layer string → suggested economics mapping fee layers
DA_LAYER_MAP = {
    "ethereum (blobs)":     {"layers": ["l1", "beacon"], "note": "Uses calldata/blobs on L1 and beacon chain."},
    "ethereum blobs":       {"layers": ["l1", "beacon"], "note": "Uses calldata/blobs on L1 and beacon chain."},
    "ethereum (calldata)":  {"layers": ["l1"],            "note": "Posts calldata on L1 (no blobs)."},
    "celestia":             {"layers": ["celestia", "l1"],"note": "Posts blobs to Celestia; likely still settles state roots on L1."},
    "celestiablobstream":   {"layers": ["celestia", "l1"],"note": "Uses Celestia via Blobstream; likely still settles on L1."},
    "eigenda":              {"layers": ["eigenda", "l1"], "note": "Posts blobs to EigenDA; likely still settles state roots on L1."},
}

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

    da_layer = data.get("metadata_da_layer") or ""
    da_key = da_layer.lower()
    mapping = DA_LAYER_MAP.get(da_key)

    chain_bucket = data.get("bucket") or None
    is_elastic_chain = (chain_bucket or "").lower() == "elastic chain"

    result = {
        "origin_key": data.get("origin_key", origin_key),
        "name": data.get("name", ""),
        "metadata_da_layer": da_layer or None,
        "suggested_layers": mapping["layers"] if mapping else [],
        "note": mapping["note"] if mapping else (
            f"DA layer '{da_layer}' is not a standard type — "
            "manually determine which fee layers apply."
        ),
        "aliases_l2beat": data.get("aliases_l2beat") or None,
        "chain_bucket": chain_bucket,
        "recommended_dune_query_id": 6823319 if is_elastic_chain else 6819777,
    }

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
