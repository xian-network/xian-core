import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from contracting.stdlib.bridge.decimal import ContractingDecimal

fallback = None  # Fallback value in case of error, None should be handled by the smart contracts as an error
pyth_url = "https://hermes.pyth.network/v2/updates/price/"
price_feed_btc_usd = "0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43"

# Set up a session with retries and timeouts
client = requests.session()

# Retry strategy configuration
retry_strategy = Retry(
    total=3,  # Total retries
    status_forcelist=[429, 500, 502, 503, 504],  # Retries for these HTTP statuses
    method_whitelist=["GET"],  # Only retry GET requests
    backoff_factor=1  # Wait time between retries (exponential backoff)
)

# Mount the adapter with the retry strategy
adapter = HTTPAdapter(max_retries=retry_strategy)
client.mount("https://", adapter)

client.headers.update({"Content-Type": "application/json"})
client.headers.update({"Accept": "application/json"})


def get_btc_usd(block_time):
    block_time = int(block_time)
    # Go 5 seconds back to ensure the price is available
    block_time -= 5
    try:
        # Properly format the URL using f-string
        response = client.get(
            f"{pyth_url}{block_time}?ids%5B%5D={price_feed_btc_usd}",
            timeout=3  # Timeout of 3 seconds for both connection and read
        )
        # Return the parsed price divided by 10^8
        price = response.json()["parsed"][0]["price"]["price"]
        price = ContractingDecimal(price) / ContractingDecimal(10 ** 8)
        return price
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")
        return fallback
