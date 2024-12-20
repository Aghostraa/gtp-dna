import requests
import yaml
import pandas as pd
import os

# define the header for DUNE Api
headers = {
    "X-DUNE-API-KEY": os.getenv('DUNE_KEY')
}

# create & save csv file
with open('economics_da/economics_mapping.yml') as f:
    data = yaml.load(f, Loader=yaml.FullLoader)
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
df = pd.DataFrame(table, columns=['l2', 'settlement_layer', 'from_address', 'to_address', 'method', 'namespace'])
df.to_csv('economics_mapping.csv', index=False)

# clear the current table:
url = "https://api.dune.com/api/v1/table/growthepie/l2economics_mapping/clear"
response = requests.request("POST", url, headers=headers)

# upload the new data
url = "https://api.dune.com/api/v1/table/growthepie/l2economics_mapping/insert"
headers['Content-Type'] = "text/csv"
with open("./economics_mapping.csv", "rb") as data:
  response = requests.request("POST", url, data=data, headers=headers)
  print("Total rows inserted:", response.json()['rows_written'])
  print("Total data size [bytes]:", response.json()['bytes_written'])
