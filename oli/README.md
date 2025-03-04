# growthepie x OLI Label Confidence List  

This repository contains growthepie's list of trusted entities for the Open Labels Initiative (OLI).  

### Structure  
- **[trusted_entities.yml](trusted_entities.yml)** → Stores the trusted entities as a list.  
- Each address is mapped to a tag_id and a score.  
- Score range: 1–100 (100 = highest certainty the label is correct).  

### Purpose  
- This list is dynamic, new trusted entities can be added and old ones can be removed.
- Used to filter and refine raw attestations from the OLI Label Pool.  

For more details on OLI, visit [OLI Github](https://github.com/openlabelsinitiative/OLI).