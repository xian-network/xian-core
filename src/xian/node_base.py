from contracting.storage.encoder import encode
from contracting.storage.encoder import convert_dict

from xian.utils import verify, check_enough_stamps
from xian.exceptions import TransactionException
from xian.processor import TxProcessor
from xian.formatting import (
    TRANSACTION_PAYLOAD_RULES,
    TRANSACTION_RULES,
    contract_name_is_formatted
)

import marshal
import binascii


class Node:
    def __init__(self, client, nonce_storage):
        self.nonces = nonce_storage
        self.client = client
        self.tx_processor = TxProcessor(
            client=self.client
        )

    def validate_transaction(self, tx):
        # Check transaction formatting
        self.check_tx_formatting(tx)

        # Check if nonce is greater than the current nonce
        self.check_nonce(tx)

        # TODO: is this giving up to date value ? or is value only updated after hard_apply ?
        # Get the senders balance and the current stamp rate
        try:
            balance = self.client.get_var(
                contract="currency",
                variable="balances",
                arguments=[tx["payload"]["sender"]],
                mark=False
            )
        except Exception as e:
            raise TransactionException(f"Failed to retrieve 'currency' balance for sender: {e}")

        try:
            stamp_rate = self.client.get_var(
                contract="stamp_cost",
                variable="S",
                arguments=["value"],
                mark=False
            )
        except Exception as e:
            raise TransactionException(f"Failed to get stamp cost: {e}")

        contract = tx["payload"]["contract"]
        func = tx["payload"]["function"]
        stamps_supplied = tx["payload"]["stamps_supplied"]

        if stamps_supplied is None:
            stamps_supplied = 0

        if stamp_rate is None:
            stamp_rate = 0

        if balance is None:
            balance = 0

        # Get how much they are sending
        amount = tx["payload"]["kwargs"].get("amount")
        if amount is None:
            amount = 0

        # Check if they have enough stamps for the operation
        check_enough_stamps(
            balance,
            stamp_rate,
            stamps_supplied,
            contract=contract,
            function=func,
            amount=amount,
        )

        # Check if contract name is valid
        name = tx["payload"]["kwargs"].get("name")
        self.check_contract_name(contract, func, name)

    def check_contract_name(self, contract, function, name):
        if (
                contract == "submission"
                and function == "submit_contract"
                and (len(name) > 255 or not contract_name_is_formatted(name))
        ):
            raise TransactionException('Transaction contract name is invalid')

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
            raise TransactionException("Transaction has unexpected or missing keys")
        if not self.recurse_rules(d, rule):
            raise TransactionException("Transaction has wrongly formatted dictionary")

    def check_tx_keys(self, tx):
        metadata = tx.get("metadata")

        if not metadata:
            raise TransactionException("Metadata is missing")
        if len(metadata.keys()) != 1:
            raise TransactionException("Wrong number of metadata entries")

        payload = tx.get("payload")

        if not payload:
            raise TransactionException("Payload is missing")
        if not payload["sender"]:
            raise TransactionException("Payload key 'sender' is missing")
        if not payload["contract"]:
            raise TransactionException("Payload key 'contract' is missing")
        if not payload["function"]:
            raise TransactionException("Payload key 'function' is missing")
        if not payload["stamps_supplied"]:
            raise TransactionException("Payload key 'stamps_supplied' is missing")

        keys = list(payload.keys())
        keys_are_valid = list(
            map(lambda key: key in keys, list(TRANSACTION_PAYLOAD_RULES.keys()))
        )

        if not all(keys_are_valid) and len(keys) == len(list(TRANSACTION_PAYLOAD_RULES.keys())):
            raise TransactionException("Payload keys are not valid")

    def check_tx_formatting(self, tx: dict):
        self.check_tx_keys(tx)
        self.check_format(tx, TRANSACTION_RULES)

        if not verify(
                tx["payload"]["sender"], encode(tx["payload"]), tx["metadata"]["signature"]
        ):
            raise TransactionException('Transaction is not signed by the sender')

    def check_nonce(self, tx: dict):
        tx_nonce = tx["payload"]["nonce"]
        tx_sender = tx["payload"]["sender"]
        current_nonce = self.nonces.get_nonce(sender=tx_sender)

        if not (current_nonce is None or tx_nonce > current_nonce):
            raise TransactionException('Transaction nonce is invalid')

    def recompile_contract_from_source(self, s: dict):
        code = compile(s["value"], '', "exec")
        serialized_code = marshal.dumps(code)
        hexadecimal_string = binascii.hexlify(serialized_code).decode()
        return hexadecimal_string

    def apply_state_changes_from_block(self, block):
        state_changes = block.get('genesis', [])
        rewards = block.get('rewards', [])

        nanos = block.get('hlc_timestamp')

        for i, s in enumerate(state_changes):
            parts = s["key"].split(".")

            if parts[1] == "__code__":
                contract_key = f"{parts[0]}.__compiled__"
                print(f"processing {contract_key}")
                # the encoded contract data from genesis was invalid, so we recompile it.
                state_changes[i + 1]["value"]["__bytes__"] = self.recompile_contract_from_source(s)
            if type(s['value']) is dict:
                s['value'] = convert_dict(s['value'])

            self.client.raw_driver.set(s['key'], s['value'])

        for s in rewards:
            if type(s['value']) is dict:
                s['value'] = convert_dict(s['value'])

            self.client.raw_driver.set(s['key'], s['value'])

        self.client.raw_driver.hard_apply(nanos)

    async def store_genesis_block(self, genesis_block: dict):
        if genesis_block is not None:
            self.apply_state_changes_from_block(genesis_block)
