"""
Fetch active EigenDA namespaces and show which are not yet in economics_mapping.yml.

Usage:
    python fetch_eigenda_namespaces.py
    python fetch_eigenda_namespaces.py --unmapped-only

Output (JSON to stdout):
    {
        "date": "2026-03-13",
        "namespaces": [
            {"account_name": "Foo", "customer_id": "0x...", "version": 1, "blob_count": 123},
            ...
        ],
        "unmapped": [
            {"account_name": "Bar", "customer_id": "0x...", "version": 1, "blob_count": 456},
            ...
        ]
    }
"""

import argparse
import json
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path


ENDPOINT = "https://eigenda-mainnet-ethereum-blobmetadata-usage.s3.us-east-2.amazonaws.com/v2/stats"
MAPPING_URL = "https://raw.githubusercontent.com/growthepie/gtp-dna/refs/heads/main/economics_da/economics_mapping.yml"


def fetch_day(target_date: date) -> list[dict]:
    url = f"{ENDPOINT}/{target_date}.json"
    req = urllib.request.Request(url, headers={"User-Agent": "gtp-dna-skill/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return [json.loads(line) for line in resp.read().decode().strip().split("\n")]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def get_mapped_namespaces() -> set[str]:
    """Load namespaces already in economics_mapping.yml (eigenda section)."""
    try:
        import yaml
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml", "-q"])
        import yaml

    # Try local file first, fall back to remote
    script_dir = Path(__file__).resolve().parent
    for parent in [script_dir, *script_dir.parents]:
        local = parent / "economics_da" / "economics_mapping.yml"
        if local.exists():
            with open(local) as f:
                data = yaml.safe_load(f)
            break
    else:
        req = urllib.request.Request(MAPPING_URL, headers={"User-Agent": "gtp-dna-skill/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = yaml.safe_load(resp.read().decode())

    namespaces = set()
    for chain in data.values():
        for entry in chain.get("eigenda") or []:
            ns = entry.get("namespace")
            if ns:
                namespaces.add(str(ns).lower())
    return namespaces


def main():
    parser = argparse.ArgumentParser(description="List active EigenDA namespaces.")
    parser.add_argument("--unmapped-only", action="store_true",
                        help="Only show namespaces not yet in economics_mapping.yml")
    args = parser.parse_args()

    # Try today, fall back to yesterday (today's file may not exist yet)
    today = date.today()
    rows = fetch_day(today)
    if rows is None:
        today = today - timedelta(days=1)
        rows = fetch_day(today)
    if rows is None:
        print(json.dumps({"error": "Could not fetch EigenDA data for today or yesterday"}))
        sys.exit(1)

    # Group by account_name + customer_id + version
    groups: dict[tuple, dict] = {}
    for row in rows:
        key = (row.get("account_name", ""), row.get("customer_id", ""), row.get("version", 0))
        if key not in groups:
            groups[key] = {"account_name": key[0], "customer_id": key[1], "version": key[2], "blob_count": 0}
        groups[key]["blob_count"] += row.get("blob_count", 0)

    namespaces = sorted(groups.values(), key=lambda r: r["blob_count"], reverse=True)

    mapped = get_mapped_namespaces()
    unmapped = [r for r in namespaces if str(r["customer_id"]).lower() not in mapped]

    result = {
        "date": str(today),
        "total_namespaces": len(namespaces),
        "unmapped_count": len(unmapped),
    }
    if args.unmapped_only:
        result["unmapped"] = unmapped
    else:
        result["namespaces"] = namespaces
        result["unmapped"] = unmapped

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
