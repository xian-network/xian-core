import unittest
import datetime
import os
from pathlib import Path
import utils
from contracting.client import ContractingClient
from contracting.storage.driver import Driver
from xian.processor import TxProcessor
from fixtures.mock_constants import MockConstants


def create_block_meta(dt: datetime.datetime = datetime.datetime.now()):
    # Get the current time in nanoseconds
    nanos = int(dt.timestamp() * 1e9)
    # Mock b_meta dictionary with current nanoseconds
    return {
        "nanos": nanos,  # Current nanoseconds timestamp
        "height": 123456,  # Example block number
        "chain_id": "test-chain",  # Example chain ID
        "hash": "abc123def456",  # Example block hash
    }




def _resolve_contracts_dir() -> Path:
    # Primary: alongside this test file
    here = Path(__file__).resolve().parent
    p = here / "contracts" / "rollback"
    if p.is_dir():
        return p
    # Fallback: repository-style path from CWD (e.g. in CI)
    cwd = Path.cwd()
    q = cwd / "tests" / "integration" / "contracts" / "rollback"
    if q.is_dir():
        return q
    # Walk up from test file to find a tests root
    for parent in here.parents:
        candidate = parent / "tests" / "integration" / "contracts" / "rollback"
        if candidate.is_dir():
            return candidate
    # As a last resort, return the first constructed path (will raise later)
    return p


class TestStateRollback(unittest.TestCase):
    def setUp(self):
        utils.setup_fixtures()
        self.driver = Driver(storage_home=MockConstants.STORAGE_HOME)
        self.client = ContractingClient(driver=self.driver)
        self.client.flush()
        self.txp = TxProcessor(client=self.client)
        base_dir = str(_resolve_contracts_dir())
        with open(f"{base_dir}/con_mutable_map.py") as f:
            code = f.read()
        self.client.submit(code, name="con_mutable_map")
        self.contract = self.client.get_contract("con_mutable_map")
        # Submit cross-contract mutator
        with open(f"{base_dir}/con_mutator.py") as f:
            code = f.read()
        self.client.submit(code, name="con_mutator")
        # Submit token contract to use for overdraw failure
        with open(f"{base_dir}/currency_1.py") as f:
            code = f.read()
        self.client.submit(code, name="currency_1")
        # Submit a failer that mutates then attempts overdraw via token
        with open(f"{base_dir}/con_overdraw_fail.py") as f:
            code = f.read()
        self.client.submit(code, name="con_overdraw_fail")
        # Add callee-side failure to mutator
        with open(f"{base_dir}/con_mutator_fail.py") as f:
            code = f.read()
        self.client.submit(code, name="con_mutator_fail")
        # Persist submissions to disk and clear caches so driver.pending_writes is clean
        self.driver.hard_apply(0)

    def tearDown(self):
        utils.teardown_fixtures()
        self.client.flush()

    def assert_no_driver_writes(self, where: str = ""):
        self.assertEqual(self.driver.pending_writes, {}, f"pending_writes not empty {where}")
        self.assertEqual(self.driver.transaction_writes, {}, f"transaction_writes not empty {where}")

    def hard_apply_block(self, b_meta):
        # Mirror block boundary commit behavior
        self.driver.hard_apply(b_meta["nanos"])

    def driver_read_nested(self, key: str):
        # Directly query the driver for on-disk/cached state
        return self.driver.get(self.driver.make_key("con_mutable_map", "nested", [key]))

    def assert_no_contract_writes(self, where: str = ""):
        leaked = [k for k in self.driver.pending_writes.keys() if k.startswith("con_mutable_map.")]
        self.assertEqual(leaked, [], f"unexpected con_mutable_map writes {where}: {leaked}")

    def assert_currency_write_present(self, sender: str = "alice", where: str = ""):
        keys = list(self.driver.pending_writes.keys())
        self.assertTrue(any(k.startswith(f"currency.balances:{sender}") for k in keys), f"expected stamp write missing {where}: {keys}")

    def assert_contract_keys_equal(self, expected_keys, where: str = ""):
        actual = sorted([k for k in self.driver.pending_writes.keys() if k.startswith("con_mutable_map.")])
        self.assertEqual(actual, sorted(expected_keys), f"unexpected con_mutable_map writes {where}: {actual}")

    def test_in_place_mutation_rollback(self):
        bm1 = create_block_meta(datetime.datetime.now())
        bm2 = create_block_meta(datetime.datetime.now())

        # Tx 1: initialize (expected success)
        self.txp.process_tx(
            tx={
                "payload": {
                    "sender": "alice",
                    "contract": "con_mutable_map",
                    "function": "init_key",
                    "kwargs": {"key": "k"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": bm1,
            }
        )

        # Sanity check after tx1
        self.assertEqual(self.contract.nested["k"]["count"], 1)
        self.assertEqual(self.contract.nested["k"]["items"], [1])
        # Commit end of block and verify driver state
        self.hard_apply_block(bm1)
        self.assertEqual(self.driver_read_nested("k"), {"count": 1, "items": [1]})
        self.assert_no_contract_writes("after commit bm1")

        # Tx 2: mutate in-place then fail
        res2 = self.txp.process_tx(
            tx={
                "payload": {
                    "sender": "alice",
                    "contract": "con_mutable_map",
                    "function": "mutate_in_place_and_fail",
                    "kwargs": {"key": "k"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": bm2,
            }
        )

        # Ensure the tx failed as intended
        self.assertNotEqual(res2.get("tx_result", {}).get("status"), 0)
        # Failure should not introduce new contract writes
        self.assert_no_contract_writes("after mutate_in_place_and_fail failure")
        # Expected behavior: rollback => state unchanged
        self.assertEqual(self.contract.nested["k"]["count"], 1)
        self.assertEqual(self.contract.nested["k"]["items"], [1])

    def test_same_block_in_place_mutation_rollback(self):
        bm = create_block_meta(datetime.datetime.now())

        # Tx 1: initialize in same block
        self.txp.process_tx(
            tx={
                "payload": {
                    "sender": "alice",
                    "contract": "con_mutable_map",
                    "function": "init_key",
                    "kwargs": {"key": "k_sb"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": bm,
            }
        )

        # Tx 2: same block, mutate then fail
        # Snapshot current contract writes before failure
        pre_keys = sorted([k for k in self.driver.pending_writes.keys() if k.startswith("con_mutable_map.")])
        res = self.txp.process_tx(
            tx={
                "payload": {
                    "sender": "alice",
                    "contract": "con_mutable_map",
                    "function": "mutate_in_place_and_fail",
                    "kwargs": {"key": "k_sb"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": bm,
            }
        )
        self.assertNotEqual(res.get("tx_result", {}).get("status"), 0)
        post_keys = sorted([k for k in self.driver.pending_writes.keys() if k.startswith("con_mutable_map.")])
        self.assertEqual(pre_keys, post_keys, "same-block failure introduced unexpected contract writes")
        # In same block, the init write remains pending; assert no extra contract writes leaked
        self.assert_contract_keys_equal(["con_mutable_map.nested:k_sb"], "after same-block mutate + fail")
        self.assertEqual(self.contract.nested["k_sb"]["count"], 1)
        self.assertEqual(self.contract.nested["k_sb"]["items"], [1])

    def test_nested_mutation_rollback(self):
        bm1 = create_block_meta(datetime.datetime.now())
        bm2 = create_block_meta(datetime.datetime.now())

        # init nested structure
        self.txp.process_tx(
            tx={
                "payload": {
                    "sender": "alice",
                    "contract": "con_mutable_map",
                    "function": "init_nested",
                    "kwargs": {"key": "k_nested"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": bm1,
            }
        )
        self.assertEqual(self.contract.nested["k_nested"]["child"]["x"], 1)
        self.assertEqual(self.contract.nested["k_nested"]["items"], [{"v": 1}])
        # Commit block so no pending writes carry into the failing tx
        self.hard_apply_block(bm1)
        self.assert_no_contract_writes("after commit bm1 nested")

        # mutate deep and fail
        res = self.txp.process_tx(
            tx={
                "payload": {
                    "sender": "alice",
                    "contract": "con_mutable_map",
                    "function": "mutate_nested_and_fail",
                    "kwargs": {"key": "k_nested"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": bm2,
            }
        )
        self.assertNotEqual(res.get("tx_result", {}).get("status"), 0)
        self.assert_no_contract_writes("after mutate_nested_and_fail failure")
        self.assertEqual(self.contract.nested["k_nested"]["child"]["x"], 1)
        self.assertEqual(self.contract.nested["k_nested"]["items"], [{"v": 1}])

    def test_reassign_after_mutation_rollback(self):
        bm1 = create_block_meta(datetime.datetime.now())
        bm2 = create_block_meta(datetime.datetime.now())

        # init simple
        self.txp.process_tx(
            tx={
                "payload": {
                    "sender": "alice",
                    "contract": "con_mutable_map",
                    "function": "init_key",
                    "kwargs": {"key": "k_reassign"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": bm1,
            }
        )
        self.assertEqual(self.contract.nested["k_reassign"]["count"], 1)
        self.assertEqual(self.contract.nested["k_reassign"]["items"], [1])

    def test_aliasing_default_mutation_rollback(self):
        bm1 = create_block_meta(datetime.datetime.now())
        bm2 = create_block_meta(datetime.datetime.now())

        # two different keys use default
        self.txp.process_tx(
            tx={
                "payload": {
                    "sender": "alice",
                    "contract": "con_mutable_map",
                    "function": "alias_set",
                    "kwargs": {"key": "a1"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": bm1,
            }
        )
        # alias_set writes should be pending until commit
        self.assert_contract_keys_equal(["con_mutable_map.aliased:a1"], "after alias_set a1 success")
        self.txp.process_tx(
            tx={
                "payload": {
                    "sender": "alice",
                    "contract": "con_mutable_map",
                    "function": "alias_set",
                    "kwargs": {"key": "a2"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": bm1,
            }
        )
        self.assert_contract_keys_equal(["con_mutable_map.aliased:a1", "con_mutable_map.aliased:a2"], "after alias_set a2 success")

        # mutate a1 then fail; ensure a2 unchanged and a1 rolled back
        pre_keys = sorted([k for k in self.driver.pending_writes.keys() if k.startswith("con_mutable_map.")])
        res = self.txp.process_tx(
            tx={
                "payload": {
                    "sender": "alice",
                    "contract": "con_mutable_map",
                    "function": "alias_mutate_and_fail",
                    "kwargs": {"key": "a1"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": bm2,
            }
        )
        self.assertNotEqual(res.get("tx_result", {}).get("status"), 0)
        post_keys = sorted([k for k in self.driver.pending_writes.keys() if k.startswith("con_mutable_map.")])
        self.assertEqual(pre_keys, post_keys, "alias failure introduced unexpected contract writes")
        self.assertEqual(self.contract.aliased["a1"], {"count": 0, "items": []})
        self.assertEqual(self.contract.aliased["a2"], {"count": 0, "items": []})

    def test_callee_failure_after_cross_mutation_rollback(self):
        bm1 = create_block_meta(datetime.datetime.now())
        bm2 = create_block_meta(datetime.datetime.now())

        # init simple
        self.txp.process_tx(
            tx={
                "payload": {
                    "sender": "alice",
                    "contract": "con_mutable_map",
                    "function": "init_key",
                    "kwargs": {"key": "k_callee"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": bm1,
            }
        )
        self.assertEqual(self.contract.nested["k_callee"]["count"], 1)
        self.assertEqual(self.contract.nested["k_callee"]["items"], [1])

        # call mutator that fails inside callee
        res = self.txp.process_tx(
            tx={
                "payload": {
                    "sender": "alice",
                    "contract": "con_mutable_map",
                    "function": "cross_mutate_then_fail",
                    "kwargs": {"key": "k_callee", "mutator": "con_mutator_fail"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": bm2,
            }
        )
        self.assertNotEqual(res.get("tx_result", {}).get("status"), 0)
        self.assertEqual(self.contract.nested["k_callee"]["count"], 1)
        self.assertEqual(self.contract.nested["k_callee"]["items"], [1])

    def test_multiple_failing_txs_same_and_next_block(self):
        bm1 = create_block_meta(datetime.datetime.now())
        bm2 = bm1  # same block
        bm3 = create_block_meta(datetime.datetime.now())  # next block

        # init
        self.txp.process_tx(
            tx={
                "payload": {
                    "sender": "alice",
                    "contract": "con_mutable_map",
                    "function": "init_key",
                    "kwargs": {"key": "k_multi"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": bm1,
            }
        )
        self.assertEqual(self.contract.nested["k_multi"]["count"], 1)
        self.assertEqual(self.contract.nested["k_multi"]["items"], [1])

        # two failing tx in same block
        res1 = self.txp.process_tx(
            tx={
                "payload": {
                    "sender": "alice",
                    "contract": "con_mutable_map",
                    "function": "mutate_in_place_and_fail",
                    "kwargs": {"key": "k_multi"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": bm2,
            }
        )
        res2 = self.txp.process_tx(
            tx={
                "payload": {
                    "sender": "alice",
                    "contract": "con_mutable_map",
                    "function": "mutate_then_reassign_and_fail",
                    "kwargs": {"key": "k_multi"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": bm2,
            }
        )
        self.assertNotEqual(res1.get("tx_result", {}).get("status"), 0)
        self.assertNotEqual(res2.get("tx_result", {}).get("status"), 0)
        # init write remains pending in same block; ensure no new contract writes
        self.assert_contract_keys_equal(["con_mutable_map.nested:k_multi"], "after same-block dual failures")
        self.assertEqual(self.contract.nested["k_multi"]["count"], 1)
        self.assertEqual(self.contract.nested["k_multi"]["items"], [1])

        # Commit end of this block before next-block failure
        self.hard_apply_block(bm2)
        self.assert_no_contract_writes("after commit bm2 before next block")

        # failing tx in next block
        res3 = self.txp.process_tx(
            tx={
                "payload": {
                    "sender": "alice",
                    "contract": "con_mutable_map",
                    "function": "mutate_in_place_and_fail",
                    "kwargs": {"key": "k_multi"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": bm3,
            }
        )
        self.assertNotEqual(res3.get("tx_result", {}).get("status"), 0)
        self.assert_no_contract_writes("after next-block failure")
        self.assertEqual(self.contract.nested["k_multi"]["count"], 1)
        self.assertEqual(self.contract.nested["k_multi"]["items"], [1])

    def test_type_error_failure_rollback(self):
        bm1 = create_block_meta(datetime.datetime.now())
        bm2 = create_block_meta(datetime.datetime.now())

        # init simple
        self.txp.process_tx(
            tx={
                "payload": {
                    "sender": "alice",
                    "contract": "con_mutable_map",
                    "function": "init_key",
                    "kwargs": {"key": "k_type"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": bm1,
            }
        )
        self.assertEqual(self.contract.nested["k_type"]["count"], 1)
        self.assertEqual(self.contract.nested["k_type"]["items"], [1])

    def test_cross_contract_token_overdraw_failure_rollback(self):
        bm1 = create_block_meta(datetime.datetime.now())
        bm2 = create_block_meta(datetime.datetime.now())

        # init simple
        self.txp.process_tx(
            tx={
                "payload": {
                    "sender": "alice",
                    "contract": "con_mutable_map",
                    "function": "init_key",
                    "kwargs": {"key": "k_tok"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": bm1,
            }
        )
        self.assertEqual(self.contract.nested["k_tok"]["count"], 1)
        self.assertEqual(self.contract.nested["k_tok"]["items"], [1])
        # Commit before failing tx
        self.hard_apply_block(bm1)
        self.assert_no_contract_writes("after commit bm1 overdraw")

        # call failer that mutates then calls token transfer, causing overdraw failure
        res = self.txp.process_tx(
            tx={
                "payload": {
                    "sender": "alice",
                    "contract": "con_overdraw_fail",
                    "function": "mutate_then_overdraw",
                    "kwargs": {"key": "k_tok", "token": "currency_1", "to": "bob", "amount": 1},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": bm2,
            }
        )
        self.assertNotEqual(res.get("tx_result", {}).get("status"), 0)
        self.assert_no_contract_writes("after mutate_then_overdraw failure")
        # State should be unchanged due to rollback
        val = self.contract.nested["k_tok"]
        self.assertIsNotNone(val)
        self.assertEqual(val, {"count": 1, "items": [1]})

        res = self.txp.process_tx(
            tx={
                "payload": {
                    "sender": "alice",
                    "contract": "con_mutable_map",
                    "function": "type_error_after_mutation",
                    "kwargs": {"key": "k_type"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": bm2,
            }
        )
        self.assertNotEqual(res.get("tx_result", {}).get("status"), 0)
        self.assert_no_contract_writes("after type_error_after_mutation failure")
        self.assertEqual(self.contract.nested["k_type"], None)

    def test_cross_contract_mutation_rollback(self):
        bm1 = create_block_meta(datetime.datetime.now())
        bm2 = create_block_meta(datetime.datetime.now())

        # init simple
        self.txp.process_tx(
            tx={
                "payload": {
                    "sender": "alice",
                    "contract": "con_mutable_map",
                    "function": "init_key",
                    "kwargs": {"key": "k_cross"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": bm1,
            }
        )
        self.assertEqual(self.contract.nested["k_cross"]["count"], 1)
        self.assertEqual(self.contract.nested["k_cross"]["items"], [1])

        # call cross mutation, then fail in caller
        res = self.txp.process_tx(
            tx={
                "payload": {
                    "sender": "alice",
                    "contract": "con_mutable_map",
                    "function": "cross_mutate_then_fail",
                    "kwargs": {"key": "k_cross", "mutator": "con_mutator"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": bm2,
            }
        )
        self.assertNotEqual(res.get("tx_result", {}).get("status"), 0)
        # Expected unchanged
        self.assertEqual(self.contract.nested["k_cross"]["count"], 1)
        self.assertEqual(self.contract.nested["k_cross"]["items"], [1])

    def test_fees_enabled_failing_tx_rollback(self):
        bm1 = create_block_meta(datetime.datetime.now())
        bm2 = create_block_meta(datetime.datetime.now())

        # init simple
        self.txp.process_tx(
            tx={
                "payload": {
                    "sender": "alice",
                    "contract": "con_mutable_map",
                    "function": "init_key",
                    "kwargs": {"key": "k_fees"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": bm1,
            }
        )
        self.assertEqual(self.contract.nested["k_fees"]["count"], 1)
        self.assertEqual(self.contract.nested["k_fees"]["items"], [1])
        # Commit before failing tx
        self.hard_apply_block(bm1)
        self.assert_no_contract_writes("after commit bm1 fees")

        # failing tx with enabled_fees
        res = self.txp.process_tx(
            enabled_fees=True,
            tx={
                "payload": {
                    "sender": "alice",
                    "contract": "con_mutable_map",
                    "function": "mutate_in_place_and_fail",
                    "kwargs": {"key": "k_fees"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": bm2,
            }
        )
        self.assertNotEqual(res.get("tx_result", {}).get("status"), 0)
        # Fees enabled: expect only currency stamp write; no contract writes
        self.assert_currency_write_present(where="after fees-enabled mutate_in_place_and_fail failure")
        self.assert_no_contract_writes("after fees-enabled mutate_in_place_and_fail failure")
        self.assertEqual(self.contract.nested["k_fees"]["count"], 1)
        self.assertEqual(self.contract.nested["k_fees"]["items"], [1])

        # mutate then reassign and fail (fees enabled)
        res = self.txp.process_tx(
            tx={
                "payload": {
                    "sender": "alice",
                    "contract": "con_mutable_map",
                    "function": "mutate_then_reassign_and_fail",
                    "kwargs": {"key": "k_fees"},
                    "stamps_supplied": 1000,
                },
                "metadata": {"signature": "abc"},
                "b_meta": bm2,
            }
        )
        self.assertNotEqual(res.get("tx_result", {}).get("status"), 0)
        self.assert_currency_write_present(where="after fees-enabled mutate_then_reassign_and_fail failure")
        self.assert_no_contract_writes("after fees-enabled mutate_then_reassign_and_fail failure")
        self.assertEqual(self.contract.nested["k_fees"]["count"], 1)
        self.assertEqual(self.contract.nested["k_fees"]["items"], [1])


if __name__ == "__main__":
    unittest.main()


