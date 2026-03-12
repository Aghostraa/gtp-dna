---
name: update-chain-economics-mapping
description: Update an existing chain entry in economics_da/economics_mapping.yml. Use this skill whenever the user wants to edit, fix, change, or extend a chain that already exists in the mapping — for example adding a new contract address, correcting a method selector, adding a new fee layer like blobs or Celestia, removing an outdated entry, or updating a chain name.
---

You are helping update an existing chain in `economics_da/economics_mapping.yml`.

## Step 1 — Identify the chain

Ask the user which chain to update (by key or name). Read `economics_da/economics_mapping.yml`, find the existing entry, and show it to the user so they can see what's there.

If the chain key does **not** exist, stop and suggest the `add-chain-economics-mapping` skill instead.

## Step 2 — Determine what to change

Ask the user what they want to update. Common operations:

1. **Add a new entry** to an existing fee layer (`l1`, `beacon`, `celestia`, `eigenda`)
2. **Remove an entry** from a fee layer
3. **Edit an existing entry** — correct an address, fix a comment, add/change a method
4. **Add a new fee layer** section — e.g. chain is now also posting blobs
5. **Remove an entire fee layer** section
6. **Update the chain name**

Collect required fields for the change:

**`l1` / `beacon` entries** (at least one must be non-null):
- `from_address`, `to_address`, `method`, `comment`

**`celestia` entries**:
- `namespace` — base64 e.g. `"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAGVjbGlwc2U="`
- `comment` — optional

**`eigenda` entries**:
- `namespace` — hex address or IP string
- `comment` — optional

## Step 3 — Validate

- Confirm the target entry is unambiguous when removing or editing (identify by address, method, or namespace).
- Every modified/added `l1`/`beacon` entry must still have at least one non-null field.
- Warn the user if removing the last entry in a fee layer — the whole section will be removed.

## Step 4 — Show diff and confirm

Show a before/after comparison of the affected YAML block and ask for confirmation before writing.

## Step 5 — Apply the change

Use the Edit tool to make a targeted, minimal change to `economics_da/economics_mapping.yml`. Preserve all surrounding content and formatting exactly.

## Step 6 — Done

Confirm the change was applied and remind the user:
- The mapping syncs to Dune as `dune.growthepie.l2economics_mapping`.
- Open a PR if this is a community contribution.
