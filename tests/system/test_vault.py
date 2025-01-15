import unittest
from contracting.stdlib.bridge.time import Datetime
from contracting.client import ContractingClient
from contracting.storage.driver import Driver
import datetime
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
        
        # Set up paths and load contracts
        self.contracts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),'..', '..','src', 'xian', 'tools', 'genesis', 'contracts' ))
        
        # Deploy currency contract first (dependency)
        currency_path = os.path.join(self.contracts_dir, "currency.s.py")
        with open(currency_path) as f:
            code = f.read()
            self.client.submit(code, name="currency", constructor_args={"vk": self.deployer_vk})
        
        # Deploy vault contract
        vault_path = os.path.join(self.contracts_dir, "vault.s.py")
        with open(vault_path) as f:
            code = f.read()
            self.client.submit(code, name="team_lock", constructor_args={
                "initial_owners": "owner1,owner2,owner3",
                "initial_required_signatures": 2,
                "stream": "team_vesting"
            })

        self.vault = self.client.get_contract("team_lock")
        self.currency = self.client.get_contract("currency")

    def tearDown(self):
        self.client.flush()

    def test_initial_setup(self):
        # GIVEN the initial setup from constructor
        # WHEN checking initial values
        required_sigs = self.vault.required_signatures.get()
        owner_count = self.vault.owner_count.get()
        stream = self.vault.stream_id.get()
        
        # THEN values should match constructor args
        self.assertEqual(required_sigs, 2)
        self.assertEqual(owner_count, 3)
        self.assertEqual(stream, "team_vesting")
        self.assertTrue(self.vault.owners["owner1"])
        self.assertTrue(self.vault.owners["owner2"])
        self.assertTrue(self.vault.owners["owner3"])

    def test_submit_transaction(self):
        # GIVEN an owner submitting a transaction
        # WHEN submitting a new transaction
        result = self.vault.submit_transaction(
            to="receiver",
            amount=100,
            tx_type="transfer",
            signer="owner1"
        )

        # THEN transaction should be created with correct values
        tx_id = 1
        self.assertEqual(self.vault.transactions[tx_id, "type"], "transfer")
        self.assertEqual(self.vault.transactions[tx_id, "to"], "receiver")
        self.assertEqual(self.vault.transactions[tx_id, "amount"], 100)
        self.assertEqual(self.vault.transactions[tx_id, "executed"], False)
        self.assertEqual(self.vault.transactions[tx_id, "approvals"], 1)
        self.assertTrue(self.vault.transactions[tx_id, "approvers", "owner1"])

    def test_non_owner_cannot_submit_transaction(self):
        # GIVEN a non-owner trying to submit a transaction
        # WHEN/THEN should raise an exception
        with self.assertRaises(AssertionError):
            self.vault.submit_transaction(
                to="receiver",
                amount=100,
                tx_type="transfer",
                signer="non_owner"
            )

    def test_approve_transaction(self):
        # GIVEN a submitted transaction
        self.vault.submit_transaction(
            to="receiver",
            amount=100,
            tx_type="transfer",
            signer="owner1"
        )

        # WHEN another owner approves it
        self.vault.approve_transaction(tx_id=1, signer="owner2")

        # THEN approval should be recorded
        self.assertEqual(self.vault.transactions[1, "approvals"], 2)
        self.assertTrue(self.vault.transactions[1, "approvers", "owner2"])

    def test_execute_transaction_with_sufficient_approvals(self):
        # GIVEN a transaction with sufficient approvals
        # Fund the vault first
        self.currency.transfer(amount=1000, to="vault", signer=self.deployer_vk)
        
        self.vault.submit_transaction(
            to="receiver",
            amount=100,
            tx_type="transfer",
            signer="owner1"
        )
        self.vault.approve_transaction(tx_id=1, signer="owner2")

        # WHEN executing the transaction
        self.vault.execute_transaction(tx_id=1, signer="owner1")

        # THEN transaction should be executed
        self.assertTrue(self.vault.transactions[1, "executed"])
        self.assertEqual(self.currency.balances["receiver"], 100)

    def test_execute_transaction_without_sufficient_approvals(self):
        # GIVEN a transaction without sufficient approvals
        self.vault.submit_transaction(
            to="receiver",
            amount=100,
            tx_type="transfer",
            signer="owner1"
        )

        # WHEN/THEN execution should fail
        with self.assertRaises(AssertionError):
            self.vault.execute_transaction(tx_id=1, signer="owner1")

    def test_add_owner(self):
        # GIVEN a transaction to add a new owner
        self.vault.submit_transaction(
            to="new_owner",
            amount=None,
            tx_type="addOwner",
            signer="owner1"
        )
        self.vault.approve_transaction(tx_id=1, signer="owner2")

        # WHEN executing the transaction
        self.vault.execute_transaction(tx_id=1, signer="owner1")

        # THEN new owner should be added
        self.assertTrue(self.vault.owners["new_owner"])
        self.assertEqual(self.vault.owner_count.get(), 4)

    def test_remove_owner(self):
        # GIVEN a transaction to remove an owner
        self.vault.submit_transaction(
            to="owner3",
            amount=None,
            tx_type="removeOwner",
            signer="owner1"
        )
        self.vault.approve_transaction(tx_id=1, signer="owner2")

        # WHEN executing the transaction
        self.vault.execute_transaction(tx_id=1, signer="owner1")

        # THEN owner should be removed
        self.assertFalse(self.vault.owners["owner3"])
        self.assertEqual(self.vault.owner_count.get(), 2)

    def test_change_requirement(self):
        # GIVEN a transaction to change required signatures
        self.vault.submit_transaction(
            to=None,
            amount=3,
            tx_type="changeRequirement",
            signer="owner1"
        )
        self.vault.approve_transaction(tx_id=1, signer="owner2")

        # WHEN executing the transaction
        self.vault.execute_transaction(tx_id=1, signer="owner1")

        # THEN requirement should be updated
        self.assertEqual(self.vault.required_signatures.get(), 3)
        
    def test_balance_stream(self):
        # GIVEN a balance stream
        d = datetime.datetime.now() + datetime.timedelta(days=1)
        start_time = Datetime(d.year, d.month, d.day, hour=d.hour, minute=d.minute)
        balance_before = self.currency.balances["team_lock"]
        self.vault.balance_stream(signer="anybody", environment={**self.environment, "now":start_time})
        balance_after = self.currency.balances["team_lock"]

        # THEN balance should be updated
        self.assertNotEqual(balance_before, balance_after)
