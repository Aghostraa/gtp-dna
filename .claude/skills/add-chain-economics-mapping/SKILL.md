---
name: add-chain-economics-mapping
description: Add a new chain to economics_da/economics_mapping.yml. Use this skill whenever the user wants to add, register, or onboard a new L2 chain, mentions a chain that isn't in the mapping yet, asks how to track settlement or DA costs for a new chain, or says anything like "add chain", "new chain", or "register chain" in the context of the economics or DA mapping.
---

You are helping add a new chain to `economics_da/economics_mapping.yml`.

## Step 1 — Get the origin_key and validate

Ask the user for the **origin_key** if not already provided (e.g. `arbitrum`, `base`, `my_chain` — must match the key used in the `chains/` directory).

Immediately check that this key does **not** already exist in `economics_da/economics_mapping.yml`. If it does, stop and suggest the `update-chain-economics-mapping` skill instead.

## Step 2 — Load chain metadata

Run the helper script to pull name, DA layer, and L2Beat alias from the chain's `main.json`:

```bash
python .claude/skills/add-chain-economics-mapping/scripts/get_chain_info.py <origin_key>
```

The script outputs JSON with:
- `name` — use this as the chain name in the mapping
- `suggested_layers` — fee layers inferred from `metadata_da_layer` (e.g. `["l1", "beacon"]`)
- `note` — explanation of the suggestion
- `aliases_l2beat` — the L2Beat project slug (used in the next step)
- `error` — set if the chain file was not found; tell the user and stop

Show the user the chain name and suggested fee layers. The user can add or remove layers — confirm before proceeding.

## Step 3 — Fetch contract and operator addresses from L2Beat

If `aliases_l2beat` is set, run:

```bash
python .claude/skills/add-chain-economics-mapping/scripts/fetch_l2beat_contracts.py <aliases_l2beat>
```

**If `get_chain_info.py` failed, `aliases_l2beat` is null, or `fetch_l2beat_contracts.py` returns a 404**, try to find the correct L2Beat slug by fetching the full list of L2Beat projects via the GitHub API:

```
https://api.github.com/repos/l2beat/l2beat/contents/packages/config/src/projects
```

This returns a JSON array of directory entries — each has a `name` field. Find the entry whose `name` best matches the chain's `origin_key` or display name (try lowercase, replace spaces with hyphens/underscores, strip common suffixes like `-mainnet`). Once you identify the likely slug, retry `fetch_l2beat_contracts.py` with it.

This fetches `discovered.json` from L2Beat's GitHub and returns contracts split into two groups:
- `settlement_contracts` — contracts likely relevant to the mapping (inbox, oracle, rollup, dispute game, etc.)
- `bridge_contracts` — filtered out because they are bridge/escrow/portal/token contracts. End users send transactions to bridges, not the chain's settlement system — querying them returns massive irrelevant tx volumes that are hard to interpret. Only query these as a last resort if `settlement_contracts` yield no results.
- `eoas` — EOAs with their permission roles (look for `Sequence`, `Propose`, `Batch`)

From these results, identify **candidate addresses to investigate** — only from `settlement_contracts` and relevant EOAs:
- **`to_address` candidates**: Focus on `settlement_contracts` with names like `Inbox`, `OutputOracle`, `DisputeGame`, `Rollup`, `SequencerInbox`, `BatchSubmitter`, `StateCommitmentChain`, or descriptions mentioning batches, state roots, or proofs.
- **`from_address` candidates**: EOAs whose roles contain `Sequence`, `Propose`, or `Batch`.

> **State root proposers also resolve**: When Dune returns a `proposeL2Output` / `commitBatches` / similar state-root function from an EOA, that same EOA almost always also calls a **resolve or finalize function** (e.g. `resolveGame`, `finalizeWithdrawalTransaction`, `deleteL2Outputs`). Make sure to check the Dune results for **all** method selectors from that EOA — don't stop at the proposal call. Each distinct method needs its own mapping entry.

## Step 4 — Verify settlement transactions via Dune

For each candidate address from Step 3, run the Dune transaction analysis query. This verifies which addresses actually have onchain settlement activity before writing anything to the mapping. Skip addresses that have no results or only look like regular user transactions.

Use `recommended_dune_query_id` from `get_chain_info.py` output as the `--query-id`. The correct query ID is selected automatically by the script: `6819777` for most chains, `6823319` for **Elastic Chain** chains (`chain_bucket == "Elastic Chain"`) — this query additionally returns `chain_address` (the diamond address that identifies the specific chain within shared zkStack contracts).

**For `to_address` candidates** (check what is being sent to this contract):
```bash
python .claude/skills/add-chain-economics-mapping/scripts/dune_api.py \
  --query-id <recommended_dune_query_id> \
  --to-address <contract_address> \
  --from-address all \
  --from-date 2023-01-01
```

**For `from_address` candidates** (check what this EOA sends):
```bash
python .claude/skills/add-chain-economics-mapping/scripts/dune_api.py \
  --query-id <recommended_dune_query_id> \
  --to-address all \
  --from-address <eoa_address> \
  --from-date 2023-01-01
```

The query returns rows grouped by `(function, to, from)` sorted by `no_of_trx` descending, with `first_used`, `last_used`, `no_of_trx`, `avg_data_length`, and `tx_type`. For Elastic zkStack chains, also check the `chain_address` column — it contains the diamond address that should be used as the mapping identifier. Focus on the top rows — high transaction counts are the clearest signal of settlement activity.

**Interpreting results:**
- High `no_of_trx` + recurring pattern → strong candidate for the mapping
- `tx_type = 3` → EIP-4844 blob transaction → add to **both** `l1` and `beacon` layers. Type 3 transactions pay fees in two separate fee markets: the L1 execution layer (gas) and the beacon chain blob fee market. The same `from_address`/`to_address`/`method` entry must appear under both sections. **Beacon entries should be as lightweight as possible** — prefer setting `to_address` and `method` to `null` and only keeping `from_address`, since the blob fee is determined by who sends the transaction, not where it goes.
- `tx_type != 3` → regular L1 transaction → belongs in `l1` layer only
- `function` field is the 4-byte method selector (e.g. `0x3e5aa082`) — include this in the mapping entry
- If `from` address is the same EOA for all rows → use as `from_address`; set `to_address` + `method` from results
- If `to` address is the same contract for all rows → use as `to_address`; set `from_address` + `method` from results
- Ignore entries that look like one-off user transactions or have very low tx counts

Present a summary of findings to the user. Do **not** write to `economics_mapping.yml` until the Dune data confirms real settlement activity.

If `DUNE_API_KEY` is not set, tell the user and ask them to set it or provide it via `--api-key`.

## Step 5 — Confirm entries with user

Show the user the proposed mapping entries derived from the Dune results. For each entry include:
- The layer (`l1` or `beacon`)
- `from_address`, `to_address`, `method` (null if not applicable)
- A suggested `comment` with the method name (if known) and the `first_used` date from Dune. Only append `last_used` if it is **not today's date** — `last_used` is a deprecation marker for entries that are no longer active. Examples: active entry: `"commitBatches (first used 2024-03-14)"`, deprecated entry: `"commitBatches (first used 2024-03-14, last used 2024-11-30)"`

Ask the user to confirm, correct, or add any missing entries before writing.

**For `celestia` layers** (no Dune data available): direct the user to Celenium to find the namespace — namespaces typically start with `AAAAAAA...`. Send them to: `https://celenium.io/network/{chain-name}?tab=Namespaces` (replace `{chain-name}` with the chain's network name on Celenium, e.g. `https://celenium.io/network/gravity-alpha?tab=Namespaces`).

**For `eigenda` layers** (no Dune data available): run the EigenDA namespace script to find active `customer_id` values and which are not yet mapped:

```bash
python .claude/skills/add-chain-economics-mapping/scripts/fetch_eigenda_namespaces.py --unmapped-only
```

This fetches today's EigenDA blob data, groups by `account_name` / `customer_id`, and shows everything not yet in the mapping. Match the chain's name against `account_name` to find its `customer_id` — that is the `namespace` value to add.

## Step 6 — Show and confirm YAML

Show the user the exact YAML block that will be appended and ask for a final confirmation before writing.

## Step 7 — Write the entry

Append to the **end** of `economics_da/economics_mapping.yml`. Only include fee layer sections that have entries — omit the rest.

```yaml
{origin_key}:
  name: "{Chain Name}"
  l1:
    - from_address: {value or null}
      to_address: {value or null}
      method: {value or null}
      comment: "{description}"
  beacon:
    - from_address: {value or null}
      to_address: {value or null}
      method: {value or null}
      comment: "{description}"
  celestia:
    - namespace: "{base64_namespace}"
      comment: "{optional description}"
  eigenda:
    - namespace: "{hex_or_ip_namespace}"
```

## Step 8 — Done

After writing, confirm success and remind the user:
- The mapping syncs to Dune as `dune.growthepie.l2economics_mapping`.
- Open a PR if this is a community contribution.
