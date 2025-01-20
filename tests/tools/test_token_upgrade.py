import unittest
from contracting.stdlib.bridge.time import Datetime
from contracting.client import ContractingClient
from xian_py.decompiler import ContractDecompiler
import json
import os
from pathlib import Path
from xian.tools.genesis_upgrades.token_upgrade import process_genesis_data, find_code_entries, is_xsc001_token

class TestTokenUpgrade(unittest.TestCase):
    def setUp(self):
        self.client = ContractingClient()
        self.client.flush()
        
        # Load and process genesis file from fixtures
        current_dir = Path(__file__).parent
        genesis_path = current_dir / "fixtures/genesis.json"
        
        with open(genesis_path, 'r') as f:
            self.genesis_data = json.load(f)
        
        # Process genesis and get updated data
        self.updated_genesis, self.changes_made = process_genesis_data(self.genesis_data)
        
        # Find and submit all XSC001 tokens
        self.token_contracts = {}
        for idx, entry in enumerate(self.updated_genesis['abci_genesis']['genesis']):
            key = entry.get('key', '')
            if key.endswith('.__code__') and is_xsc001_token(entry['value']) and "pixel" not in key and key.startswith("con_"):
                contract_name = key.replace('.__code__', '')
                original_code = ContractDecompiler().decompile(entry['value'])
                print(f"Submitting {contract_name}")
                # Check if the code has a constructor argument for vk
                if "____(vk: str)" in original_code:
                    self.client.submit(original_code, name=contract_name, constructor_args={"vk": "sys"})
                else:
                    self.client.submit(original_code, name=contract_name)
                self.token_contracts[contract_name] = self.client.get_contract(contract_name)

    def tearDown(self):
        self.client.flush()

    def test_all_tokens_approve_functionality(self):
        """Test that all upgraded tokens have the updated approve functionality"""
        for contract_name, contract in self.token_contracts.items():
            with self.subTest(contract=contract_name):
                # Test approve
                contract.approve(amount=500, to="spender", signer="sys")
                
                # Check allowance
                allowance = contract.approvals["sys", "spender"]
                self.assertEqual(allowance, 500)
                
                # Test transfer_from with approval
                contract.transfer_from(
                    amount=100,
                    to="recipient",
                    main_account="sys",
                    signer="spender"
                )
                
                # Check balances and remaining allowance
                self.assertEqual(contract.balances["recipient"], 100)
                self.assertEqual(contract.approvals["sys", "spender"], 400)

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
                        signer="unauthorized"
                    )
                self.assertIn("Not enough coins approved to send", str(context.exception))

    def test_all_tokens_approve_overwrites(self):
        """Test that approve overwrites previous allowances"""
        for contract_name, contract in self.token_contracts.items():
            with self.subTest(contract=contract_name):
                # Initial approval
                contract.approve(amount=500, to="spender", signer="sys")
                self.assertEqual(contract.approvals["sys", "spender"], 500)
                
                # New approval should overwrite
                contract.approve(amount=200, to="spender", signer="sys")
                self.assertEqual(contract.approvals["sys", "spender"], 200)

    def test_all_tokens_balance_of_functionality(self):
        """Test that all tokens have the balance_of functionality working correctly"""
        for contract_name, contract in self.token_contracts.items():
            with self.subTest(contract=contract_name):
                # First set up some balances
                contract.transfer(amount=100, to="recipient", signer="sys")
                
                # Test balance_of for recipient
                recipient_balance = contract.balance_of(account="recipient")
                self.assertEqual(recipient_balance, 100)
                
                # Test balance_of for sys account
                sys_balance = contract.balance_of(account="sys")
                self.assertGreater(sys_balance, 0)  # sys should have some balance as initial holder
                
                # Test balance_of for non-existent account
                zero_balance = contract.balance_of(account="non_existent")
                self.assertEqual(zero_balance, 0)  # Should return default value of 0

if __name__ == "__main__":
    unittest.main()
