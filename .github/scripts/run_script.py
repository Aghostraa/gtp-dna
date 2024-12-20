import yaml
import pandas as pd

# Load YAML data
with open('economics_da/economics_mapping.yml') as f:
    data = yaml.load(f, Loader=yaml.FullLoader)

# Process YAML data into a table
table = [
    [
        L2, 
        settlement_layer, 
        f.get('from_address'), 
        f.get('to_address'), 
        f.get('method'), 
        f.get('namespace') if settlement_layer == 'celestia' else None
    ]
    for L2, layers in data.items()
    for settlement_layer, filters in layers.items()
    for f in filters
]

# Convert table to DataFrame and save to CSV
df = pd.DataFrame(table, columns=['l2', 'settlement_layer', 'from_address', 'to_address', 'method', 'namespace'])
df.to_csv('economics_mapping.csv', index=False)