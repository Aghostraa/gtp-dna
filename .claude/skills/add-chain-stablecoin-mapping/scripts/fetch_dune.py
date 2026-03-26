"""
Fetch stablecoin data from Dune Analytics query 6910797.

Parameters are optional — omitting one returns all rows for that dimension.

Usage:
    python fetch_dune.py --chain ethereum         # all symbols on ethereum
    python fetch_dune.py --symbol USDC            # USDC across all chains
    python fetch_dune.py --chain base --symbol USDT

Arguments:
    --chain   Dune chain identifier (e.g. "ethereum", "base", "arbitrum")
    --symbol  Token symbol to filter (e.g. "USDC", "USDT")

Environment:
    DUNE_API_KEY  — Dune Analytics API key (required)

Output (JSON to stdout):
    {
        "query_id": 6910797,
        "params": {"chain": "base", "symbol": "all"},
        "row_count": 3,
        "rows": [
            {
                "chain": "base",
                "symbol": "USDC",
                "address": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
                "decimals": 6,
                ...
            },
            ...
        ]
    }
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

QUERY_ID = 6910797

logging.getLogger("dune_client").setLevel(logging.WARNING)


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


def ensure_dune_client():
    try:
        import dune_client  # noqa: F401
    except ImportError:
        import subprocess
        print("Installing dune-client...", file=sys.stderr)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "dune-client", "-q"])


def run_query(query_id: int, params: dict, api_key: str) -> list[dict]:
    from dune_client.client import DuneClient
    from dune_client.query import QueryBase
    from dune_client.types import QueryParameter

    client = DuneClient(api_key)
    query = QueryBase(name=f"query_{query_id}", query_id=query_id)
    query.params = [QueryParameter.text_type(name=k, value=str(v)) for k, v in params.items()]

    df = client.refresh_into_dataframe(query)

    rows = []
    for _, row in df.iterrows():
        record = {}
        for col, val in row.items():
            if isinstance(val, (bytes, bytearray)):
                record[col] = "0x" + val.hex()
            elif hasattr(val, "isoformat"):  # datetime
                record[col] = val.isoformat()
            elif val != val:  # NaN
                record[col] = None
            else:
                record[col] = val
        rows.append(record)

    return rows


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Fetch stablecoins from Dune query 6910797 by chain and/or symbol."
    )
    parser.add_argument(
        "--chain",
        default="all",
        help="Dune chain identifier (e.g. 'ethereum', 'base'). Omit for all chains.",
    )
    parser.add_argument(
        "--symbol",
        default="all",
        help="Token symbol to filter (e.g. 'USDC'). Omit for all symbols.",
    )
    parser.add_argument(
        "--api-key",
        help="Dune API key (defaults to DUNE_API_KEY env var)",
    )
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("DUNE_API_KEY")
    if not api_key:
        print(json.dumps({
            "error": "No Dune API key found. Set DUNE_API_KEY env var or pass --api-key."
        }))
        sys.exit(1)

    ensure_dune_client()

    params = {
        "chain": args.chain,
        "symbol": args.symbol,
    }

    print(f"[info] running query {QUERY_ID} with params: {params}", file=sys.stderr)

    try:
        rows = run_query(QUERY_ID, params, api_key)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    result = {
        "query_id": QUERY_ID,
        "params": params,
        "row_count": len(rows),
        "rows": rows,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
