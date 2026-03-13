---
name: add-chain-stablecoin-mapping
description: Add a new chain to the address_mapping in stables/stables_config_v2.py. Use this skill whenever the user wants to onboard a new chain for stablecoin tracking, a chain is missing from address_mapping, or the user says anything like "add chain", "new chain", or "onboard chain" in the context of stablecoins.
---

You are helping add a new chain's stablecoin addresses to `address_mapping` in `stables/stables_config_v2.py`.

The goal is to identify which stablecoins already in `coin_mapping` are deployed on the new chain, find their local contract addresses and decimals, and add a new entry under `address_mapping[origin_key]`.

## Step 1 — Get the origin_key and validate

Ask the user for the **origin_key** if not provided (e.g. `arbitrum`, `base`, `my_chain` — must match the key used in the `chains/` directory and in `address_mapping`).

Check whether the key **already exists** in `address_mapping` inside `stables/stables_config_v2.py`. If it does, stop and suggest the `update-stablecoin-mapping` skill instead.

## Step 2 — Load chain metadata

Run the helper script to get stablecoin-relevant aliases from the chain's `main.json`:

```bash
python .claude/skills/add-chain-stablecoin-mapping/scripts/get_chain_info.py <origin_key>
```

The script outputs JSON with:
- `name` — human-readable chain name
- `aliases_coingecko_chain` — platform key used in CoinGecko's coin API (e.g. `"arbitrum-one"`)
- `aliases_coingecko` — used for CoinGecko ecosystem page
- `aliases_defillama` — used for DeFi Llama stablecoins page
- `aliases_l2beat` — used to fetch the L2Beat TVS JSON
- `deployed_supplyreader` — date stablecoin supply reading was set up (null = not yet configured)
- `coingecko_ecosystem_url` — direct link to browse ecosystem tokens
- `defillama_stablecoins_url` — direct link to DeFi Llama stablecoins page
- `l2beat_tvs_url` — direct link to L2Beat TVS JSON
- `error` — set if the chain file was not found; stop and tell the user

Show the user the chain name and the relevant URLs. Note if `deployed_supplyreader` is null — the chain may not be fully set up for stablecoin tracking yet; mention this to the user.

## Step 3 — Discover stablecoin addresses from L2Beat

Fetch the L2Beat TVS JSON to get a preliminary list of stablecoin addresses deployed on the chain:

```bash
python .claude/skills/add-chain-stablecoin-mapping/scripts/fetch_l2beat_tvs.py <aliases_l2beat>
```

The script returns `stablecoin_candidates` — a list of tokens with `symbol`, `address`, `decimals`, and `category`. These are L2Beat's known stablecoin tokens for this chain and are a good starting point.

**If the script returns a 404 or `aliases_l2beat` is null**, try finding the correct slug by fetching:
```
https://api.github.com/repos/l2beat/l2beat/contents/packages/config/src/tvs/json
```
This returns directory entries — each has a `name` field. Match against the chain's `origin_key` or display name, then retry.

Show the user the stablecoin candidates list. For each one, note which `token_id` in `coin_mapping` it corresponds to (match by symbol). Candidates with no matching `token_id` can be skipped for now.

## Step 4 — Match against coin_mapping and cross-check addresses

Read `stables/stables_config_v2.py` and show the user the current `coin_mapping` entries. For each stablecoin candidate from Step 3:

1. **Match by symbol** to a `token_id` in `coin_mapping`.
2. **Verify the address** — L2Beat may list bridge escrow addresses rather than local token addresses. We always want the **local token address on the chain**, not the bridge contract.
   - Cross-check using CoinGecko: if `aliases_coingecko_chain` is set, the address under `coin_data["detail_platforms"][aliases_coingecko_chain]` is authoritative.
   - Use the DeFi Llama stablecoins page or the chain's block explorer to verify if needed.
   - For bridged tokens (`metric_key == "bridged"`), confirm the address is the bridged token contract on the chain, not an L1 escrow.

Tell the user which addresses you were able to verify and which need manual confirmation. Do **not** write any entries until addresses are confirmed.

## Step 5 — Confirm entries with user

Show the user the proposed `address_mapping` block for this chain:

```python
"<origin_key>": {
    "<token_id>": {
        "address": "0x...",
        "decimals": 6
    },
    ...
}
```

Ask the user to:
- Confirm or correct addresses and decimals
- Identify any stablecoins present on the chain that are missing from the list
- Decide whether to skip any tokens that have negligible liquidity or are not yet live

Note any tokens from `coin_mapping` that have a `coingecko_id` but **no** matching address found for this chain — list them explicitly so the user is aware.

## Step 6 — Write the entry

Insert the confirmed block into `address_mapping` in `stables/stables_config_v2.py`. Add it in alphabetical order by `origin_key` among the existing entries, or at the end if that is cleaner. Preserve the existing formatting (4-space indent, lowercase addresses).

Do **not** modify `coin_mapping` — that is handled by the `update-stablecoin-mapping` skill.

## Step 7 — Done

After writing, confirm success and remind the user:
- If `deployed_supplyreader` was null, the chain still needs to be configured in the backend before supply data will be collected.
- If `aliases_coingecko_chain` is missing from the chain's `main.json`, the semi-automated CoinGecko update script (described in `stables/stables_README.md`) won't be able to auto-discover future tokens for this chain.
- Open a PR if this is a community contribution.
