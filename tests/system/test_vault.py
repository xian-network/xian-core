import unittest
from contracting.stdlib.bridge.time import Datetime
from contracting.client import ContractingClient
import os

class TestVaultContract(unittest.TestCase):
    def setUp(self):
        # Bootstrap the environment
        self.chain_id = "test-chain"
        self.environment = {
            "chain_id": self.chain_id
        }
        self.deployer_vk = "xian-deployer"

        self.client = ContractingClient(environment=self.environment)
        self.client.flush()
        
        self.contracts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),'..', '..','src', 'xian', 'tools', 'genesis', 'contracts' ))
        
        # Deploy vault contract
        vault_path = os.path.join(self.contracts_dir, "vault.s.py")
        with open(vault_path) as f:
            code = f.read()
            self.client.submit(code, name="vault", constructor_args={
                "initial_owners": "owner1,owner2,owner3",
                "initial_required_signatures": 2,
                "stream": "test-stream"
            })

        self.vault = self.client.get_contract("vault")
        
        # Deploy currency contract
        currency_path = os.path.join(self.contracts_dir, "currency.s.py")
        with open(currency_path) as f:
            code = f.read()
            self.client.submit(code, name="currency", constructor_args={"vk": self.deployer_vk})

    def tearDown(self):
        self.client.flush()

    def test_submit_transaction(self):
        # GIVEN
        contract = "currency"
        function = "transfer"
        args = {"amount": 100, "to": "receiver"}

        # WHEN
        result = self.vault.submit_transaction(
            contract=contract,
            function=function,
            args=args,
            tx_type='external',
            signer="owner1"
        )

        # THEN
        tx_id = 1  # First transaction
        self.assertEqual(result, "Transaction 1 submitted.")
        self.assertEqual(self.vault.transactions[tx_id, 'type'], 'external')
        self.assertEqual(self.vault.transactions[tx_id, 'contract'], contract)
        self.assertEqual(self.vault.transactions[tx_id, 'function'], function)
        self.assertEqual(self.vault.transactions[tx_id, 'args'], args)
        self.assertEqual(self.vault.transactions[tx_id, 'executed'], False)
        self.assertEqual(self.vault.transactions[tx_id, 'approvals'], 1)

    def test_submit_transaction_non_owner(self):
        # GIVEN
        non_owner = "random_person"

        # WHEN/THEN
        with self.assertRaises(AssertionError):
            self.vault.submit_transaction(
                contract="currency",
                function="transfer",
                args={"amount": 100, "to": "receiver"},
                signer=non_owner
            )

    def test_approve_transaction(self):
        # GIVEN
        tx_id = 1
        self.vault.submit_transaction(
            contract="currency",
            function="transfer",
            args={"amount": 100, "to": "receiver"},
            tx_type='external',
            signer="owner1"
        )

        # WHEN
        result = self.vault.approve_transaction(tx_id=1, signer="owner2")

        # THEN
        self.assertEqual(result, "Transaction 1 approved by owner2.")
        self.assertEqual(self.vault.transactions[1, 'approvals'], 2)
        self.assertTrue(self.vault.transactions[1, 'approvers', 'owner2'])

    def test_approve_transaction_already_approved(self):
        # GIVEN
        tx_id = self.vault.submit_transaction(
            contract="currency",
            function="transfer",
            tx_type='external',
            args={"amount": 100, "to": "receiver"},
            signer="owner1"
        )

        # WHEN/THEN
        with self.assertRaises(AssertionError):
            self.vault.approve_transaction(tx_id=1, signer="owner1")  # owner1 already approved during submission

    def test_execute_transaction_insufficient_approvals(self):
        # GIVEN
        tx_id = self.vault.submit_transaction(
            contract="currency",
            function="transfer",
            args={"amount": 100, "to": "receiver"},
            signer="owner1"
        )

        # WHEN/THEN
        with self.assertRaises(AssertionError):
            self.vault.execute_transaction(tx_id=1, signer="owner1")  # Only 1 approval, needs 2

    def test_execute_transaction_success(self):
        # GIVEN
        # First deploy currency contract that we'll interact with
        currency_path = os.path.join(self.contracts_dir, "currency.s.py")
        with open(currency_path) as f:
            code = f.read()
            self.client.submit(code, name="currency", constructor_args={"vk": self.deployer_vk})

        # Submit and approve transaction
        tx_id = self.vault.submit_transaction(
            contract="currency",
            function="transfer",
            args={"amount": 100, "to": "receiver"},
            signer="owner1"
        )
        self.vault.approve_transaction(tx_id=1, signer="owner2")

        # WHEN
        result = self.vault.execute_transaction(tx_id=1, signer="owner1")

        # THEN
        self.assertTrue(self.vault.transactions[1, 'executed'])

    def test_execute_transaction_already_executed(self):
        # GIVEN
        tx_id = self.vault.submit_transaction(
            contract="currency",
            function="transfer",
            args={"amount": 100, "to": "receiver"},
            tx_type='external',
            signer="owner1"
        )
        self.vault.approve_transaction(tx_id=1, signer="owner2")
        self.vault.execute_transaction(tx_id=1, signer="owner1")
        breakpoint()
        # WHEN/THEN
        with self.assertRaises(AssertionError):
            self.vault.execute_transaction(tx_id=1, signer="owner1")

    def test_submit_add_owner_transaction(self):
        # GIVEN
        new_owner = "new_owner"
        
        # WHEN
        result = self.vault.submit_transaction(
            args={"address": new_owner},
            tx_type='addOwner',
            signer="owner1"
        )

        # THEN
        self.assertEqual(result, "Transaction 1 submitted.")
        self.assertEqual(self.vault.transactions[1, 'type'], 'addOwner')
        self.assertEqual(self.vault.transactions[1, 'args'], {"address": new_owner})

    def test_submit_remove_owner_transaction(self):
        # GIVEN
        owner_to_remove = "owner3"
        
        # WHEN
        result = self.vault.submit_transaction(
            args={"address": owner_to_remove},
            tx_type='removeOwner',
            signer="owner1"
        )

        # THEN
        self.assertEqual(result, "Transaction 1 submitted.")
        self.assertEqual(self.vault.transactions[1, 'type'], 'removeOwner')
        self.assertEqual(self.vault.transactions[1, 'args'], {"address": owner_to_remove})

    def test_submit_change_requirement_transaction(self):
        # GIVEN
        new_requirement = 3
        
        # WHEN
        result = self.vault.submit_transaction(
            args={"required": new_requirement},
            tx_type='changeRequirement',
            signer="owner1"
        )

        # THEN
        self.assertEqual(result, "Transaction 1 submitted.")
        self.assertEqual(self.vault.transactions[1, 'type'], 'changeRequirement')
        self.assertEqual(self.vault.transactions[1, 'args'], {"required": new_requirement})
