import asyncio
import logging
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
    ) -> bytes:
        with use_node_constants(node_dir) as node_constants:
            app = await Xian.create(constants=node_constants)
            app.current_block_meta = {"height": 0, "nanos": 0}
            self._seed_account_balances(app)

            cleanup: Optional[Callable[[], None]] = None
            if mutate is not None:
                maybe_cleanup = mutate(app)
                if asyncio.iscoroutine(maybe_cleanup):
                    maybe_cleanup = await maybe_cleanup
                if callable(maybe_cleanup):
                    cleanup = maybe_cleanup

            try:
                last_app_hash: Optional[bytes] = None
                for request in requests:
                    response = await self._process_request(app, request)
                    last_app_hash = response.finalize_block.app_hash
                    await app.commit()

                if last_app_hash is None:
                    raise AssertionError("scenario produced no finalize_block responses")
                return last_app_hash
            finally:
                if cleanup is not None:
                    cleanup()

    def _seed_account_balances(self, app: Xian) -> None:
        for account, amount in SCENARIO_ACCOUNT_BALANCES.items():
            storage_key = f"currency.balances:{account}"
            app.client.raw_driver.set(storage_key, amount)

    async def test_app_hash_consistency_across_nodes(self) -> None:
        for name, requests in self.scenarios.items():
            hashes: List[bytes] = []
            for node_dir in self.node_dirs:
                hashes.append(await self._run_node(node_dir, requests))

            self.assertGreater(len(hashes), 1, f"scenario '{name}' did not run on multiple nodes")
            self.assertTrue(all(h == hashes[0] for h in hashes[1:]), f"scenario '{name}' produced divergent app hashes")

    async def test_module_probe_divergence_detection(self) -> None:
        module_requests = self.scenarios.get("module_probe")
        if not module_requests:
            self.skipTest("module_probe scenario missing")

        baseline_hash = await self._run_node(self.node_dirs[0], module_requests)

        async def mutate(app: Xian) -> Callable[[], None]:
            from contracting.stdlib.bridge import hashing

            original_sha3 = hashing.sha3

            def patched_sha3(value: str) -> str:
                return "mutated-" + original_sha3(value)[::-1]

            hashing.sha3 = patched_sha3

            def restore() -> None:
                hashing.sha3 = original_sha3

            return restore

        divergent_hash = await self._run_node(self.node_dirs[1], module_requests, mutate=mutate)

        self.assertNotEqual(
            baseline_hash,
            divergent_hash,
            "mutating a bridge module should produce divergent app hashes across nodes",
        )


if __name__ == "__main__":
    unittest.main()
