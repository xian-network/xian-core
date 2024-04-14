import time
from web3 import Web3, exceptions

class ETHQuery:
    ETH_RPC = "https://cloudflare-eth.com"

    def __init__(self):
        self.web3 = Web3(Web3.HTTPProvider(self.ETH_RPC))
        if not self.web3.is_connected():
            raise ConnectionError("Failed to connect to Ethereum node.")

    def retry_logic(self, func, *args, retries=3, delay=1):
        last_exception = None
        for attempt in range(retries):
            try:
                return func(*args)
            except exceptions.ContractLogicError as e:
                last_exception = e
                print(f"Contract logic error on attempt {attempt+1}: {e}")
            except exceptions.BadFunctionCallOutput as e:
                last_exception = e
                print(f"Function call failed on attempt {attempt+1}: {e}")
            except Exception as e:
                last_exception = e
                print(f"Unexpected error on attempt {attempt+1}: {e}")
            time.sleep(delay * (2 ** attempt))  # Exponential back-off
        return None, last_exception  # Returns None and the last exception on failure

    def call_contract(self, abi, contract_address, data):
        func = lambda: self.web3.eth.contract(address=contract_address, abi=abi).functions[data].call()
        result, exception = self.retry_logic(func)
        if exception:
            return f"Error after final attempt: {exception}"
        return result

    def get_block(self, block_number):
        func = lambda: self.web3.eth.get_block(block_number, full_transactions=True)
        result, exception = self.retry_logic(func)
        if exception:
            return f"Error after final attempt: {exception}"
        return result

    def get_block_by_hash(self, block_hash):
        func = lambda: self.web3.eth.get_block(block_hash, full_transactions=True)
        result, exception = self.retry_logic(func)
        if exception:
            return f"Error after final attempt: {exception}"
        return result

    def get_transaction(self, tx_hash):
        func = lambda: self.web3.eth.get_transaction(tx_hash)
        result, exception = self.retry_logic(func)
        if exception:
            return f"Error after final attempt: {exception}"
        return result

    def get_receipt(self, tx_hash):
        func = lambda: self.web3.eth.get_transaction_receipt(tx_hash)
        result, exception = self.retry_logic(func)
        if exception:
            return f"Error after final attempt: {exception}"
        return result
