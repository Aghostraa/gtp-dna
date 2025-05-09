# growthepie DNA

This repository contains the core data definitions and mapping files that power [growthepie.xyz](https://www.growthepie.xyz) - an open-source Ethereum analytics platform.

## 🌟 Overview

The GTP-DNA repo acts as the central source of truth for growthepie's config files and metadata. It contains:

- **Chain definitions** - Metadata about L1 and L2s
- **Data availability mapping** - Information about how Layer 2 post data
- **Economic tracking** - Transaction mapping for cost analysis across Layer 2s
- **Label confidence lists** - Entity verification for Open Labels Initiative

All of this data feeds directly into growthepie's analytics pipelines, dashboards, and APIs.

## 📁 Repository Structure

- **`/chains/`** - JSON definitions for each blockchain we track
  - Each chain has its own directory containing:
    - `main.json` - Core chain metadata
    - `logo.json` - SVG path data for chain logo

- **`/da_layers/`** - Data availability layer definitions
  - Each DA layer has:
    - `main.json` - Core DA layer metadata
    - `logo.json` - SVG path data for DA layer logo

- **`/economics_da/`** - Economics and data availability tracking
  - `economics_mapping.yml` - Maps transaction types to their respective chains
  - `readme.md` - Explanation of the economics mapping

- **`/logos/`** -  Logo definitions for applications or chains not yet supported by growthepie
  - `images/` - Project logos, mapping the name to the official project slug in the OSS directory
  - `custom_logos.json` - SVG path data for custom chain logos

- **`/oli/`** - Open Labels Initiative data
  - `trusted_entities.yml` - List of trusted entities for OLI
  - `README.md` - Explanation of the OLI integration

## 🔍 Key Components

### Chain Definitions

The chain definition files in `/chains/` directory contain structured metadata about each blockchain, including:

- Basic identifiers (name, chain ID, symbol)
- Block explorer URLs
- Color schemes for UI
- Technology stack details
- Social media links
- API deployment flags
- Cross-check sources

### Data Availability Mapping

The `/economics_da/economics_mapping.yml` file maps L2 transactions to their respective DA (Data Availability) layers. This enables:

- Tracking of Layer 1 costs for each Layer 2
- Analysis of data posting patterns
- Monitoring of economic efficiency

### Open Labels Initiative (OLI)

The `/oli/` directory contains confidence scores for trusted attesters in the Open Labels Initiative ecosystem, which helps with entity verification.

## 🤝 How to Contribute

We welcome contributions from the community! Here's how you can help:

### Adding or Updating Chain Information

1. **Fork the repository**

2. **Create or modify chain definition files**
   - If adding a new chain, create a new directory in `/chains/` named after the chain
   - Copy the structure from an existing chain and adapt it
   - Include `main.json` with all required metadata
   - Add `logo.json` with SVG path data for the chain's logo

3. **Test your changes**
   - Ensure all JSON files are properly formatted
   - Validate that all required fields are included

4. **Submit a pull request**
   - Provide a clear description of your changes
   - Reference any relevant issues or external resources

### Updating Economics/DA Mappings

1. **Fork the repository**

2. **Edit the mapping file**
   - Update `/economics_da/economics_mapping.yml` with new or corrected mappings
   - Follow the existing structure for consistency
   - Add detailed comments for new entries

3. **Submit a pull request**
   - Explain the reasoning behind your changes
   - Include links to transaction examples if applicable

## 📊 Data Usage

The definitions in this repository power several features on growthepie.xyz:

- **Economics Overview**: https://www.growthepie.xyz/economics
- **Data Availability Overview**: https://www.growthepie.xyz/data-availability
- **Chain Listings**: Various chain metrics and visualizations

The economics data is also available via a Dune Analytics table:
```sql
SELECT * FROM dune.growthepie.l2economics_mapping
```

## 📜 License

This repository is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgements

Special thanks to all contributors who help maintain and improve this data. Your efforts help provide accurate and comprehensive information to the blockchain community.

---

For questions or feedback, please open an issue on this repository or reach out to the growthepie team.