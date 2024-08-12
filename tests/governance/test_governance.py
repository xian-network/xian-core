import unittest
from contracting.storage.driver import Driver
from contracting.execution.executor import Executor
from contracting.constants import STAMPS_PER_TAU
from xian.processor import TxProcessor
from contracting.client import ContractingClient
import contracting
import random
import string
import os
import sys
from loguru import logger
from contracting.stdlib.bridge.time import Datetime
from fixtures.test_constants import TestConstants

# Get the directory where the script is located
script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

# Change the current working directory
os.chdir(script_dir)


def submission_kwargs_for_file(f):
    # Get the file name only by splitting off directories
    split = f.split("/")
    split = split[-1]

    # Now split off the .s
    split = split.split(".")
    contract_name = split[0]

    with open(f) as file:
        contract_code = file.read()

    return {
        "name": f"con_{contract_name}",
        "code": contract_code,
    }


TEST_SUBMISSION_KWARGS = {
    "sender": "stu",
    "contract_name": "submission",
    "function_name": "submit_contract",
}


class MyTestCase(unittest.TestCase):

    def setUp(self):
        self.c = ContractingClient(storage_home=TestConstants.STORAGE_HOME)
        self.tx_processor = TxProcessor(client=self.c)
        # Hard load the submission contract
        self.d = self.c.raw_driver
        self.d.flush_full()

        # Get the directory where the script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Construct absolute paths for the contract files
        submission_contract_path = os.path.abspath(
            os.path.join(
                script_dir,
                "../../xian-contracting/src/contracting/contracts/submission.s.py",
            )
        )
        currency_contract_path = os.path.abspath(
            os.path.join(
                script_dir,
                "../../src/xian/tools/genesis/contracts/currency.s.py",
            )
        )
        dao_contract_path = os.path.abspath(
            os.path.join(
                script_dir, "../../src/xian/tools/genesis/contracts/dao.s.py"
            )
        )
        rewards_contract_path = os.path.abspath(
            os.path.join(
                script_dir,
                "../../src/xian/tools/genesis/contracts/rewards.s.py",
            )
        )
        stamp_cost_contract_path = os.path.abspath(
            os.path.join(
                script_dir,
                "../../src/xian/tools/genesis/contracts/stamp_cost.s.py",
            )
        )
        members_contract_path = os.path.abspath(
            os.path.join(
                script_dir,
                "../../src/xian/tools/genesis/contracts/members.s.py",
            )
        )
        foundation_contract_path = os.path.abspath(
            os.path.join(
                script_dir,
                "../../src/xian/tools/genesis/contracts/foundation.s.py",
            )
        )

        with open(submission_contract_path) as f:
            contract = f.read()
        self.d.set_contract(name="submission", code=contract)

        with open(currency_contract_path) as f:
            contract = f.read()
        self.c.submit(
            contract,
            name="currency",
            constructor_args={
                "vk": "7fa496ca2438e487cc45a8a27fd95b2efe373223f7b72868fbab205d686be48e"
            },
        )
        self.d.set(
            key="currency.balances:7fa496ca2438e487cc45a8a27fd95b2efe373223f7b72868fbab205d686be48e",
            value=100000,
        )
        self.d.set(
            key="currency.balances:dff5d54d9c3cdb04d279c3c0a123d6a73a94e0725d7eac955fdf87298dbe45a6",
            value=100000,
        )
        self.d.set(
            key="currency.balances:6d2476cd66fa277b6077c76cdcd92733040dada2e12a28c3ebb08af44e12be76",
            value=100000,
        )
        self.d.set(
            key="currency.balances:b4d1967e6264bbcd61fd487caf3cafaffdc34be31d0994bf02afdcc2056c053c",
            value=100000,
        )
        self.d.set(
            key="currency.balances:db21a73137672f075f9a8ee142a1aa4839a5deb28ef03a10f3e7e16c87db8f24",
            value=100000,
        )
        self.d.set(key="currency.balances:new_node", value=1000000)

        with open(dao_contract_path) as f:
            contract = f.read()
        self.c.submit(contract, name="dao", owner="masternodes")

        with open(rewards_contract_path) as f:
            contract = f.read()
        self.c.submit(contract, name="rewards", owner="masternodes")
        self.d.set(key="rewards.S:value", value=[0.88, 0.01, 0.01, 0.1])

        with open(stamp_cost_contract_path) as f:
            contract = f.read()
        self.c.submit(contract, name="stamp_cost", owner="masternodes")
        self.d.set(key="stamp_cost.S:value", value=20)

        with open(members_contract_path) as f:
            contract = f.read()
        self.c.submit(
            contract,
            name="masternodes",
            constructor_args={
                "genesis_registration_fee": 100000,
                "genesis_nodes": [
                    "7fa496ca2438e487cc45a8a27fd95b2efe373223f7b72868fbab205d686be48e",
                    "dff5d54d9c3cdb04d279c3c0a123d6a73a94e0725d7eac955fdf87298dbe45a6",
                    "6d2476cd66fa277b6077c76cdcd92733040dada2e12a28c3ebb08af44e12be76",
                    "b4d1967e6264bbcd61fd487caf3cafaffdc34be31d0994bf02afdcc2056c053c",
                    "db21a73137672f075f9a8ee142a1aa4839a5deb28ef03a10f3e7e16c87db8f24",
                ],
            },
        )

        with open(foundation_contract_path) as f:
            contract = f.read()
        self.c.submit(
            contract,
            name="foundation",
            constructor_args={
                "vk": "7fa496ca2438e487cc45a8a27fd95b2efe373223f7b72868fbab205d686be48e"
            },
        )

        self.currency = self.c.get_contract("currency")
        self.dao = self.c.get_contract("dao")
        self.rewards = self.c.get_contract("rewards")
        self.stamp_cost = self.c.get_contract("stamp_cost")
        self.masternodes = self.c.get_contract("masternodes")

    def tearDown(self):
        self.d.flush_full()

    def register(self):
        approve_currency = self.tx_processor.process_tx(
            tx={
                "payload": {
                    "sender": "new_node",
                    "contract": "currency",
                    "function": "approve",
                    "kwargs": {"amount": 100000, "to": "masternodes"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": {"nanos": 0, "hash": "0x0", "height": 0, "chain_id": "test-chain"},
            }
        )
        register_node = self.tx_processor.process_tx(
            tx={
                "payload": {
                    "sender": "new_node",
                    "contract": "masternodes",
                    "function": "register",
                    "kwargs": {},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": {"nanos": 0, "hash": "0x0", "height": 0, "chain_id": "test-chain"},
            }
        )

    def unregister(self):
        unregister_node = self.tx_processor.process_tx(
            tx={
                "payload": {
                    "sender": "new_node",
                    "contract": "masternodes",
                    "function": "unregister",
                    "kwargs": {},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": {"nanos": 0, "hash": "0x0", "height": 0, "chain_id": "test-chain"},
            }
        )

    def vote_in(self):
        vote = self.tx_processor.process_tx(
            tx={
                "payload": {
                    "sender": "7fa496ca2438e487cc45a8a27fd95b2efe373223f7b72868fbab205d686be48e",
                    "contract": "masternodes",
                    "function": "propose_vote",
                    "kwargs": {"type_of_vote": "add_member", "arg": "new_node"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": {"nanos": 0, "hash": "0x0", "height": 0, "chain_id": "test-chain"},
            }
        )
        vote2 = self.tx_processor.process_tx(
            tx={
                "payload": {
                    "sender": "dff5d54d9c3cdb04d279c3c0a123d6a73a94e0725d7eac955fdf87298dbe45a6",
                    "contract": "masternodes",
                    "function": "vote",
                    "kwargs": {"proposal_id": 1, "vote": "yes"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": {"nanos": 0, "hash": "0x0", "height": 0, "chain_id": "test-chain"},
            }
        )

    def vote_out(self):
        vote = self.tx_processor.process_tx(
            tx={
                "payload": {
                    "sender": "7fa496ca2438e487cc45a8a27fd95b2efe373223f7b72868fbab205d686be48e",
                    "contract": "masternodes",
                    "function": "propose_vote",
                    "kwargs": {
                        "type_of_vote": "remove_member",
                        "arg": "new_node",
                    },
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": {"nanos": 0, "hash": "0x0", "height": 0, "chain_id": "test-chain"},
            }
        )
        vote2 = self.tx_processor.process_tx(
            tx={
                "payload": {
                    "sender": "dff5d54d9c3cdb04d279c3c0a123d6a73a94e0725d7eac955fdf87298dbe45a6",
                    "contract": "masternodes",
                    "function": "vote",
                    "kwargs": {"proposal_id": 2, "vote": "yes"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": {"nanos": 0, "hash": "0x0", "height": 0, "chain_id": "test-chain"},
            }
        )
        vote3 = self.tx_processor.process_tx(
            tx={
                "payload": {
                    "sender": "6d2476cd66fa277b6077c76cdcd92733040dada2e12a28c3ebb08af44e12be76",
                    "contract": "masternodes",
                    "function": "vote",
                    "kwargs": {"proposal_id": 2, "vote": "yes"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": {"nanos": 0, "hash": "0x0", "height": 0, "chain_id": "test-chain"},
            }
        )

    def vote_stamp_cost(self):
        vote = self.tx_processor.process_tx(
            tx={
                "payload": {
                    "sender": "7fa496ca2438e487cc45a8a27fd95b2efe373223f7b72868fbab205d686be48e",
                    "contract": "masternodes",
                    "function": "propose_vote",
                    "kwargs": {"type_of_vote": "stamp_cost_change", "arg": 30},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": {"nanos": 0, "hash": "0x0", "height": 0, "chain_id": "test-chain"},
            }
        )
        vote2 = self.tx_processor.process_tx(
            tx={
                "payload": {
                    "sender": "dff5d54d9c3cdb04d279c3c0a123d6a73a94e0725d7eac955fdf87298dbe45a6",
                    "contract": "masternodes",
                    "function": "vote",
                    "kwargs": {"proposal_id": 1, "vote": "yes"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": {"nanos": 0, "hash": "0x0", "height": 0, "chain_id": "test-chain"},
            }
        )

    def vote_reward_change(self):
        vote = self.tx_processor.process_tx(
            tx={
                "payload": {
                    "sender": "7fa496ca2438e487cc45a8a27fd95b2efe373223f7b72868fbab205d686be48e",
                    "contract": "masternodes",
                    "function": "propose_vote",
                    "kwargs": {
                        "type_of_vote": "reward_change",
                        "arg": [0.78, 0.11, 0.01, 0.1],
                    },
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": {"nanos": 0, "hash": "0x0", "height": 0, "chain_id": "test-chain"},
            }
        )
        vote2 = self.tx_processor.process_tx(
            tx={
                "payload": {
                    "sender": "dff5d54d9c3cdb04d279c3c0a123d6a73a94e0725d7eac955fdf87298dbe45a6",
                    "contract": "masternodes",
                    "function": "vote",
                    "kwargs": {"proposal_id": 1, "vote": "yes"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": {"nanos": 0, "hash": "0x0", "height": 0, "chain_id": "test-chain"},
            }
        )

    def vote_dao_payout(self):
        vote = self.tx_processor.process_tx(
            tx={
                "payload": {
                    "sender": "7fa496ca2438e487cc45a8a27fd95b2efe373223f7b72868fbab205d686be48e",
                    "contract": "masternodes",
                    "function": "propose_vote",
                    "kwargs": {
                        "type_of_vote": "dao_payout",
                        "arg": {"amount": 100000, "to": "new_node"},
                    },
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": {"nanos": 0, "hash": "0x0", "height": 0, "chain_id": "test-chain"},
            }
        )
        vote2 = self.tx_processor.process_tx(
            tx={
                "payload": {
                    "sender": "dff5d54d9c3cdb04d279c3c0a123d6a73a94e0725d7eac955fdf87298dbe45a6",
                    "contract": "masternodes",
                    "function": "vote",
                    "kwargs": {"proposal_id": 1, "vote": "yes"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": {"nanos": 0, "hash": "0x0", "height": 0, "chain_id": "test-chain"},
            }
        )

    def vote_reg_fee_change(self):
        vote = self.tx_processor.process_tx(
            tx={
                "payload": {
                    "sender": "7fa496ca2438e487cc45a8a27fd95b2efe373223f7b72868fbab205d686be48e",
                    "contract": "masternodes",
                    "function": "propose_vote",
                    "kwargs": {
                        "type_of_vote": "change_registration_fee",
                        "arg": 200000,
                    },
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": {"nanos": 0, "hash": "0x0", "height": 0, "chain_id": "test-chain"},
            }
        )
        vote2 = self.tx_processor.process_tx(
            tx={
                "payload": {
                    "sender": "dff5d54d9c3cdb04d279c3c0a123d6a73a94e0725d7eac955fdf87298dbe45a6",
                    "contract": "masternodes",
                    "function": "vote",
                    "kwargs": {"proposal_id": 1, "vote": "yes"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": {"nanos": 0, "hash": "0x0", "height": 0, "chain_id": "test-chain"},
            }
        )

    def vote_types_change(self):
        vote = self.tx_processor.process_tx(
            tx={
                "payload": {
                    "sender": "7fa496ca2438e487cc45a8a27fd95b2efe373223f7b72868fbab205d686be48e",
                    "contract": "masternodes",
                    "function": "propose_vote",
                    "kwargs": {
                        "type_of_vote": "change_types",
                        "arg": [
                            "new_type1",
                            "new_type2",
                            "new_type3",
                            "new_type4",
                        ],
                    },
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": {"nanos": 0, "hash": "0x0", "height": 0, "chain_id": "test-chain"},
            }
        )
        vote2 = self.tx_processor.process_tx(
            tx={
                "payload": {
                    "sender": "dff5d54d9c3cdb04d279c3c0a123d6a73a94e0725d7eac955fdf87298dbe45a6",
                    "contract": "masternodes",
                    "function": "vote",
                    "kwargs": {"proposal_id": 1, "vote": "yes"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": {"nanos": 0, "hash": "0x0", "height": 0, "chain_id": "test-chain"},
            }
        )

    def announce_leave(self):
        announce = self.tx_processor.process_tx(
            tx={
                "payload": {
                    "sender": "new_node",
                    "contract": "masternodes",
                    "function": "announce_leave",
                    "kwargs": {},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": {"nanos": 0, "hash": "0x0", "height": 0, "chain_id": "test-chain"},
            }
        )

    def leave(self):
        leave = self.tx_processor.process_tx(
            tx={
                "payload": {
                    "sender": "new_node",
                    "contract": "masternodes",
                    "function": "leave",
                    "kwargs": {},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": {
                    "nanos": 99999999999999999999,
                    "hash": "0x0",
                    "height": 0,
                    "chain_id": "test-chain",
                },
            }
        )

    def test_register(self):
        self.register()
        self.assertEqual(
            self.masternodes.pending_registrations["new_node"], True
        )
        self.assertEqual(self.currency.balances["new_node"], 900000)

    def test_unregister(self):
        self.register()
        self.unregister()
        self.assertEqual(
            self.masternodes.pending_registrations["new_node"], False
        )
        self.assertEqual(self.currency.balances["new_node"], 1000000)

    def test_vote_in_node(self):
        self.register()
        self.vote_in()
        self.assertEqual(self.masternodes.votes[1]["yes"], 2)
        self.assertEqual(self.masternodes.votes[1]["no"], 0)
        self.assertEqual(self.masternodes.votes[1]["finalized"], True)
        nodes = self.masternodes.nodes.get()
        self.assertIn("new_node", nodes)

    def test_vote_out_node(self):
        self.register()
        self.vote_in()
        self.vote_out()
        self.assertEqual(self.masternodes.votes[2]["yes"], 3)
        self.assertEqual(self.masternodes.votes[2]["no"], 0)
        self.assertEqual(self.masternodes.votes[2]["finalized"], True)
        nodes = self.masternodes.nodes.get()
        self.assertNotIn("new_node", nodes)

    def test_announce_leave(self):
        self.register()
        self.vote_in()
        self.announce_leave()

    def test_leave(self):
        self.register()
        self.vote_in()
        self.announce_leave()
        self.leave()
        self.assertEqual(self.masternodes.pending_leave["new_node"], False)

    def test_force_leave(self):
        self.register()
        self.vote_in()
        self.vote_out()
        self.leave()
        self.assertEqual(self.masternodes.pending_leave["new_node"], False)

    def test_leave_payback(self):
        self.register()
        self.vote_in()
        self.announce_leave()
        self.leave()
        self.unregister()
        self.assertEqual(self.currency.balances["new_node"], 1000000)

    def test_force_leave_payback(self):
        self.register()
        self.vote_in()
        self.vote_out()
        self.leave()
        self.unregister()
        self.assertEqual(self.currency.balances["new_node"], 1000000)

    def test_stamp_rate_vote(self):
        self.assertEqual(self.stamp_cost.S["value"], 20)
        self.vote_stamp_cost()
        self.assertEqual(self.masternodes.votes[1]["yes"], 2)
        self.assertEqual(self.masternodes.votes[1]["no"], 0)
        self.assertEqual(self.masternodes.votes[1]["finalized"], True)
        self.assertEqual(self.stamp_cost.S["value"], 30)

    def test_reward_change_vote(self):
        self.assertEqual(self.rewards.S["value"], [0.88, 0.01, 0.01, 0.1])
        self.vote_reward_change()
        self.assertEqual(self.masternodes.votes[1]["yes"], 2)
        self.assertEqual(self.masternodes.votes[1]["no"], 0)
        self.assertEqual(self.masternodes.votes[1]["finalized"], True)
        self.assertEqual(self.rewards.S["value"], [0.78, 0.11, 0.01, 0.1])

    def test_dao_payout(self):
        self.assertEqual(self.currency.balances["new_node"], 1000000)
        self.vote_dao_payout()
        self.assertEqual(self.masternodes.votes[1]["yes"], 2)
        self.assertEqual(self.masternodes.votes[1]["no"], 0)
        self.assertEqual(self.masternodes.votes[1]["finalized"], True)
        self.assertEqual(self.currency.balances["new_node"], 1100000)

    def test_reg_fee_change(self):
        self.assertEqual(self.masternodes.registration_fee.get(), 100000)
        self.vote_reg_fee_change()
        self.assertEqual(self.masternodes.votes[1]["yes"], 2)
        self.assertEqual(self.masternodes.votes[1]["no"], 0)
        self.assertEqual(self.masternodes.votes[1]["finalized"], True)
        self.assertEqual(self.masternodes.registration_fee.get(), 200000)

    def test_types_change(self):
        self.assertEqual(
            self.masternodes.types.get(),
            [
                "add_member",
                "remove_member",
                "change_registration_fee",
                "reward_change",
                "dao_payout",
                "stamp_cost_change",
                "change_types",
            ],
        )
        self.vote_types_change()
        self.assertEqual(self.masternodes.votes[1]["yes"], 2)
        self.assertEqual(self.masternodes.votes[1]["no"], 0)
        self.assertEqual(self.masternodes.votes[1]["finalized"], True)
        self.assertEqual(
            self.masternodes.types.get(),
            ["new_type1", "new_type2", "new_type3", "new_type4"],
        )


if __name__ == "__main__":
    unittest.main()
