import requests
import os

api_key = os.getenv('DUNE_KEY')
if not api_key:
    raise ValueError("API Key not set. Ensure DUNE_KEY is configured correctly.")

headers = {
    "X-DUNE-API-KEY": api_key,
    "Content-Type": "application/json"
}

# Delete the existing table (ignore 404 if it doesn't exist yet)
delete_url = "https://api.dune.com/api/v1/table/growthepie/l2economics_mapping"
delete_response = requests.delete(delete_url, headers=headers)
if delete_response.ok:
    print("Existing table deleted.")
elif delete_response.status_code == 404:
    print("Table does not exist yet, skipping delete.")
else:
    raise RuntimeError(f"Dune API table deletion failed: {delete_response.json()}")

# Create the table with the schema matching economics_mapping.csv
url = "https://api.dune.com/api/v1/table/create"
payload = {
    "namespace": "growthepie",
    "table_name": "l2economics_mapping",
    "description": "Mapping of L2 chains to their settlement and DA contracts/methods",
    "is_private": False,
    "schema": [
        {"name": "l2",               "type": "varchar"},
        {"name": "name",             "type": "varchar"},
        {"name": "settlement_layer", "type": "varchar"},
        {"name": "from_address",     "type": "varbinary"},
        {"name": "to_address",       "type": "varbinary"},
        {"name": "method",           "type": "varbinary"},
        {"name": "namespace",        "type": "varchar"},
        {"name": "start_block",      "type": "bigint"},
        {"name": "end_block",        "type": "bigint"}
    ]
}

response = requests.post(url, json=payload, headers=headers)
result = response.json()
print(result)

if not response.ok:
    raise RuntimeError(f"Dune API table creation failed: {result}")

print("Table created successfully.")
