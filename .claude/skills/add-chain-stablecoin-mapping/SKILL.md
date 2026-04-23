---
name: add-chain-stablecoin-mapping
description: Add a new chain to the address_mapping in stables/stables_config_v2.py. Use this skill whenever the user wants to onboard a new chain for stablecoin tracking, a chain is missing from address_mapping, or the user says anything like "add chain", "new chain", or "onboard chain" in the context of stablecoins.
---

You are helping add a new chain's stablecoin addresses to `address_mapping` in `stables/stables_config_v2.py`.

The goal is to identify which stablecoins already in `coin_mapping` are deployed on the new chain, find their contract addresses and decimals, and add a new entry under `address_mapping[origin_key]`.

## Tracking modes

There are two ways to track stablecoin supply for a chain. Ask the user which they want, or recommend based on the chain's architecture:

### Option A — Direct tracking (recommended)

Calls `totalSupply()` directly on each stablecoin contract deployed on the L2. Requires knowing the local token address on the chain.

```python
"<origin_key>": {
    "<token_id>": {
        "address": "0x...",
        "decimals": 6
    },
    ...
}
```

Use this whenever the chain has EVM-compatible contracts and a working RPC. This is the preferred approach.

### Option B — `track_on_l1` (not recommended)

Instead of reading supply on the L2, this sums the balances held in L1 Ethereum bridge escrow contracts. Only works for **lock-and-mint canonical bridges** — tokens that are minted on L2 only when ETH-side tokens are locked in an escrow.

```python
"<origin_key>": {
    "track_on_l1": [
        "0x674bdf20A0F284D710BC40872100128e2d66Bd3f",
        "0xD97D09f3bd931a14382ac60f156C1285a56Bb51B"
    ]
}
```

The list contains the L1 escrow/bridge contract addresses (not token addresses). The backend sums all ERC-20 balances held by these contracts on Ethereum to estimate total stablecoin supply locked on the L2.

**Limitations:** misses natively issued stablecoins (USDC via CCTP, USDe, etc.), third-party bridges, and any token not routed through the canonical bridge. Only use this for chains where direct L2 RPC access is unavailable or the chain is not EVM-compatible.

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
- `aliases_coingecko_chain` — platform key used in CoinGecko's contract address API (e.g. `"arbitrum-one"`). Used by `fetch_coingecko_ecosystem.py`.
- `aliases_defillama` — chain slug for DefiLlama. Used by `fetch_defillama_assets.py`.
- `aliases_l2beat` — chain slug for L2Beat TVS JSON. Used by `fetch_l2beat_tvs.py`.
- `deployed_supplyreader` — date stablecoin supply reading was set up (null = not yet configured)
- `error` — set if the chain file was not found; stop and tell the user

Show the user the chain name and aliases. Note if `deployed_supplyreader` is null — the chain may not be fully set up for stablecoin tracking yet; mention this to the user. Documentation on how to set up the supply reader can be found [here](https://github.com/growthepie/backend-internal/tree/main/SupplyReader).

> **If the chain file is missing or many fields are null**, the chain's `chains/<origin_key>/main.json` may not exist yet or may be incomplete. In that case, create or fill out `main.json` first before continuing — the discovery scripts depend on `aliases_coingecko_chain`, `aliases_defillama`, and `aliases_l2beat` to find the right data sources. Prompt the user here to help fill it out.

## Step 3 — Discover stablecoin addresses

Run **all four** discovery scripts in parallel — they are independent read-only fetches with no dependencies on each other:

```bash
python .claude/skills/add-chain-stablecoin-mapping/scripts/fetch_l2beat_tvs.py <aliases_l2beat>
python .claude/skills/add-chain-stablecoin-mapping/scripts/fetch_defillama_assets.py <aliases_defillama>
python .claude/skills/add-chain-stablecoin-mapping/scripts/fetch_coingecko_ecosystem.py <aliases_coingecko_chain>
python .claude/skills/add-chain-stablecoin-mapping/scripts/fetch_dune.py --chain <aliases_dune_chain>
```

The `aliases_dune_chain` value is the Dune chain identifier for the chain (e.g. `ethereum`, `base`, `arbitrum`). Use the chain's common lowercase name — it typically matches the `origin_key` or a close variant. If unsure, omit `--chain` to get all results and filter manually.

### Dune (`fetch_dune.py`)

Returns stablecoin addresses from Dune Analytics query 6910797. Useful as an independent on-chain data source that cross-validates CoinGecko, L2Beat, and DefiLlama results. Requires `DUNE_API_KEY` to be set in `.env` or the environment.

### L2Beat TVS (`fetch_l2beat_tvs.py`)

Returns two buckets:

- **`native`** — `amount.type == "totalSupply"` tracked on-chain. The `address` field is the **actual local token address** on the chain. Also includes `bridged_using` if the token arrived via a bridge (e.g. LayerZero OFT) but is tracked by total supply on the L2. These addresses are ready to use.
- **`bridged_via_l1_escrow`** — tracked via L1 escrow balances. Only `l1_token_address` and `escrow_addresses` (on Ethereum) are available — **no local L2 address**. Use CoinGecko or a block explorer to find the actual L2 address.

**If the script returns a 404 or `aliases_l2beat` is null**, try finding the correct slug by fetching:
```
https://api.github.com/repos/l2beat/l2beat/contents/packages/config/src/tvs/json
```
This returns directory entries — each has a `name` field. Match against the chain's `origin_key` or display name, then retry.

### DefiLlama coreAssets (`fetch_defillama_assets.py`)

Returns `stablecoins` — a flat list of `{ symbol, address }` pairs from DefiLlama's curated asset registry for this chain. These are canonical addresses used by DeFi protocols and are generally reliable.

**If the script errors with "Chain not found"**, the chain may use a different slug in DefiLlama (e.g. `avax` instead of `avalanche`). Check `aliases_defillama` from Step 2.

### CoinGecko ecosystem (`fetch_coingecko_ecosystem.py`)

Returns `stablecoins` — coins from the chain's CoinGecko ecosystem category that match stablecoin symbols, with their contract address and decimals looked up directly from CoinGecko's platform data. Also returns `no_address_found` for stablecoins in the category that CoinGecko doesn't have a contract address for on this platform.

**If the script errors with "Category not found"**, the chain may use a different prefix. Browse `https://www.coingecko.com/en/categories` to find the right slug.

### Merging results

Combine all four sources into a single candidate list. Where two or more sources agree on an address for the same symbol, that address is highly reliable. Where they disagree or only one source has it, flag for manual verification. Show the user the merged candidate list.

## Step 4 — Match against coin_mapping and cross-check addresses

Read `stables/stables_config_v2.py`. For each stablecoin candidate from Step 3, do the following:

### 4a — Match to coin_mapping

Match by symbol to an existing entry in `coin_mapping`. If a match is found, note the `token_id` — that will be the key used in `address_mapping`.

If **no match exists**, propose a new `coin_mapping` entry. First determine whether the token is **natively issued** or **bridged (lock-and-mint)** based on the available data (L2Beat `bridged_using`, CoinGecko name, token symbol like "USDC.e", or source field), then use the appropriate format:

#### Resolving `owner_project`

The `owner_project` field must match a slug in the growthepie OSO-directory (projects API). **Always run the lookup script** before proposing a new entry:

```bash
python .claude/skills/add-chain-stablecoin-mapping/scripts/fetch_owner_project.py <keyword1> [keyword2 ...]
```

- Use the token symbol, issuer name, or project name as keywords (e.g. `lumi luausd`, `circle usdc`).
- If one or more matches are returned, pick the most relevant `owner_project` slug and show it to the user for confirmation.
- **If no match is found**, set `owner_project` to `null` and **explicitly warn the user** that this field should be filled in with the correct OSO-directory slug before merging. The full directory is at `https://api.growthepie.com/v1/labels/projects.json`. The user might need to create a new project in the OSO-directory if none currently exists. Suggest using the following tool: https://www.openlabelsinitiative.org/project

**Natively issued stablecoin** (`metric_key: "direct"`):
```python
{
    "owner_project": "<issuer_slug>",         # slug from OSO-directory, or null if not found
    "token_id": "<owner_project>_<symbol>",   # e.g. "fraxfinance_frxusd"
    "symbol": "FRXUSD",
    "coingecko_id": ["frax-usd"],             # list, from CoinGecko fetch
    "metric_key": "direct",
    "bridged_origin_chain": None,
    "bridged_origin_token_id": None,
    "fiat": "usd",                            # "usd", "eur", etc. based on peg
    "logo": "https://...",                    # from CoinGecko iconUrl or coin detail
    "color_hex": "#XXXXXX"                    # dominant color from logo, best guess
}
```

**Bridged / lock-and-mint stablecoin** (`metric_key: "bridged"`):
```python
{
    "owner_project": "<issuer_slug>",         # slug from OSO-directory, or null if not found
    "token_id": "<owner_project>_<symbol>",   # e.g. "circlefin_usdce"
    "symbol": "USDC.e",
    "coingecko_id": ["usd-coin-ethereum-bridged"],  # CoinGecko ID for the bridged variant
    "metric_key": "bridged",
    "bridged_origin_chain": "ethereum",       # chain where the canonical token lives
    "bridged_origin_token_id": "circlefin_usdc",  # token_id of the origin token in coin_mapping
    "fiat": "usd",
    "logo": "https://...",
    "color_hex": "#XXXXXX"
}
```

Signals that a token is bridged: symbol suffix like `.e`, `(bridged)` in the name, L2Beat `source == "canonical"` or `bridged_using` field present with a bridge name, or a CoinGecko ID containing "bridged".

Present all proposed new `coin_mapping` entries to the user for confirmation before writing anything.

### 4b — Build address_mapping entries

**If using `track_on_l1`** (chosen in the Tracking modes section): skip Steps 4a and the token matching entirely. The entry only needs the L1 bridge escrow contract addresses — no `token_id` keys are needed:

```python
"<origin_key>": {
    "track_on_l1": [
        "0x...",   # L1 bridge escrow contract 1
        "0x...",   # L1 bridge escrow contract 2
    ]
}
```

Ask the user for the L1 escrow contract addresses (find via the chain's official bridge docs or L2Beat's escrow list). Then skip to Step 5.

---

**If using direct tracking**: for each matched or newly proposed token, build:

```python
"<origin_key>": {
    "<token_id>": {
        "address": "0x...",   # local token address on this chain (lowercase)
        "decimals": 6,
        "exclude_balances": [  # optional: addresses to exclude from supply (e.g. treasury, reserves)
            "0x..."
        ]
    },
    ...
}
```

**Rules:**
- Only include candidates where the address is the **local token address on the chain** — not an L1 escrow or bridge contract. For `bridged_via_l1_escrow` entries from L2Beat, the local L2 address must first be confirmed via CoinGecko (`detail_platforms[aliases_coingecko_chain]`) or a block explorer.
- **Do not remove existing entries** in `address_mapping[origin_key]`. Only flag conflicts (same `token_id` with a different address or different decimals) and ask the user how to resolve them.
- Skip tokens with negligible liquidity or that are clearly not yet live.

Present the full proposed changes (new `coin_mapping` entries + updated `address_mapping` block) to the user for confirmation before writing anything.

## Step 5 — Write the entry

Once the user confirms, write both sets of changes to `stables/stables_config_v2.py`:

1. **New `coin_mapping` entries** — append after the last existing entry in `coin_mapping`.
2. **`address_mapping[origin_key]`** — insert in alphabetical order by `origin_key`, or append if cleaner. Preserve existing formatting (4-space indent, lowercase addresses).

## Step 6 — Done


After writing, confirm success and remind the user:
- If `deployed_supplyreader` was null, suggest to the user to deploy the supply reader contract for more efficient RPC calls and better performance.
- Open a PR if this is a community contribution.
