import re
from contracting.db.encoder import encode
from xian.utils import verify, has_enough_stamps
from xian.processor import TxProcessor
from xian.exceptions import (
    TransactionSignatureInvalid,
    TransactionNonceInvalid,
    TransactionFormattingError,
)
from xian.formatting import TRANSACTION_PAYLOAD_RULES, TRANSACTION_RULES, contract_name_is_valid


class Xian:
    def __init__(self, driver, nonce_storage):

        self.driver = driver
        self.nonces = nonce_storage
        self.tx_processor = TxProcessor(client = self.client, driver = self.driver)
        

    def validate_transaction(self, tx):
        return self.transaction_is_valid(tx, self.client, self.nonces)
    

    def set_nonce(self, tx):
        self.nonces.set_nonce(
        sender=tx['payload']['sender'],
        value=tx['payload']['nonce']
    )
        
    def dict_has_keys(self, d: dict, keys: set):
        key_set = set(d.keys())
        return len(keys ^ key_set) == 0
        
    def recurse_rules(self, d: dict, rule: dict):
        if callable(rule):
            return rule(d)

        for key, subrule in rule.items():
            arg = d[key]

            if type(arg) == dict:
                if not self.recurse_rules(arg, subrule):
                    return False

            elif type(arg) == list:
                for a in arg:
                    if not self.recurse_rules(a, subrule):
                        return False

            elif callable(subrule):
                if not subrule(arg):
                    return False

        return True


    def check_format(self, d: dict, rule: dict):
        expected_keys = set(rule.keys())

        if not self.dict_has_keys(d, expected_keys):
            return False

        return self.recurse_rules(d, rule)
        
    def check_tx_keys(self, tx):
        metadata = tx.get("metadata")
        if not metadata or len(metadata.keys()) != 1:
            print("Metadata is missing")
            return False
        payload = tx.get("payload")
        if not payload:
            print("Payload is missing")
            return False
        keys = list(payload.keys())
        keys_are_valid = list(
            map(lambda key: key in keys, list(TRANSACTION_PAYLOAD_RULES.keys()))
        )

        if not all(keys_are_valid) and len(keys) == len(list(TRANSACTION_PAYLOAD_RULES.keys())):
            print("Payload Keys are not valid")
            return False
        return True
        
    def check_tx_formatting(self, tx: dict):
        if not self.check_tx_keys(tx):
            print("Keys are not valid")
            raise TransactionFormattingError
        if not self.check_format(tx, TRANSACTION_RULES):
            print("Format is not valid")
            raise TransactionFormattingError
        if not verify(
            tx["payload"]["sender"], encode(tx["payload"]), tx["metadata"]["signature"]
        ):
            print("Signature is not valid")
            raise TransactionSignatureInvalid

        
    def check_nonce(self, tx: dict):
        tx_nonce = tx["payload"]["nonce"]
        tx_sender = tx["payload"]["sender"]
        current_nonce = self.nonces.get_nonce(sender=tx_sender)
        
        valid = current_nonce is None or tx_nonce > current_nonce

        if not valid:
            print("Nonce is wrong")
            raise TransactionNonceInvalid

        return valid
        
    # Run through all tests
    def transaction_is_valid(self,
        transaction,
        client,
        strict=True,
        tx_per_block=15,
        timeout=60,
    ):
        # Checks if correct processor and if signature is valid
        try:
            self.check_tx_formatting(transaction)
        except Exception as e:
            print(f"Check Tx Formatting Failed: {e}")
            return False
        
        # Put in to variables for visual ease
        if "payload" not in transaction:
            print("Payload is missing")
            return False
        if "sender" not in transaction["payload"]:
            print("Sender is missing")
            return False
        sender = transaction["payload"]["sender"]

        # Check the Nonce is greater than the current nonce we have
        try:
            self.check_nonce(tx=transaction, nonces=self.nonces)
        except Exception as e:
            print(f"Check Nonce Failed: {e}")
            return False
        
        # Get the senders balance and the current stamp rate
        try:
            balance = client.get_var(
                contract="currency", variable="balances", arguments=[sender], mark=False
            )  # is this giving up to date value ? or is value only updated after hard_apply ?
        except Exception as e:
            print(f"Get Currency Balance for Sender Failed: {e}")
            return False
        
        try:
            stamp_rate = client.get_var(
                contract="stamp_cost", variable="S", arguments=["value"], mark=False
            )

        except Exception as e:
            print(f"Get Stamp Cost Failed: {e}")
            return False
        
        if "contract" not in transaction["payload"]:
            print("Contract is missing")
            return False
        
        if "function" not in transaction["payload"]:
            print("Function is missing")
            return False
        
        if "stamps_supplied" not in transaction["payload"]:
            print("Stamps Supplied is missing")
            return False

        contract = transaction["payload"]["contract"]
        func = transaction["payload"]["function"]
        stamps_supplied = transaction["payload"]["stamps_supplied"]

        if stamps_supplied is None:
            stamps_supplied = 0

        if stamp_rate is None:
            stamp_rate = 0

        if balance is None:
            balance = 0

        # Get how much they are sending
        amount = transaction["payload"]["kwargs"].get("amount")
        if amount is None:
            amount = 0

        # Check if they have enough stamps for the operation
        try:
            has_enough_stamps(
                balance,
                stamp_rate,
                stamps_supplied,
                contract=contract,
                function=func,
                amount=amount,
            )
        except Exception as e:
            print(f"Checking if Sender has enough stamps failed: {e}")
            return False

        # Check if contract name is valid
        name = transaction["payload"]["kwargs"].get("name")
        try:
            contract_name_is_valid(contract, func, name)
        except Exception as e:
            print(f"Checking if Contract Name is valid failed: {e}")
            return False
        return True

    async def store_genesis_block(self, genesis_block: dict) -> bool:
        self.log.info('Processing Genesis Block.')
        await self.hard_apply_block(block=genesis_block)
