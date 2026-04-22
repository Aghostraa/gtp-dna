"""
Parse stables/stables_config_v2.py and output the line ranges for each chain
block inside address_mapping. Useful for knowing exactly where to insert a new
token entry without reading the whole file.

Usage:
    # List all chains with their line ranges
    python get_address_mapping_lines.py

    # Show line range for a specific chain
    python get_address_mapping_lines.py polygon_pos

Output (JSON to stdout):
    {
        "polygon_pos": {
            "block_start": 2714,   # line with "polygon_pos": {
            "last_entry_end": 3483, # last line of the last token entry (before closing })
            "block_end": 3484      # line with closing },
        },
        ...
    }
"""

import json
import re
import sys
from pathlib import Path


def parse_address_mapping_lines(config_path: Path) -> dict:
    lines = config_path.read_text().splitlines()

    # Find the start of address_mapping
    mapping_start = None
    for i, line in enumerate(lines):
        if re.match(r"^address_mapping\s*=\s*\{", line):
            mapping_start = i
            break

    if mapping_start is None:
        return {}

    # Walk through lines inside address_mapping to find chain blocks
    # A chain block starts with:  "    \"<chain_key>\": {"
    # and ends with:              "    },"  or  "    }"
    chain_pattern = re.compile(r'^    "([^"]+)":\s*\{')
    close_pattern = re.compile(r'^    \}')

    chains = {}
    current_chain = None
    current_chain_start = None
    depth = 0  # depth inside address_mapping (1 = chain level, 2 = token level)

    i = mapping_start
    # skip the address_mapping = { line itself (depth 0 → 1)
    depth = 1
    i += 1

    while i < len(lines):
        line = lines[i]

        # Detect chain-level open:  "    "<chain>": {"
        m = chain_pattern.match(line)
        if m and depth == 1:
            current_chain = m.group(1)
            current_chain_start = i + 1  # 1-based line number
            depth = 2
            i += 1
            continue

        # Detect chain-level close:  "    }," or "    }" (at depth 2 back to 1)
        if close_pattern.match(line) and depth == 2:
            if current_chain is not None:
                # last_entry_end: the line just before this closing brace
                last_entry_end = i  # 1-based: this closing line is i+1, so entry ends at i
                chains[current_chain] = {
                    "block_start": current_chain_start,
                    "last_entry_end": last_entry_end,  # 1-based line of last content line
                    "block_end": i + 1,                # 1-based line of the closing }
                }
            current_chain = None
            current_chain_start = None
            depth = 1
            i += 1
            continue

        # Detect end of address_mapping itself: "}" at depth 1
        if re.match(r"^\}", line) and depth == 1:
            break

        i += 1

    return chains


def main():
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parents[3]  # scripts/ -> update-.../ -> skills/ -> .claude/ -> repo root
    config_path = repo_root / "stables" / "stables_config_v2.py"

    if not config_path.exists():
        print(json.dumps({"error": f"Config file not found: {config_path}"}))
        sys.exit(1)

    chains = parse_address_mapping_lines(config_path)

    if len(sys.argv) == 2:
        key = sys.argv[1].strip()
        if key not in chains:
            print(json.dumps({"error": f"Chain '{key}' not found in address_mapping. Known chains: {list(chains.keys())}"}))
            sys.exit(1)
        print(json.dumps({key: chains[key]}, indent=2))
    else:
        print(json.dumps(chains, indent=2))


if __name__ == "__main__":
    main()
