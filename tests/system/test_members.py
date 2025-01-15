import unittest
from contracting.stdlib.bridge.time import Datetime, Timedelta
from contracting.client import ContractingClient
import datetime
import os

class TestMembersContract(unittest.TestCase):
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
        
        # Deploy required contracts first with correct constructor args
        contract_args = {
            "currency": {"vk": self.deployer_vk},
            "stamp_cost": {"initial_rate": 20},
            "rewards": None,
            "dao": None
        }

        for contract in ["currency.s.py", "dao.s.py", "rewards.s.py", "stamp_cost.s.py"]:
            path = os.path.join(self.contracts_dir, contract)
            with open(path) as f:
                code = f.read()
                name = contract.split('.')[0]
                self.client.submit(code, name=name, constructor_args=contract_args[name])
        
        # Deploy members contract
        members_path = os.path.join(self.contracts_dir, "members.s.py")
        with open(members_path) as f:
            code = f.read()
            self.client.submit(code, name="members", constructor_args={
                "genesis_nodes": ["node1", "node2", "node3"],
                "genesis_registration_fee": 1000
            })

        self.members = self.client.get_contract("members")
        self.currency = self.client.get_contract("currency")

        # Add initial balance to deployer directly
        self.currency.balances[self.deployer_vk] = 100000

    def test_initial_setup(self):
        # GIVEN the initial setup from constructor
        # WHEN checking initial values
        nodes = self.members.nodes.get()
        fee = self.members.registration_fee.get()
        types = self.members.types.get()
        
        # THEN values should match constructor args
        self.assertEqual(len(nodes), 3)
        self.assertEqual(fee, 1000)
        self.assertTrue("add_member" in types)
        self.assertTrue("remove_member" in types)

    def test_register_new_member(self):
        # GIVEN sufficient funds for registration
        self.currency.approve(amount=1000, to="members", signer="new_member")
        self.currency.transfer(amount=1000, to="new_member", signer=self.deployer_vk)
        
        # WHEN registering
        self.members.register(signer="new_member")
        
        # THEN registration should be pending
        self.assertTrue(self.members.pending_registrations["new_member"])
        self.assertEqual(self.members.holdings["new_member"], 1000)

    def test_propose_and_approve_new_member(self):
        # GIVEN a pending registration
        self.currency.approve(amount=1000, to="members", signer="new_member")
        self.currency.transfer(amount=1000, to="new_member", signer=self.deployer_vk)
        self.members.register(signer="new_member")
        
        # WHEN proposing and voting
        self.members.propose_vote(
            type_of_vote="add_member",
            arg="new_member",
            signer="node1"
        )
        
        self.members.vote(proposal_id=1, vote="yes", signer="node2")
        self.members.vote(proposal_id=1, vote="yes", signer="node3")
        
        # THEN member should be added
        nodes = self.members.nodes.get()
        self.assertTrue("new_member" in nodes)

    def test_announce_and_leave(self):
        # GIVEN a node announcing leave
        current_time = Datetime(year=2024, month=1, day=1)
        self.members.announce_leave(signer="node1", environment={"now": current_time})
        
        # WHEN time passes (7 days + 1 hour to be safe)
        future_time = Datetime(year=2024, month=1, day=8, hour=1)
        
        self.members.leave(signer="node1", environment={"now": future_time})
        
        # THEN they should be removed from nodes
        nodes = self.members.nodes.get()
        self.assertTrue("node1" not in nodes)

    def test_vote_expiry(self):
        # GIVEN a pending vote
        self.currency.approve(amount=1000, to="members", signer="new_member")
        self.currency.transfer(amount=1000, to="new_member", signer=self.deployer_vk)
        self.members.register(signer="new_member")
        
        self.members.propose_vote(
            type_of_vote="add_member",
            arg="new_member",
            signer="node1",
            environment={"now": Datetime(year=2024, month=1, day=1)}
        )
        
        # WHEN trying to vote after expiry
        future_time = Datetime(
            year=2024, month=1, day=8
        )
        
        # THEN vote should fail
        with self.assertRaises(AssertionError):
            self.members.vote(
                proposal_id=1,
                vote="yes",
                signer="node2",
                environment={"now": future_time}
            )

    def test_balance_stream(self):
        # GIVEN a balance stream
        base_time = datetime.datetime.now()
        contracting_time = Datetime._from_datetime(base_time)
        future_time = contracting_time + Timedelta(days=7)
        
        dao_balance_before = self.currency.balances["dao"]
        self.members.balance_stream(signer="anybody", environment={"now": future_time})
        dao_balance_after = self.currency.balances["dao"]

        # THEN balance should be different
        self.assertNotEqual(dao_balance_before, dao_balance_after)