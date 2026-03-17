#!/usr/bin/env python3
"""
Search the growthepie projects directory (based on the OSO-directory) for owner_project slugs.

Usage:
    python fetch_owner_project.py <keyword1> [keyword2 ...]

Example:
    python fetch_owner_project.py lumi luausd
    python fetch_owner_project.py circle usdc

Returns JSON with matching projects from https://api.growthepie.com/v1/labels/projects.json.
Matching is case-insensitive and checks the slug, display_name, and description fields.
"""

import json
import sys
import urllib.request


API_URL = "https://api.growthepie.com/v1/labels/projects.json"


def fetch_projects():
    with urllib.request.urlopen(API_URL, timeout=15) as resp:
        return json.loads(resp.read())


def search(data, keywords):
    types = data["types"]
    rows = data["data"]

    slug_idx = types.index("owner_project")
    name_idx = types.index("display_name")
    desc_idx = types.index("description")

    keywords_lower = [kw.lower() for kw in keywords]
    matches = []

    for row in rows:
        slug = (row[slug_idx] or "").lower()
        name = (row[name_idx] or "").lower()
        desc = (row[desc_idx] or "").lower()
        searchable = f"{slug} {name} {desc}"

        if all(kw in searchable for kw in keywords_lower):
            matches.append({
                "owner_project": row[slug_idx],
                "display_name": row[name_idx],
                "description": row[desc_idx],
            })

    return matches


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: fetch_owner_project.py <keyword1> [keyword2 ...]"}))
        sys.exit(1)

    keywords = sys.argv[1:]

    try:
        data = fetch_projects()
    except Exception as e:
        print(json.dumps({"error": f"Failed to fetch projects: {e}"}))
        sys.exit(1)

    if not (isinstance(data, dict) and "data" in data):
        print(json.dumps({"error": "Unexpected API response structure"}))
        sys.exit(1)

    results = search(data["data"], keywords)

    output = {
        "keywords": keywords,
        "matches": results,
        "total_matches": len(results),
    }
    if not results:
        output["note"] = (
            "No matches found. Set owner_project to null and ask the user to supply "
            "the correct slug from https://api.growthepie.com/v1/labels/projects.json"
        )

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
