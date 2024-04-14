import time
from web3 import Web3, exceptions

class ETHQuery:

    def __init__(self, eth_rpc="https://cloudflare-eth.com", contract_address="0x1b44F3514812d835EB1BDB0acB33d3fA3351Ee43", abi_path="eth_abi/btcusd.json"):
        self.web3 = Web3(Web3.HTTPProvider(eth_rpc))
        self.contract_address = contract_address
        with open(abi_path, "r") as f:
            self.abi = f.read()
        if not self.web3.is_connected():
            raise ConnectionError("Failed to connect to Ethereum node.")

    def retry_logic(self, func, *args, retries=3, delay=1):
        last_exception = None
        for attempt in range(retries):
            try:
                result = func(*args)  # Attempt to call the function
                return result, None  # Return the result and None for exception if successful
            except exceptions.ContractLogicError as e:
                last_exception = e
                print(f"Contract logic error on attempt {attempt+1}: {e}")
            except exceptions.BadFunctionCallOutput as e:
                last_exception = e
                print(f"Function call failed on attempt {attempt+1}: {e}")
            except Exception as e:
                last_exception = e
                print(f"Unexpected error on attempt {attempt+1}: {e}")
            time.sleep(delay)
        return None, last_exception  # Only return None and the last exception after all retries fail

    def call_contract(self, function_name):
        func = lambda: self.web3.eth.contract(address=self.contract_address, abi=self.abi).functions[function_name]().call()
        result, exception = self.retry_logic(func)
        if exception:
            return None # After all retries fail, return None
        return result