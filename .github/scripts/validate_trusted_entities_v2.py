#!/usr/bin/env python3
"""
Validation script for oli/trusted_entities_v2.yml.
"""
from oli import OLI
oli = OLI()

# read in yaml file as json
import yaml
with open('oli/trusted_entities_v2.yml') as f:
    trust_list = yaml.load(f, Loader=yaml.FullLoader)

# attest the trust list
print(oli.validate_trust_list('growthepie', trust_list['attesters']))