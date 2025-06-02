import yaml
import pandas as pd
import sys
from collections import defaultdict

# Load the YAML file
try:
    with open('economics_da/economics_mapping.yml') as f:
        data = yaml.safe_load(f)
except Exception as e:
    print(f"❌ ERROR: unable to load YAML file: {e}")
    sys.exit(1)

# extract data from yaml file
table = []
try:
    for L2, layers in data.items():
        for settlement_layer, filters in layers.items():
            if isinstance(filters, list):
                for f in filters:
                    row = [
                        L2,
                        layers.get('name'),
                        settlement_layer,
                        f.get('from_address'),
                        f.get('to_address'),
                        f.get('method'),
                        f.get('namespace') if settlement_layer == 'celestia' else None
                    ]
                    table.append(row)
except Exception as e:
    print("❌ ERROR: Failed to extract data from economics_mapping.yml")
    print(f"Error details: {e}")
    sys.exit(1)

# Create DataFrame
try:
    df = pd.DataFrame(table, columns=['l2', 'name', 'settlement_layer', 'from_address', 'to_address', 'method', 'namespace'])
except Exception as e:
    print("❌ ERROR: Failed to create DataFrame from extracted data")
    print(f"Error details: {e}")
    sys.exit(1)

# check for duplicate rows
duplicate_columns = ['l2', 'settlement_layer', 'from_address', 'to_address', 'method', 'namespace']
duplicates = df[df.duplicated(subset=duplicate_columns, keep=False)]
if not duplicates.empty:
    print("❌ ERROR: Duplicates found in economics_mapping.yml")
    print("Found duplicate entries:")
    print(duplicates)
    sys.exit(1)

# check for unsoported settlement layers
allowed_settlement_layers = ['beacon', 'l1', 'celestia', 'eigenda']
unsupported_settlement_layers = df[~df['settlement_layer'].isin(allowed_settlement_layers)]
if not unsupported_settlement_layers.empty:
    print("❌ ERROR: Unsupported settlement layers found in economics_mapping.yml")
    print("Found unsupported settlement layers:", unsupported_settlement_layers['settlement_layer'].unique().tolist())
    print(f"Was found in the following {len(unsupported_settlement_layers)} rows:")
    print(unsupported_settlement_layers)
    print("Please check the settlement_layer field in economics_mapping.yml")
    print("Allowed settlement layers are:", allowed_settlement_layers)
    sys.exit(1)

# check for valid addresses
def is_valid_address(address):
    if address is None:  # None is valid
        return True
    if len(address) == 42 and address.startswith('0x'):
        return True
    return False
columns_to_check = ['from_address', 'to_address']
invalid_addresses = df[columns_to_check].apply(lambda col: col.map(is_valid_address))
if not invalid_addresses.all().all():
    print("❌ ERROR: Invalid addresses found in the DataFrame")
    invalid_rows = df[~invalid_addresses.all(axis=1)]
    print("Invalid rows:")
    print(invalid_rows[columns_to_check + ['l2']])
    sys.exit(1)

# Ensure all required columns are None and not empty strings e.g. ""
required_columns = ['from_address', 'to_address', 'method', 'namespace']
missing_required = (df[required_columns] == "").any(axis=1)
if missing_required.any():
    print(f"❌ ERROR: No empty strings (e.g. \"\" or \'\') allowed in {required_columns} columns!")
    missing_rows = df[missing_required]
    print(f"Rows that violate this:")
    print(missing_rows[required_columns + ['l2']])
    sys.exit(1)

# make sure each row has at least one of these columns filled
required_columns = ['from_address', 'to_address', 'method', 'namespace']
missing_required = df[required_columns].isnull().all(axis=1)
if missing_required.any():
    print("❌ ERROR: Missing required columns in the DataFrame")
    missing_rows = df[missing_required]
    print(f"Rows with missing required columns (at least one of {required_columns}):")
    print(missing_rows)
    sys.exit(1)
    
# all checks passed
print("✅ Validation passed: No errors found in economics_mapping.yml")
