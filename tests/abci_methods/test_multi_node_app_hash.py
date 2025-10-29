import asyncio
import logging
from dataclasses import dataclass
import unittest
from io import BytesIO
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, Iterable, List, Optional, Union

from abci.server import ProtocolHandler
from abci.utils import read_messages
from cometbft.abci.v1beta3.types_pb2 import Request, Response

try:
    import contracting  # type: ignore  # noqa: F401
except ImportError:  # pragma: no cover - handled by unittest skip
    CONTRACTING_AVAILABLE = False
else:
    CONTRACTING_AVAILABLE = True

from fixtures.multi_node import (
    setup_multi_node_fixtures,
    teardown_multi_node_fixtures,
    use_node_constants,
)
from fixtures.multi_node_instrumentation import (
    attach_state_fingerprint_recorder,
    StateFingerprintRecorder,
)
from fixtures.multi_node_scenarios import (
    SCENARIO_ACCOUNT_BALANCES,
    load_multi_node_scenarios,
)

if CONTRACTING_AVAILABLE:
    from xian.xian_abci import Xian
elif TYPE_CHECKING:  # pragma: no cover - for type checkers only
    from xian.xian_abci import Xian  # type: ignore[misc]
else:
    Xian = Any  # type: ignore[assignment]

logging.disable(logging.CRITICAL)


async def deserialize(raw: bytes) -> Response:
    resp = next(read_messages(BytesIO(raw), Response))
    return resp


ScenarioRequests = List[Request]
Cleanup = Optional[Callable[[], None]]
MutatorResult = Union[Cleanup, Awaitable[Cleanup]]
Mutator = Callable[[Xian], MutatorResult]


@unittest.skipUnless(CONTRACTING_AVAILABLE, "contracting dependency is required for multi-node integration tests")
class TestMultiNodeAppHash(unittest.IsolatedAsyncioTestCase):
    @dataclass
    class NodeRunResult:
        app_hash: bytes
        block_fingerprints: List[str]

    async def asyncSetUp(self) -> None:
        self.node_dirs = setup_multi_node_fixtures(3)
        self.scenarios: Dict[str, ScenarioRequests] = load_multi_node_scenarios()
        if not self.scenarios:
            self.skipTest("no multi-node scenarios registered")

    async def asyncTearDown(self) -> None:
        teardown_multi_node_fixtures()

    async def _process_request(self, app: Xian, request: Request) -> Response:
        handler = ProtocolHandler(app)
        raw = await handler.process("finalize_block", request)
        return await deserialize(raw)

    async def _run_node(
        self,
        node_dir,
        requests: Iterable[Request],
        mutate: Optional[Mutator] = None,
    ) -> "TestMultiNodeAppHash.NodeRunResult":
        with use_node_constants(node_dir) as node_constants:
            app = await Xian.create(constants=node_constants)
            app.current_block_meta = {"height": 0, "nanos": 0}
            app.enable_tx_fee = False
            app.rewards_handler = None
            self._seed_account_balances(app)

            cleanup_callbacks: List[Callable[[], None]] = []

            recorder: StateFingerprintRecorder = attach_state_fingerprint_recorder(app)
            cleanup_callbacks.append(recorder.cleanup)  # type: ignore[arg-type]

            if mutate is not None:
                maybe_cleanup = mutate(app)
                if asyncio.iscoroutine(maybe_cleanup):
                    maybe_cleanup = await maybe_cleanup
                if callable(maybe_cleanup):
                    cleanup_callbacks.append(maybe_cleanup)

            try:
                last_app_hash: Optional[bytes] = None
                block_fingerprints: List[str] = []
                for request in requests:
                    recorder.begin_block()
                    response = await self._process_request(app, request)
                    last_app_hash = response.finalize_block.app_hash
                    block_fingerprints.append(recorder.finish_block())
                    await app.commit()

                if last_app_hash is None:
                    raise AssertionError("scenario produced no finalize_block responses")
                return self.NodeRunResult(app_hash=last_app_hash, block_fingerprints=block_fingerprints)
            finally:
                for cleanup in reversed(cleanup_callbacks):
                    cleanup()

    def _seed_account_balances(self, app: Xian) -> None:
        for account, amount in SCENARIO_ACCOUNT_BALANCES.items():
            storage_key = f"currency.balances:{account}"
            app.client.raw_driver.set(storage_key, amount)

    async def test_app_hash_consistency_across_nodes(self) -> None:
        for name, requests in self.scenarios.items():
            hashes: List[bytes] = []
            block_fingerprints: List[List[str]] = []
            for node_dir in self.node_dirs:
                result = await self._run_node(node_dir, requests)
                hashes.append(result.app_hash)
                block_fingerprints.append(result.block_fingerprints)

            self.assertGreater(len(hashes), 1, f"scenario '{name}' did not run on multiple nodes")
            self.assertTrue(all(h == hashes[0] for h in hashes[1:]), f"scenario '{name}' produced divergent app hashes")
            self.assertTrue(
                all(fp == block_fingerprints[0] for fp in block_fingerprints[1:]),
                f"scenario '{name}' produced divergent state fingerprints",
            )

    async def test_module_probe_divergence_detection(self) -> None:
        module_requests = self.scenarios.get("module_probe")
        if not module_requests:
            self.skipTest("module_probe scenario missing")

        baseline_result = await self._run_node(self.node_dirs[0], module_requests)

        async def mutate(app: Xian) -> Callable[[], None]:
            from contracting.stdlib.bridge import hashing

            original_sha3 = hashing.sha3
            original_module_sha3 = hashing.hashlib_module.sha3

            def patched_sha3(value: str) -> str:
                return "mutated-" + original_sha3(value)[::-1]

            hashing.sha3 = patched_sha3
            hashing.hashlib_module.sha3 = patched_sha3

            def restore() -> None:
                hashing.sha3 = original_sha3
                hashing.hashlib_module.sha3 = original_module_sha3

            return restore

        divergent_result = await self._run_node(self.node_dirs[1], module_requests, mutate=mutate)

        self.assertNotEqual(
            baseline_result.block_fingerprints,
            divergent_result.block_fingerprints,
            "mutating a bridge module should produce divergent state fingerprints across nodes",
        )

        # Finalize block app hashes currently ignore transaction state, so they
        # remain equal even when the bridge produces divergent outputs.  The
        # explicit fingerprint comparison above ensures tests still catch
        # non-determinism until production hashing is updated.
        self.assertEqual(baseline_result.app_hash, divergent_result.app_hash)


if __name__ == "__main__":
    unittest.main()
