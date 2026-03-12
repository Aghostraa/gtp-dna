"""
Fetch contract and operator addresses for a chain from L2Beat's discovered.json.

L2Beat maintains a `discovered.json` per project that captures all on-chain
contracts and EOAs found via their discovery system. This script fetches that
file and returns the data most relevant to filling in economics_mapping.yml:
  - Named contracts (to_address candidates)
  - EOAs with their permission roles (from_address candidates, e.g. sequencer/batcher)

Usage:
    python fetch_l2beat_contracts.py <l2beat_slug>

    The slug is `aliases_l2beat_slug` from main.json (e.g. "blast", "arbitrum").

Output (JSON to stdout):
    {
        "slug": "blast",
        "contracts": [
            {"name": "SystemConfig", "address": "0xABC...", "description": "..."},
            ...
        ],
        "eoas": [
            {"address": "0xDEF...", "roles": ["Sequencer", "Batcher"]},
            ...
        ],
        "note": "Run `python get_chain_info.py <origin_key>` to get the slug."
    }
"""

import json
import sys
import urllib.request
import urllib.error

GITHUB_RAW = "https://raw.githubusercontent.com/l2beat/l2beat/main"
DISCOVERED_PATH = "packages/config/src/projects/{slug}/discovered.json"


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "gtp-dna-skill/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def clean_address(addr: str) -> str:
    """Strip chain prefix like 'eth:' from L2Beat addresses."""
    return addr.split(":")[-1] if ":" in addr else addr


def extract_roles(entry: dict) -> list[str]:
    """
    Derive human-readable role labels for an EOA from its receivedPermissions.
    L2Beat permissions have an `type` field (e.g. 'sequence', 'propose', 'upgrade').
    """
    roles = []
    for perm in entry.get("receivedPermissions", []):
        ptype = perm.get("permission") or perm.get("type") or ""
        target_name = perm.get("target", {}).get("name", "") if isinstance(perm.get("target"), dict) else ""
        label = ptype.capitalize()
        if target_name:
            label += f" on {target_name}"
        if label:
            roles.append(label)
    return roles


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: fetch_l2beat_contracts.py <l2beat_slug>"}))
        sys.exit(1)

    slug = sys.argv[1].strip().lower()
    url = f"{GITHUB_RAW}/{DISCOVERED_PATH.format(slug=slug)}"

    try:
        data = fetch_json(url)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(json.dumps({
                "error": f"No discovered.json found for slug '{slug}' on L2Beat. "
                         f"Check that aliases_l2beat_slug in main.json is correct.",
                "tried_url": url,
            }))
        else:
            print(json.dumps({"error": f"HTTP {e.code} fetching {url}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    contracts = []
    eoas = []

    for entry in data.get("entries", []):
        addr = clean_address(entry.get("address", ""))
        etype = entry.get("type", "")

        if etype == "Contract":
            contracts.append({
                "name": entry.get("name", ""),
                "address": addr,
                "description": entry.get("description", "") or "",
                "proxy_type": entry.get("proxyType", ""),
            })
        elif etype == "EOA":
            roles = extract_roles(entry)
            eoas.append({
                "address": addr,
                "roles": roles,
            })

    result = {
        "slug": slug,
        "source_url": url,
        "contracts": contracts,
        "eoas": eoas,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
