# Welcome to the Economics and DA Mapping

This repository defines all transactions sent by L2s that should be considered in the cost and DA metrics calculations for the [Economics Overview](https://www.growthepie.xyz/economics) and the [DA Overview](https://www.growthepie.xyz/da-overview) pages.  

The result is a list of transactions grouped by each L2, enabling calculations such as total transaction fees and total blob data size per L2.

## Community Contribution

This is a community-driven effort. Please feel free to double-check the [mapping](economics_mapping.yml) and submit a PR to add, update, or adjust any mappings. Thank you for your contribution. 


## Mapping Structure

Each L2 network has its own entry. The structure is then further divided by the underlying chains where the L2 posts data. This could be any of the following:

- **Ethereum L1 (`L1`):** Used for execution and settlement.
- **Ethereum Beacon Chain (`beacon`):** Used for blobs.
- **Celestia (`celestia`):** Most common altDA also used for blobs data.

### Key Concepts Behind the Mapping

The purpose of this mapping is to filter raw transaction tables down to only the transactions the L2 sent (paid for) or those for which the L2 substituted gas fees.  
Additionally, it includes all transactions the L2 must send to operate its chain, primarily involving settling its states, posting data, or submitting proofs.  
Costs that cannot be tracked on-chain (such as off-chain compute) are not included.

### Filter Parameters

For **Ethereum L1 (`L1`)** and **Ethereum Beacon Chain (`beacon`)** transactions, the following filters can be set, at least one has to be not `null`:

1. **From Address (****`from_address`****):** Identifies who sent the transaction (e.g. sequencer).
2. **To Address (****`to_address`****):** Specifies the recipient of the transaction (e.g. inbox contract).
3. **Method (****`method`****):** Indicates the specific function call invoked during the transaction.

For **Celestia (`celestia`):**

- **Namespace:** The namespace the blobs are sent to (base64 format e.g. "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAGVjbGlwc2U=").

*more altDA chains to be listed soon*


