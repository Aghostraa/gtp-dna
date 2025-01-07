import os
from web3 import Web3
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()


def save_token_abi_and_creation_date(contract_address, api_key, provider_url):
    web3 = Web3(Web3.HTTPProvider(provider_url))

    if not web3.is_connected():
        raise ConnectionError("Failed to connect to Ethereum node.")

    # Fetch the ABI from Etherscan
    etherscan_api_url = f"https://api.etherscan.io/api"
    params = {
        'module': 'contract',
        'action': 'getabi',
        'address': contract_address,
        'apikey': api_key
    }

    response = requests.get(etherscan_api_url, params=params)
    
    if response.status_code != 200:
        raise ValueError("Failed to fetch ABI. Check your API key or contract address.")

    data = response.json()

    if data['status'] != '1':
        raise ValueError(f"Error from Etherscan API: {data['message']}")

    abi = data['result']

    # Save the ABI to a JSON file
    with open("token_abi.json", "w") as abi_file:
        json.dump(json.loads(abi), abi_file, indent=4)

    print("ABI saved to token_abi.json")

    # Fetch the contract creation transaction
    params = {
        'module': 'account',
        'action': 'txlist',
        'address': contract_address,
        'startblock': 0,
        'endblock': 99999999,
        'sort': 'asc',
        'apikey': api_key
    }

    response = requests.get(etherscan_api_url, params=params)

    if response.status_code != 200:
        raise ValueError("Failed to fetch transaction list. Check your API key or contract address.")

    data = response.json()

    if data['status'] != '1':
        raise ValueError(f"Error from Etherscan API: {data['message']}")

    transactions = data['result']

    # The first transaction in the sorted list should be the creation transaction
    creation_tx = transactions[0]
    
    # Get the timestamp of the creation transaction
    creation_timestamp = int(creation_tx['timeStamp'])
    creation_date = datetime.utcfromtimestamp(creation_timestamp).strftime('%Y-%m-%d %H:%M:%S')

    print(f"Contract creation date (UTC): {creation_date}")

    return abi, creation_date

contract_address = "0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0"
etherscan_api_key = os.getenv("ETHERSCAN_API")
infura_provider_url = "https://mainnet.infura.io/v3/" + os.getenv("INFURA_API")

save_token_abi_and_creation_date(contract_address, etherscan_api_key, infura_provider_url)
