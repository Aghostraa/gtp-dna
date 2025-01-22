# Welcome to the Economics and DA Mapping

This repository defines all transactions sent by L2s that should be considered in the cost and DA metrics calculations for the [Economics Overview](https://www.growthepie.xyz/economics) and the [DA Overview](http://growthepie.xyz/data-availability/overview) pages.  

The result is a list of transactions grouped by each L2, enabling calculations such as total L1 fees paid or total blob daten size per L2.

### Dune Analytics Table

This mapping is automatically synced to a Dune table and can be accessed in Dune as follows:

`SELECT * 
FROM dune.growthepie.l2economics_mapping`

### Community Contribution

This is a community-driven effort. Please feel free to double-check the [mapping](economics_mapping.yml) and submit a PR to add, update or adjust any mappings. Thank you for your contribution. 


## Mapping Structure

Each L2 network has its own section, which is further divided by the underlying fee markets where the L2 pays fees. These could be any of the following layers:

- **Ethereum L1 Execution Layer (`l1`):** Used for execution and settlement of transactions. This should include all fees paid in the L1 fee market. 
- **Ethereum Beacon Chain Layer (`beacon`):** Used by L2s to post blobs. This should include all fees paid in the beacon chain fee market.
- **Celestia (`celestia`):** Most common altDA also used to post blobs. This should include all fees paid to Celestia.

### Key Concepts Behind the Mapping

The purpose of this mapping is to get a table with all transactions sent (or paid for) by L2s broken down based on the different fee market. 
Transactions on L2s are primarily used to settle states, post raw transaction data or submit proofs.
Costs that cannot be tracked onchain (such as offchain compute) are not included.

### Filter Parameters

For **Ethereum L1 Execution Layer (`L1`)** and **Ethereum Beacon Chain Layer (`beacon`)**, the following filters can be set, at least one field has to be not `null`:

1. **`from_address`**: Identifies who sent the transaction (e.g. sequencer).
2. **`to_address`**: Specifies the recipient of the transaction (e.g. inbox contract).
3. **`method`**: Indicates the specific function call invoked during the transaction.

For **Celestia (`celestia`)** the following filter must be set:

- **Namespace:** Namespace of the blobs (in base64 format e.g. "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAGVjbGlwc2U=").

*more fee markets (altDAs) to be listed soon*


