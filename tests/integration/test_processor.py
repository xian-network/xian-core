import unittest
from contracting.client import ContractingClient
from xian.processor import TxProcessor
from fixtures.mock_constants import MockConstants
from datetime import datetime
from utils import setup_fixtures, teardown_fixtures
import time
import os


def create_block_meta(dt: datetime = datetime.now()):
    # Get the current time in nanoseconds
    nanos = int(time.mktime(dt.timetuple()) * 1e9 + dt.microsecond * 1e3)
    # Mock b_meta dictionary with current nanoseconds
    return {
        "nanos": nanos,  # Current nanoseconds timestamp
        "height": 123456,  # Example block number
        "chain_id": "test-chain",  # Example chain ID
        "hash": "abc123def456",  # Example block hash
    }


class TestProcessor(unittest.TestCase):
    def setUp(self):
        setup_fixtures()
        # Called before every test, bootstraps the environment.
        self.c = ContractingClient()
        self.d = self.c.raw_driver
        # self.c.flush()
        self.tx_processor = TxProcessor(client=self.c)
        # Hard load the submission contract
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # submission_contract_path = os.path.abspath(
        #     os.path.join(
        #         self.script_dir,
        #         "../../xian-contracting/src/contracting/contracts/submission.s.py",
        #     )
        # )
        
        # with open(submission_contract_path) as f:
        #     code = f.read()
        # self.d.set_contract(name="submission", code=code)

        # Get the directory where the script is located

        token_path = os.path.abspath(
            os.path.join(
                self.script_dir,
                "./contracts/token_contract.py",
            )
        )
        with open("./contracts/token_contract.py") as f:
            code = f.read()
            self.c.submit(code, name="currency")

        self.currency = self.c.get_contract("currency")

        proxy_path = os.path.abspath(
            os.path.join(
                self.script_dir,
                "./contracts/proxy.py",
            )
        )
        with open("./contracts/proxy.py") as f:
            code = f.read()
            self.c.submit(code, name="proxy")

        self.proxy = self.c.get_contract("proxy")

    def tearDown(self):
        teardown_fixtures()
        # Called after every test, ensures each test starts with a clean slate and is isolated from others
        # self.c.flush()

    def test_transfer_returns_event(self):
        # Setup - approve first
        self.d.set(
            key="currency.balances:sys:bob",
            value=100000,
        )
        self.d.set(
            key="currency.balances:sys",
            value=100000,
        )
        # Now transfer
        res = self.tx_processor.process_tx(
            tx={
                "payload": {
                    "contract": "currency",
                    "function": "transfer_from",
                    "sender": "bob",
                    "kwargs": {
                        "amount": 100,
                        "to": "bob",
                        "main_account": "sys",
                    },
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": create_block_meta(),
            }
        )
        expected_events = [
            {
                "caller": "bob",
                "contract": "currency",
                "event": "Transfer",
                "data_indexed": {"from": "sys", "to": "bob"},
                "data": {"amount": 100},
                "signer": "bob",
            }
        ]
        self.assertEqual(res["tx_result"]["events"], expected_events)

    def test_send_multiple_returns_events(self):
        self.d.set(
            key="currency.balances:proxy",
            value=100000,
        )
        self.d.set(
            key="currency.balances:sys",
            value=100000,
        )
        self.d.set(
            key="currency.balances:bob",
            value=100000,
        )
        res = self.tx_processor.process_tx(
            enabled_fees=True,
            tx={
                "payload": {
                    "contract": "proxy",
                    "function": "send_multiple",
                    "sender": "bob",
                    "kwargs": {
                        "amount": 100,
                        "to": ["casey", "francis", "sally", "ed", "yolanda"],
                    },
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": create_block_meta(),
            }
        )
        expected_events = [
            {
                "caller": "proxy",
                "contract": "currency",
                "event": "Transfer",
                "data_indexed": {"from": "proxy", "to": "casey"},
                "data": {"amount": 100},
                "signer": "bob",
            },
            {
                "caller": "proxy",
                "contract": "currency",
                "event": "Transfer",
                "data_indexed": {"from": "proxy", "to": "francis"},
                "data": {"amount": 100},
                "signer": "bob",
            },
            {
                "caller": "proxy",
                "contract": "currency",
                "event": "Transfer",
                "data_indexed": {"from": "proxy", "to": "sally"},
                "data": {"amount": 100},
                "signer": "bob",
            },
            {
                "caller": "proxy",
                "contract": "currency",
                "event": "Transfer",
                "data_indexed": {"from": "proxy", "to": "ed"},
                "data": {"amount": 100},
                "signer": "bob",
            },
            {
                "caller": "proxy",
                "contract": "currency",
                "event": "Transfer",
                "data_indexed": {"from": "proxy", "to": "yolanda"},
                "data": {"amount": 100},
                "signer": "bob",
            },
        ]

        self.assertEqual(res["tx_result"]["events"], expected_events)
        
        


if __name__ == "__main__":
    unittest.main()
