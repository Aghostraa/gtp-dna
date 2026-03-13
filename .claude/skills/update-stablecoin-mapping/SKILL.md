---
name: update-stablecoin-mapping
description: Add a new stablecoin or new addresses for an existing stablecoin in stables/stables_config_v2.py. Use this skill whenever the user wants to add a new stablecoin token, add addresses for an existing token on additional chains, a chain already exists in address_mapping and needs new tokens added, or the user says anything like "add stablecoin", "new token", "add token", "missing stablecoin", or "add addresses" in the context of stablecoin tracking.
---

You are helping update `stables/stables_config_v2.py` — either by adding a new stablecoin to `coin_mapping`, adding `address_mapping` entries for an existing token on new chains, or both.

## Step 1 — Understand what is being added

Ask the user what they want to add (if not already clear):
- **New stablecoin token**: needs a new entry in `coin_mapping` + `address_mapping` entries per chain.
- **New chain addresses for existing token**: the token_id already exists in `coin_mapping`, but is missing from `address_mapping` for one or more chains. (If the entire chain is missing from `address_mapping`, suggest `add-chain-stablecoin-mapping` instead.)

Read `stables/stables_config_v2.py` to check the current state before proceeding.

## Step 2 — Gather token metadata (new stablecoin only)

If adding a new stablecoin, collect the following from the user or look it up:

| Field | Description |
|---|---|
| `owner_project` | OLI schema `owner_project` tag. See: https://www.openlabelsinitiative.org/project |
| `token_id` | Unique ID. Recommended: `{owner_project}_{symbol_lowercase}` |
| `symbol` | Token symbol (e.g. `USDC`) |
| `coingecko_id` | List of CoinGecko IDs (used for address discovery). Look up on coingecko.com. |
| `metric_key` | `"direct"` if natively issued; `"bridged"` if it bridges another canonical token |
| `bridged_origin_chain` | If `metric_key == "bridged"`: the chain where the canonical token lives |
| `bridged_origin_token_id` | If `metric_key == "bridged"`: the canonical token_id to deduct from |
| `fiat` | Peg currency: `usd`, `eur`, `gbp`, `chf`, `aud`, `jpy`, etc. Must exist in `currency_config.py` |
| `logo` | CoinGecko large image URL (optional but recommended) |
| `color_hex` | Brand color for charts (optional) |

**T3 Rules — check before adding**:
1. No value-increasing stablecoins (e.g. sUSDS, aTokens).
2. No stablecoins that mainly wrap another stablecoin, unless it is a bridge representation.
3. Only stablecoins that anyone can own (no permissioned/institutional-only tokens like BUIDL).

If the token violates any T3 rule, stop and tell the user.

## Step 3 — Find addresses per chain

For each chain where the stablecoin is deployed, you need the **local token address** (not a bridge escrow) and **decimals**.

### Option A — CoinGecko (preferred for tokens with a `coingecko_id`)

Fetch coin detail from the CoinGecko API:
```
GET https://api.coingecko.com/api/v3/coins/{coingecko_id}
```
(Use the pro API if `COINGECKO_API` env var is set: `https://pro-api.coingecko.com/api/v3/coins/{coingecko_id}` with header `x-cg-pro-api-key`.)

From the response:
- `coin_data["detail_platforms"][aliases_coingecko_chain]["contract_address"]` → address
- `coin_data["detail_platforms"][aliases_coingecko_chain]["decimal_place"]` → decimals

The `aliases_coingecko_chain` for each chain can be found by running:
```bash
python .claude/skills/add-chain-stablecoin-mapping/scripts/get_chain_info.py <origin_key>
```

Match each platform key from CoinGecko against the `aliases_coingecko_chain` values across all chains in `chains/`. Only keep chains that are already in `address_mapping`.

### Option B — L2Beat TVS JSON (good for chain-focused discovery)

```bash
python .claude/skills/add-chain-stablecoin-mapping/scripts/fetch_l2beat_tvs.py <aliases_l2beat>
```

Filter results by matching symbol. Verify the address is the local token (not a bridge escrow) using the chain's block explorer.

### Option C — DeFi Llama or block explorer (manual fallback)

Direct the user to:
- `https://defillama.com/stablecoins/{aliases_defillama}` — lists stablecoins with addresses
- The chain's block explorer — search by token symbol

## Step 4 — Review T3 rules for chain-specific entries

For `metric_key == "bridged"` tokens: confirm the address is the bridged token on the chain (not the L1 escrow). Verify `bridged_origin_chain` and `bridged_origin_token_id` are correct — these are used to avoid double-counting supply.

For `metric_key == "direct"` tokens: confirm the token is natively issued on this chain (e.g. Circle issues USDC natively on many L2s).

## Step 5 — Show proposed changes and confirm

Show the user exactly what will be added:

**If adding a new coin_mapping entry:**
```python
{
    "owner_project": "...",
    "token_id": "...",
    "symbol": "...",
    "coingecko_id": ["..."],
    "metric_key": "direct",          # or "bridged"
    "bridged_origin_chain": None,    # or "ethereum"
    "bridged_origin_token_id": None, # or "circlefin_usdc"
    "fiat": "usd",
    "logo": "https://...",
    "color_hex": "#..."
}
```

**If adding address_mapping entries:**
```python
# Under address_mapping["<origin_key>"]:
"<token_id>": {
    "address": "0x...",
    "decimals": 6
}
```

List any chains where you could not find or verify an address — the user may want to add those manually later.

Ask the user to confirm before writing.

## Step 6 — Write the changes

Use the Edit tool to insert into `stables/stables_config_v2.py`:

1. **`coin_mapping`** (if new token): append the new dict at the end of the `coin_mapping` list, before the closing `]`. Match the existing formatting (4-space indent, trailing comma).

2. **`address_mapping`** (new chain addresses): for each chain, insert the new `token_id` entry inside the existing chain block. If the chain block doesn't exist yet, suggest using `add-chain-stablecoin-mapping` first.

Do not add commented-out sections. Keep `address_mapping` comment-free to keep auto-generated diffs clean (as noted in the README).

## Step 7 — Done

After writing, confirm success and remind the user:
- If `coingecko_id` is set, the semi-automated update script in `stables_README.md` can discover new chain addresses automatically in the future.
- If `aliases_coingecko_chain` is missing for any chain, add it to `chains/{origin_key}/main.json` so the script can match it.
- Open a PR if this is a community contribution.
