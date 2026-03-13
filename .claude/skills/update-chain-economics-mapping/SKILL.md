---
name: update-chain-economics-mapping
description: Update an existing chain entry in economics_da/economics_mapping.yml by adding newly discovered contracts or EOAs. Use this skill whenever a chain's settlement contracts have changed, a new sequencer EOA or inbox contract was deployed, an alert fires about unexpected addresses or methods, or the user says anything like "update chain", "new contract", "rotated to", "upgrade", or pastes an alert message about a chain's economics mapping changing. IMPORTANT: this skill only adds entries, never removes them.
---

You are helping extend an existing chain's entry in `economics_da/economics_mapping.yml`.

**Core principle**: updates should only ever **add** new entries. Do not remove existing entries unless an old address directly conflicts with a newly confirmed one (e.g. same `to_address`+`method` pair that now routes differently). Keeping old entries preserves historical cost attribution.

## Step 1 — Get the origin_key and load current mapping

Ask the user for the **origin_key** if not already clear from context (e.g. from an alert message). The file is keyed by `origin_key`, so this must be exact.

Read `economics_da/economics_mapping.yml` and show the user the **current entry** for that chain so both of you have a shared baseline.

If the key does **not** exist, stop and suggest the `add-chain-economics-mapping` skill instead.

## Step 2 — Understand what changed

Most updates fall into one pattern: **a contract or EOA was rotated or added as part of a chain upgrade** — a new sequencer inbox, a new output oracle, a new proposer EOA, or a new DA namespace.

If the user provided an **alert message**, parse it for clues. Alerts typically look like:

> "The economics mapping function for bob has changed. Details: settlement on l1, 10 trx per day, from_address: 0x7cb1022d30b9860c36b243e7b181a1d46f618c69, to_address: \<nil\>, method: 0x2810e1d6."

**Important — how alerts work**: alerts fire on addresses that are **already in the mapping** and are detecting a change in their activity pattern. The address in the alert is the **existing/known** one that may be getting deprecated or rotated away from. Do not check whether the alert address is already in the mapping — it always will be. Instead, treat the alert as a signal that a **new** contract or EOA may have taken over and is not yet in the mapping.

From an alert, extract:
- `origin_key` — the chain name in the alert (e.g. "bob")
- The fee layer mentioned (`l1`, `beacon`, etc.)
- The existing address and method — useful context for understanding the role being rotated

Address casing is irrelevant — `0xABC...` and `0xabc...` are the same address. Never flag a casing difference as a mismatch.

If no alert was provided, ask the user what changed (new contract address, upgrade announcement, etc.).

## Step 3 — Load chain metadata and check for settlement layer changes

Run `get_chain_info.py` first to get the L2Beat slug and check whether the chain's settlement layer has changed:

```bash
python .claude/skills/add-chain-economics-mapping/scripts/get_chain_info.py <origin_key>
```

This returns `suggested_layers` (derived from `metadata_da_layer`) and `aliases_l2beat`.

Compare `suggested_layers` against the fee layer sections currently in the mapping:
- If the mapping has only `l1` entries but `suggested_layers` now includes `beacon` → the chain likely migrated to blobs; this is a strong signal that new entries are needed.
- If a new AltDA layer (`celestia`, `eigenda`) appears in `suggested_layers` but is absent from the mapping → the chain added an AltDA; new namespace entries are needed. For Celestia, ask the user to look up the namespace on Celenium — namespaces typically start with `AAAAAAA...`. Direct them to: `https://celenium.io/network/{chain-name}?tab=Namespaces` (replace `{chain-name}` with the chain's network name on Celenium, e.g. `https://celenium.io/network/gravity-alpha?tab=Namespaces`).
- If `suggested_layers` matches what is already mapped → no layer-level change; focus on contract/EOA rotation within the existing layers.

Tell the user what you observe about the layer comparison before proceeding.

## Step 4 — Fetch current contracts from L2Beat

Using the `aliases_l2beat` from the previous step, fetch the latest known contracts and EOAs:

```bash
python .claude/skills/add-chain-economics-mapping/scripts/fetch_l2beat_contracts.py <aliases_l2beat>
```

The script returns contracts split into `settlement_contracts` and `bridge_contracts`. Prioritise `settlement_contracts` as candidates — bridge/escrow/portal contracts receive transactions from end users, not from the chain's settlement system, and querying them via Dune returns massive irrelevant volumes that are hard to interpret. Only fall back to `bridge_contracts` as a last resort if `settlement_contracts` yield no useful results.

Compare the `settlement_contracts` and EOAs against what is already in the mapping (case-insensitive). Identify **addresses present in L2Beat but missing from the current mapping** — these are the candidates for new entries.

Use the existing alert address to understand the **role** being rotated (e.g. if `0x7cb1...` is a proposer EOA in L2Beat, look for other proposer EOAs or contracts in `settlement_contracts` that are not yet in the mapping — those are the likely replacements).

## Step 5 — Verify new addresses via Dune

For each candidate address not yet in the mapping, confirm it has real settlement activity using the Dune query. Use the same approach as in the add-chain skill:

Use `recommended_dune_query_id` from `get_chain_info.py` output as the `--query-id`. The correct query ID is selected automatically by the script: `6819777` for most chains, `6823319` for **Elastic Chain** chains (`chain_bucket == "Elastic Chain"`) — this query additionally returns `chain_address` (the diamond address identifying the specific chain within shared zkStack contracts).

**Contract address (to_address candidate):**
```bash
python .claude/skills/add-chain-economics-mapping/scripts/dune_api.py \
  --query-id <recommended_dune_query_id> \
  --to-address <contract_address> \
  --from-address all \
  --from-date 2023-01-01
```

**EOA address (from_address candidate):**
```bash
python .claude/skills/add-chain-economics-mapping/scripts/dune_api.py \
  --query-id <recommended_dune_query_id> \
  --to-address all \
  --from-address <eoa_address> \
  --from-date 2023-01-01
```

For Elastic zkStack chains, also check the `chain_address` column in results — it contains the diamond address that identifies the specific chain and should be used in the mapping.

Results are sorted by `no_of_trx` descending — focus on the top rows. A handful of high-count rows with consistent `function` and `to`/`from` patterns is the clearest signal of settlement activity. Many low-count rows likely indicate user interactions, not chain-level settlement.

Interpret results:
- High `no_of_trx` + recurring pattern → confirmed settlement activity, add to mapping
- `tx_type = 3` → EIP-4844 blob transaction → add to **both** `l1` and `beacon` layers. Type 3 transactions pay fees in two separate fee markets: the L1 execution layer (gas) and the beacon chain blob fee market. The same `from_address`/`to_address`/`method` entry must appear under both sections.
- `tx_type != 3` → regular L1 call → `l1` layer only
- `function` field → 4-byte method selector to include in the entry
- `first_used` / `last_used` → use in the `comment` field

If an alert address is confirmed active but missing from the mapping, that's the entry to add.

## Step 6 — Propose new entries

Show the user the proposed additions as YAML entries. For each new entry include:
- The layer (`l1` or `beacon`)
- `from_address`, `to_address`, `method` (null where not applicable)
- A `comment` with the method name (if known) and the `first_used` date from Dune. Only append `last_used` if it is **not today's date** — `last_used` is a deprecation marker for entries that are no longer active. Examples: active entry: `"commitBatches (first used 2024-03-14)"`, deprecated entry: `"commitBatches (first used 2024-03-14, last used 2024-11-30)"`

Only propose **additions**. If an old entry appears to be superseded (same contract, same method, but a newer version now exists), mention it to the user but do not remove it without explicit confirmation.

Ask the user to confirm before writing.

## Step 7 — Apply the change

Use the Edit tool to insert the new entries into the correct fee layer section of the chain's block. Preserve all surrounding YAML exactly — indentation, null values, comment style.

## Step 8 — Done

Confirm the update and remind the user:
- The mapping syncs to Dune as `dune.growthepie.l2economics_mapping`.
- Open a PR if this is a community contribution.
