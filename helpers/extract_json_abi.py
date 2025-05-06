import os
import json
import requests
from datetime import datetime
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Ensure API keys are loaded
etherscan_api_key = os.getenv("ETHERSCAN_API")
infura_api = os.getenv("INFURA_API")

if not etherscan_api_key or not infura_api:
    raise ValueError("Missing API keys. Please check your .env file for ETHERSCAN_API and INFURA_API.")

# Construct the Infura provider URL
infura_provider_url = "https://mainnet.infura.io/v3/" + infura_api
print("Infura URL:", infura_provider_url)


def save_token_abi_and_creation_date(contract_address, api_key, provider_url):
    # Initialize Web3 instance and check connectivity
    web3 = Web3(Web3.HTTPProvider(provider_url))
    print("Attempting to connect to Ethereum node...")
    if not web3.is_connected():
        raise ConnectionError(
            "Failed to connect to Ethereum node. "
            "Please check your Infura API key, network connection, or consider using a different provider."
        )
    print("Connected to Ethereum node.")

    # Fetch the ABI from Etherscan
    etherscan_api_url = "https://api.etherscan.io/api"
    params = {
        'module': 'contract',
        'action': 'getabi',
        'address': contract_address,
        'apikey': api_key
    }
    print("Fetching contract ABI from Etherscan...")
    response = requests.get(etherscan_api_url, params=params)
    if response.status_code != 200:
        raise ValueError("Failed to fetch ABI. Check your API key or contract address.")

    data = response.json()
    if data.get('status') != '1':
        raise ValueError(f"Error from Etherscan API (ABI fetch): {data.get('message')}")

    abi = data['result']

    # Save the ABI to a JSON file
    try:
        with open("token_abi.json", "w") as abi_file:
            json.dump(json.loads(abi), abi_file, indent=4)
        print("ABI saved to token_abi.json")
    except Exception as e:
        raise IOError(f"Failed to write ABI to file: {e}")

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
    print("Fetching transaction list from Etherscan...")
    response = requests.get(etherscan_api_url, params=params)
    if response.status_code != 200:
        raise ValueError("Failed to fetch transaction list. Check your API key or contract address.")

    data = response.json()
    if data.get('status') != '1':
        raise ValueError(f"Error from Etherscan API (txlist fetch): {data.get('message')}")

    transactions = data['result']
    if not transactions:
        raise ValueError("No transactions found for this contract address.")

    # The first transaction in the sorted list should be the creation transaction
    creation_tx = transactions[0]

    # Get the timestamp of the creation transaction
    try:
        creation_timestamp = int(creation_tx['timeStamp'])
    except (KeyError, ValueError) as e:
        raise ValueError("Failed to parse transaction timestamp.") from e

    creation_date = datetime.utcfromtimestamp(creation_timestamp).strftime('%Y-%m-%d %H:%M:%S')
    print(f"Contract creation date (UTC): {creation_date}")

    return abi, creation_date


if __name__ == "__main__":
    # Specify the contract address to inspect
    contract_address = "0x6033f7f88332b8db6ad452b7c6d5bb643990ae3f"

    try:
        save_token_abi_and_creation_date(contract_address, etherscan_api_key, infura_provider_url)
    except Exception as e:
        print("An error occurred:", e)
