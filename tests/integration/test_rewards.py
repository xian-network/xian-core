import unittest
from contracting.storage.driver import Driver
from contracting.execution.executor import Executor
from contracting.constants import STAMPS_PER_TAU
from xian.processor import TxProcessor
from xian.rewards import RewardsHandler
from contracting.client import ContractingClient
import contracting
import random
import string
import os
import sys
from pathlib import Path
from loguru import logger
from contracting.stdlib.bridge.time import Datetime

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

from datetime import datetime, timedelta
import time

def create_block_meta(dt: datetime):
    # Get the current time in nanoseconds
    nanos = int(time.mktime(dt.timetuple()) * 1e9 + dt.microsecond * 1e3)
    # Mock b_meta dictionary with current nanoseconds
    return {
        "nanos": nanos,                # Current nanoseconds timestamp
        "height": 123456,              # Example block number
        "chain_id": "test-chain",      # Example chain ID
        "hash": "abc123def456"         # Example block hash
    }


class MyTestCase(unittest.TestCase):

    def setUp(self):
        self.c = ContractingClient(storage_home=Path.home() / Path('/tmp/cometbft/') / Path('xian/'))
        self.tx_processor = TxProcessor(client=self.c)
        self.rewards_handler = RewardsHandler(client=self.c)
        # Hard load the submission contract
        self.d = self.c.raw_driver
        self.d.flush_full()

        # Get the directory where the script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Construct absolute paths for the contract files
        submission_contract_path = os.path.abspath(
            os.path.join(
                script_dir,
                "../../contracting/src/contracting/contracts/submission.s.py",
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
                ],
            },
        )

        with open(foundation_contract_path) as f:
            contract = f.read()
        self.c.submit(
            contract,
            name="foundation",
            constructor_args={
                "vk": "7fa496ca2438e487cc45a8a27fd95b2efe373223f7b72868fbab205d686be48e",
            },
        )

        self.currency = self.c.get_contract("currency")
        self.dao = self.c.get_contract("dao")
        self.rewards = self.c.get_contract("rewards")
        self.stamp_cost = self.c.get_contract("stamp_cost")
        self.masternodes = self.c.get_contract("masternodes")

    def tearDown(self):
        self.d.flush_full()

    def test_rewards(self):
        transfer = self.tx_processor.process_tx(
            tx={
                "payload": {
                    "sender": "7fa496ca2438e487cc45a8a27fd95b2efe373223f7b72868fbab205d686be48e",
                    "contract": "currency",
                    "function": "transfer",
                    "kwargs": {
                        "amount": 1000,
                        "to": "stu",
                    },
                    "stamps_supplied": 100,
                },
                "metadata": {"signature": "abc"},
                "b_meta": {"nanos": 0, "hash": "0x0", "height": 0, "chain_id": "test-chain"},
            },
            enabled_fees=True,rewards_handler=self.rewards_handler
        )
        self.assertTrue(transfer["tx_result"]["state"][1]['value'], 0.004)
        transfer2 = self.tx_processor.process_tx(
            tx={
                "payload": {
                    "sender": "7fa496ca2438e487cc45a8a27fd95b2efe373223f7b72868fbab205d686be48e",
                    "contract": "currency",
                    "function": "transfer",
                    "kwargs": {
                        "amount": 1000,
                        "to": "stu",
                    },
                    "stamps_supplied": 100,
                },
                "metadata": {"signature": "abc"},
                "b_meta": {"nanos": 0, "hash": "0x0", "height": 0, "chain_id": "test-chain"},
            },
            enabled_fees=True,rewards_handler=self.rewards_handler
        )
        self.assertTrue(transfer2["tx_result"]["state"][1]['value'], 0.008)

if __name__ == "__main__":
    unittest.main()
