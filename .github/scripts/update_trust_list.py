#!/usr/bin/env python3
"""
Attest the OLI trust list using the oli-python package.
"""
from oli import OLI
import os

oli = OLI(private_key=os.getenv('OLI_API_KEY'))

# read in yaml file as json
import yaml
with open('oli/trusted_entities_v2.yml') as f:
    trust_list = yaml.load(f, Loader=yaml.FullLoader)

# attest the trust list
r = oli.submit_trust_list('growthepie', trust_list['attesters'])

# print for debugging purposes
print(r)