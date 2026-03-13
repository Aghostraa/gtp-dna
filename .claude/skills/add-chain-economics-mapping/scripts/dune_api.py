"""
Run a Dune Analytics query and return results as JSON.

Used by the add-chain-economics-mapping skill to verify settlement transactions
for candidate addresses extracted from L2Beat before writing to economics_mapping.yml.

Default query (6819777) returns transaction breakdown by function, from/to address
and date range — ideal for identifying which methods and addresses are relevant
for the economics mapping.

Usage:
    python dune_api.py --query-id 6819777 --to-address 0xABC... --from-address all --from-date 2024-01-01
    python dune_api.py --query-id 6819777 --to-address all --from-address 0xDEF... --from-date 2024-01-01

Environment:
    DUNE_API_KEY  — Dune Analytics API key (required)

Output (JSON to stdout):
    {
        "query_id": 6819777,
        "params": {"to_address": "0x...", "from_address": "all", "from_date": "2024-01-01"},
        "rows": [
            {
                "function": "0x3e5aa082",
                "to": "0x...",
                "from": "0x...",
                "first_used": "2024-03-14T10:00:00",
                "last_used": "2025-01-01T00:00:00",
                "no_of_trx": 12345,
                "avg_data_length": 420.5,
                "tx_type": 3
            },
            ...
        ],
        "row_count": 5
    }
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

logging.getLogger("dune_client").setLevel(logging.WARNING)


def load_dotenv():
    """Load .env file from repo root into os.environ (does not overwrite existing vars)."""
    script_dir = Path(__file__).resolve().parent
    # Walk up from scripts/ to find a .env file
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

    # Convert to JSON-serialisable records
    rows = []
    for _, row in df.iterrows():
        record = {}
        for col, val in row.items():
            # Convert bytes/hex objects to 0x-prefixed strings
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
    parser = argparse.ArgumentParser(description="Run a Dune query and return JSON results.")
    parser.add_argument("--query-id", type=int, default=6819777,
                        help="Dune query ID (default: 6819777 — transaction breakdown by function/address)")
    parser.add_argument("--to-address", default="all",
                        help="Filter by recipient address (0x... or 'all')")
    parser.add_argument("--from-address", default="all",
                        help="Filter by sender address (0x... or 'all')")
    parser.add_argument("--from-date", default="2024-01-01",
                        help="Start date for query (YYYY-MM-DD, default: 2024-01-01)")
    parser.add_argument("--api-key",
                        help="Dune API key (defaults to DUNE_API_KEY env var)")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("DUNE_API_KEY")
    if not api_key:
        print(json.dumps({"error": "No Dune API key found. Set DUNE_API_KEY env var or pass --api-key."}))
        sys.exit(1)

    ensure_dune_client()

    params = {
        "to_address": args.to_address,
        "from_address": args.from_address,
        "from_date": args.from_date,
    }

    try:
        rows = run_query(args.query_id, params, api_key)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    result = {
        "query_id": args.query_id,
        "params": params,
        "row_count": len(rows),
        "rows": rows,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
