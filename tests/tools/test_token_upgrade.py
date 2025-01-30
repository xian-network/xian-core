import unittest
from contracting.stdlib.bridge.time import Datetime
from contracting.client import ContractingClient
from xian.utils.block import compile_contract_from_source
from xian_py.decompiler import ContractDecompiler
from xian_py.wallet import Wallet
from contracting.stdlib.bridge.hashing import sha3
import datetime
import json
import os
from pathlib import Path
from xian.tools.genesis_upgrades.token_upgrade import (
    process_genesis_data,
    find_code_entries,
    is_xsc001_token,
)


class TestTokenUpgrade(unittest.TestCase):
    def setUp(self):
        self.client = ContractingClient()
        self.client.flush()

        # Load and process genesis file from fixtures
        current_dir = Path(__file__).parent
        genesis_path = current_dir / "fixtures/genesis.json"

        with open(genesis_path, "r") as f:
            self.genesis_data = json.load(f)

        # Process genesis and get updated data
        self.updated_genesis, self.changes_made = process_genesis_data(
            self.genesis_data
        )

        # These contracts are broken and need to be excluded
        self.EXCLUDED_CONTRACTS = [
            "con_snake.__code__",
            "con_xfinxty.__code__",
            "con_stk.__code__",
            "con_stk001.__code__",
            "con_stk5.__code__",
            "con_stk6.__code__",
            "con_stk003.__code__",
            "con_stk005.__code__",
            "con_stk006.__code__",
        ]

        # Find and submit all XSC001 tokens
        self.token_contracts = {}
        for idx, entry in enumerate(
            self.updated_genesis["abci_genesis"]["genesis"]
        ):
            key = entry.get("key", "")
            if (
                key.endswith(".__code__")
                and is_xsc001_token(entry["value"])
                and "pixel" not in key
                and key.startswith("con_")
                and key not in self.EXCLUDED_CONTRACTS
            ):

                contract_name = key.replace(".__code__", "")
                print(f"Submitting {contract_name}")
                compiled_code = compile_contract_from_source(entry)
                self.client.raw_driver.set(
                    f"{contract_name}.__compiled__", compiled_code
                )
                self.client.raw_driver.set(key, entry.get("value"))
                self.token_contracts[contract_name] = self.client.get_contract(
                    contract_name
                )
            else:
                self.client.raw_driver.set(key, entry.get("value"))

    def tearDown(self):
        self.client.flush()

    def test_all_tokens_approve_functionality(self):
        """Test that all upgraded tokens have the updated approve functionality"""
        for contract_name, contract in self.token_contracts.items():
            with self.subTest(contract=contract_name):
                # Test approve
                contract.balances["sys"] = 10000000
                contract.approve(amount=500, to="spender", signer="sys")

                # Check allowance
                allowance = contract.balances["sys", "spender"]
                self.assertEqual(allowance, 500)

                # Test transfer_from with approval
                contract.transfer_from(
                    amount=100,
                    to="recipient",
                    main_account="sys",
                    signer="spender",
                )


                    # Check balances and remaining allowance
                self.assertEqual(contract.balances["recipient"], 100)
                self.assertEqual(contract.balances["sys", "spender"], 400)

    def test_all_tokens_transfer_from_validation(self):
        """Test that all upgraded tokens properly validate transfer_from operations"""
        for contract_name, contract in self.token_contracts.items():
            with self.subTest(contract=contract_name):
                # Try transfer_from without approval
                with self.assertRaises(Exception) as context:
                    contract.transfer_from(
                        amount=100,
                        to="recipient",
                        main_account="sys",
                        signer="unauthorized",
                    )
                self.assertIn(
                    "Not enough coins approved to send", str(context.exception)
                )

    def test_all_tokens_approve_overwrites(self):
        """Test that approve overwrites previous allowances"""
        for contract_name, contract in self.token_contracts.items():
            with self.subTest(contract=contract_name):
                # Initial approval
                contract.approve(amount=500, to="spender", signer="sys")
                self.assertEqual(contract.balances["sys", "spender"], 500)

                # New approval should overwrite
                contract.approve(amount=200, to="spender", signer="sys")
                self.assertEqual(contract.balances["sys", "spender"], 200)

    def test_all_tokens_balance_of_functionality(self):
        """Test that all tokens have the balance_of functionality working correctly"""
        for contract_name, contract in self.token_contracts.items():
            with self.subTest(contract=contract_name):
                # First set up some balances
                contract.balances["sys"] = 10000000
                contract.transfer(amount=100, to="recipient", signer="sys")

                # Test balance_of for recipient
                recipient_balance = contract.balance_of(address="recipient")
                self.assertEqual(recipient_balance, 100)

                # Test balance_of for sys account
                sys_balance = contract.balance_of(address="sys")
                self.assertGreater(
                    sys_balance, 0
                )  # sys should have some balance as initial holder

                # Test balance_of for non-existent account
                zero_balance = contract.balance_of(address="non_existent")
                self.assertEqual(
                    zero_balance, 0
                )  # Should return default value of 0

    def test_all_xsc002_tokens_permit_functionality(self):
        """Test that all upgraded tokens have the updated permit functionality"""
        for contract_name, contract in self.token_contracts.items():
            with self.subTest(contract=contract_name):
                private_key = "ed30796abc4ab47a97bfb37359f50a9c362c7b304a4b4ad1b3f5369ecb6f7fd8"
                wallet = Wallet(private_key)
                public_key = wallet.public_key
                deadline = create_deadline()
                spender = "some_spender"
                value = 100
                chain_id = "test-chain"
                msg = construct_permit_msg(
                    public_key,
                    spender,
                    value,
                    deadline,
                    contract_name,
                    chain_id,
                )
                hash = sha3(msg)
                signature = wallet.sign_msg(msg)

                if vars(contract).get("permit") is not None:
                    response = contract.permit(
                        owner=public_key,
                        spender=spender,
                        value=value,
                        deadline=str(deadline),
                        signature=signature,
                        environment={"chain_id": chain_id},
                    )
                    self.assertEqual(response, hash)


def construct_permit_msg(
    owner: str,
    spender: str,
    value: float,
    deadline: dict,
    contract_name: str,
    chain_id: str,
):
    return f"{owner}:{spender}:{value}:{deadline}:{contract_name}:{chain_id}"


def create_deadline(minutes=1):
    d = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
    return Datetime(d.year, d.month, d.day, hour=d.hour, minute=d.minute)


if __name__ == "__main__":
    unittest.main()
